import Foundation
import SwiftUI

/// App-wide state. Owns credentials, the deal list, and refresh.
@MainActor
final class AppState: ObservableObject {
    @Published var isConfigured = false
    @Published var deals: [DealSummary] = []
    @Published var runs: [PickupRun] = []
    @Published var status: ServerStatus?
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var sort: String = "score"
    @Published var showingSaved = false

    private let tokenKey = "flipscan.token"
    private let urlKey = "flipscan.baseurl"

    init() {
        if let token = Keychain.read(tokenKey),
           let urlString = UserDefaults.standard.string(forKey: urlKey),
           let url = URL(string: urlString) {
            Task {
                await APIClient.shared.configure(baseURL: url, token: token)
                isConfigured = true
                await refresh()
            }
        }
    }

    // MARK: - Setup

    func connect(urlString: String, token: String) async -> Bool {
        var normalized = urlString.trimmingCharacters(in: .whitespaces)
        if normalized.hasSuffix("/") { normalized.removeLast() }
        guard let url = URL(string: normalized), url.scheme != nil else {
            errorMessage = "That doesn't look like a URL. Include http:// or https://"
            return false
        }

        await APIClient.shared.configure(baseURL: url, token: token)
        do {
            let serverStatus = try await APIClient.shared.status()
            status = serverStatus
            Keychain.save(tokenKey, value: token)
            UserDefaults.standard.set(normalized, forKey: urlKey)
            isConfigured = true
            errorMessage = nil
            await refresh()
            return true
        } catch {
            await APIClient.shared.clear()
            errorMessage = error.localizedDescription
            return false
        }
    }

    func disconnect() {
        Keychain.delete(tokenKey)
        UserDefaults.standard.removeObject(forKey: urlKey)
        deals = []
        runs = []
        status = nil
        isConfigured = false
        Task { await APIClient.shared.clear() }
    }

    // MARK: - Data

    func refresh() async {
        guard isConfigured else { return }
        isLoading = true
        defer { isLoading = false }

        do {
            async let fetchedDeals = APIClient.shared.deals(
                sort: sort, status: showingSaved ? "saved" : nil)
            async let fetchedStatus = APIClient.shared.status()
            deals = try await fetchedDeals
            status = try await fetchedStatus
            errorMessage = nil
        } catch APIError.unauthorized {
            errorMessage = APIError.unauthorized.localizedDescription
            disconnect()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func refreshRuns() async {
        guard isConfigured else { return }
        do {
            runs = try await APIClient.shared.runs()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func act(on dealId: Int, action: String, buyPrice: Double? = nil) async {
        do {
            try await APIClient.shared.sendFeedback(
                dealId: dealId,
                payload: FeedbackPayload(action: action, actualBuyPrice: buyPrice))
            if action == "passed" {
                deals.removeAll { $0.id == dealId }
            } else {
                await refresh()
            }
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func scanNow() async {
        do {
            try await APIClient.shared.triggerScan()
            // The scan runs server-side; give it a moment before reloading
            // rather than showing an unchanged list and looking broken.
            try? await Task.sleep(for: .seconds(6))
            await refresh()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    var totalPotential: Double { deals.reduce(0) { $0 + $1.netProfit } }
}

/// Minimal Keychain wrapper. The API token is a credential, so it does not
/// belong in UserDefaults, which is plain-text inside the app container.
enum Keychain {
    private static let service = "com.flipscan.app"

    static func save(_ key: String, value: String) {
        guard let data = value.data(using: .utf8) else { return }
        delete(key)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock,
        ]
        SecItemAdd(query as CFDictionary, nil)
    }

    static func read(_ key: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    static func delete(_ key: String) {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: key,
        ]
        SecItemDelete(query as CFDictionary)
    }
}

import Foundation

enum APIError: LocalizedError {
    case notConfigured
    case unauthorized
    case server(String)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .notConfigured: return "No server configured yet."
        case .unauthorized:  return "That token was rejected. Check FLIPSCAN_API_TOKEN on the server."
        case .server(let message): return message
        case .transport(let error): return error.localizedDescription
        }
    }
}

/// Talks to the FlipScan server. One shared token, sent as a bearer header.
actor APIClient {
    static let shared = APIClient()

    private var baseURL: URL?
    private var token: String?

    private lazy var decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        // The server sends offset-qualified ISO timestamps, but SQLite-backed
        // rows have historically come back naive. Accept both rather than
        // failing the whole response over a missing 'Z'.
        decoder.dateDecodingStrategy = .custom { decoder in
            let container = try decoder.singleValueContainer()
            let text = try container.decode(String.self)
            if let date = ISO8601DateFormatter.withFractionalSeconds.date(from: text) { return date }
            if let date = ISO8601DateFormatter.plain.date(from: text) { return date }
            if let date = DateFormatter.naiveUTCFractional.date(from: text) { return date }
            if let date = DateFormatter.naiveUTC.date(from: text) { return date }
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "Unrecognised date: \(text)")
        }
        return decoder
    }()

    private lazy var encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()

    func configure(baseURL: URL, token: String) {
        self.baseURL = baseURL
        self.token = token
    }

    func clear() {
        baseURL = nil
        token = nil
    }

    // MARK: - Core

    private func request<T: Decodable>(
        _ path: String,
        method: String = "GET",
        query: [String: String] = [:],
        body: (any Encodable)? = nil
    ) async throws -> T {
        guard let baseURL, let token else { throw APIError.notConfigured }

        var components = URLComponents(
            url: baseURL.appendingPathComponent(path),
            resolvingAgainstBaseURL: false)
        if !query.isEmpty {
            components?.queryItems = query.map { URLQueryItem(name: $0.key, value: $0.value) }
        }
        guard let url = components?.url else { throw APIError.notConfigured }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = method
        urlRequest.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.timeoutInterval = 30

        if let body {
            urlRequest.httpBody = try encoder.encode(AnyEncodable(body))
        }

        do {
            let (data, response) = try await URLSession.shared.data(for: urlRequest)
            guard let http = response as? HTTPURLResponse else {
                throw APIError.server("Malformed response")
            }
            if http.statusCode == 401 { throw APIError.unauthorized }
            guard (200..<300).contains(http.statusCode) else {
                let detail = (try? JSONDecoder().decode(ErrorBody.self, from: data))?.detail
                throw APIError.server(detail ?? "HTTP \(http.statusCode)")
            }
            return try decoder.decode(T.self, from: data)
        } catch let error as APIError {
            throw error
        } catch let error as DecodingError {
            throw APIError.server("Could not read the server's response: \(error)")
        } catch {
            throw APIError.transport(error)
        }
    }

    private struct ErrorBody: Decodable { let detail: String? }

    // MARK: - Endpoints

    func deals(sort: String = "score", limit: Int = 60,
               status: String? = nil, minProfit: Double? = nil) async throws -> [DealSummary] {
        var query = ["sort": sort, "limit": String(limit)]
        if let status { query["status"] = status; query["include_dismissed"] = "true" }
        if let minProfit { query["min_profit"] = String(minProfit) }
        return try await request("api/deals", query: query)
    }

    func deal(_ id: Int) async throws -> DealDetail {
        try await request("api/deals/\(id)")
    }

    func runs(clusterMiles: Double = 8, minRunSize: Int = 2) async throws -> [PickupRun] {
        try await request("api/deals/runs",
                          query: ["cluster_miles": String(clusterMiles),
                                  "min_run_size": String(minRunSize)])
    }

    @discardableResult
    func sendFeedback(dealId: Int, payload: FeedbackPayload) async throws -> FeedbackAck {
        try await request("api/deals/\(dealId)/feedback", method: "POST", body: payload)
    }

    func status() async throws -> ServerStatus {
        try await request("api/status")
    }

    @discardableResult
    func triggerScan() async throws -> ScanAck {
        try await request("api/scans/run", method: "POST")
    }

    @discardableResult
    func registerDevice(token deviceToken: String, label: String) async throws -> DeviceAck {
        struct Body: Encodable { let platform: String; let token: String; let label: String }
        return try await request("api/devices", method: "POST",
                                 body: Body(platform: "apns", token: deviceToken, label: label))
    }

    struct FeedbackAck: Decodable { let ok: Bool; let status: String?; let note: String? }
    struct ScanAck: Decodable { let ok: Bool; let note: String? }
    struct DeviceAck: Decodable { let ok: Bool; let id: Int? }
}

/// Type-erasing wrapper so `request` can take any Encodable body.
/// The closure form matters: `wrapped.encode` as a partially-applied method
/// reference on an existential doesn't type-check.
private struct AnyEncodable: Encodable {
    private let encodeFunc: (any Encoder) throws -> Void

    init(_ wrapped: any Encodable) {
        encodeFunc = { encoder in try wrapped.encode(to: encoder) }
    }

    func encode(to encoder: any Encoder) throws { try encodeFunc(encoder) }
}

// MARK: - Date parsing

extension ISO8601DateFormatter {
    static let withFractionalSeconds: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter
    }()

    static let plain: ISO8601DateFormatter = {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        return formatter
    }()
}

extension DateFormatter {
    /// Fallback for timestamps with no offset. Assumed UTC, which is what the
    /// server writes even when the database drops the timezone.
    static let naiveUTC: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss"
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }()

    static let naiveUTCFractional: DateFormatter = {
        let formatter = DateFormatter()
        formatter.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSS"
        formatter.timeZone = TimeZone(identifier: "UTC")
        formatter.locale = Locale(identifier: "en_US_POSIX")
        return formatter
    }()
}

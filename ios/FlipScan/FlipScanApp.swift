import SwiftUI
import UserNotifications

@main
struct FlipScanApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate
    @StateObject private var state = AppState()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(state)
                .tint(.flipAccent)
                .task { appDelegate.state = state }
        }
    }
}

/// Handles APNs registration and notification taps.
///
/// Explicitly main-actor isolated: UIKit delegate callbacks arrive on the main
/// thread anyway, and saying so keeps strict-concurrency checking quiet about
/// touching `UIApplication` and `AppState` from here.
@MainActor
final class AppDelegate: NSObject, UIApplicationDelegate, UNUserNotificationCenterDelegate {
    weak var state: AppState?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions options: [UIApplication.LaunchOptionsKey: Any]? = nil
    ) -> Bool {
        UNUserNotificationCenter.current().delegate = self
        return true
    }

    func requestPushPermission() {
        UNUserNotificationCenter.current().requestAuthorization(
            options: [.alert, .sound, .badge]
        ) { granted, _ in
            guard granted else { return }
            DispatchQueue.main.async {
                UIApplication.shared.registerForRemoteNotifications()
            }
        }
    }

    func application(
        _ application: UIApplication,
        didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
    ) {
        let token = deviceToken.map { String(format: "%02x", $0) }.joined()
        // Read the device name here, on the main actor, rather than awaiting it
        // from inside the detached task.
        let deviceName = UIDevice.current.name
        Task {
            try? await APIClient.shared.registerDevice(token: token, label: deviceName)
        }
    }

    func application(
        _ application: UIApplication,
        didFailToRegisterForRemoteNotificationsWithError error: Error
    ) {
        print("APNs registration failed: \(error.localizedDescription)")
    }

    /// Show the banner even when the app is open — she may be mid-scroll when
    /// something better turns up.
    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        willPresent notification: UNNotification
    ) async -> UNNotificationPresentationOptions {
        [.banner, .sound, .list]
    }

    func userNotificationCenter(
        _ center: UNUserNotificationCenter,
        didReceive response: UNNotificationResponse
    ) async {
        let info = response.notification.request.content.userInfo
        if let dealId = info["deal_id"] as? Int {
            await MainActor.run { NotificationRouter.shared.pendingDealId = dealId }
        }
        await state?.refresh()
    }
}

/// Carries a tapped notification's deal id into the view layer.
@MainActor
final class NotificationRouter: ObservableObject {
    static let shared = NotificationRouter()
    @Published var pendingDealId: Int?
}

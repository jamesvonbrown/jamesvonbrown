import SwiftUI

struct RootView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        if state.isConfigured {
            MainTabView()
        } else {
            SetupView()
        }
    }
}

struct MainTabView: View {
    @EnvironmentObject private var state: AppState
    @ObservedObject private var router = NotificationRouter.shared
    @State private var selection = 0

    var body: some View {
        TabView(selection: $selection) {
            DealListView()
                .tabItem { Label("Deals", systemImage: "tag") }
                .tag(0)
            RunsView()
                .tabItem { Label("Runs", systemImage: "car") }
                .tag(1)
            SettingsView()
                .tabItem { Label("Settings", systemImage: "gearshape") }
                .tag(2)
        }
        // A tapped notification should land on that deal, not just open the app.
        .onChange(of: router.pendingDealId) { _, newValue in
            if newValue != nil { selection = 0 }
        }
    }
}

struct SetupView: View {
    @EnvironmentObject private var state: AppState
    @State private var urlString = ""
    @State private var token = ""
    @State private var connecting = false

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                Image(systemName: "arrow.up.right.circle.fill")
                    .font(.system(size: 56))
                    .foregroundStyle(Color.flipAccent)
                    .padding(.top, 40)

                Text("FlipScan").font(.largeTitle.bold())

                Text("Connect to your scanner. Both values are in the server's "
                     + ".env file.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                VStack(spacing: 10) {
                    TextField("https://your-server:8000", text: $urlString)
                        .textContentType(.URL)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                        .textInputAutocapitalization(.never)
                    SecureField("Access token", text: $token)
                        .textContentType(.password)
                }
                .textFieldStyle(.roundedBorder)
                .padding(.horizontal)

                if let error = state.errorMessage {
                    Text(error)
                        .font(.footnote)
                        .foregroundStyle(Color.flipDanger)
                        .multilineTextAlignment(.center)
                        .padding(.horizontal)
                }

                Button {
                    Task {
                        connecting = true
                        _ = await state.connect(urlString: urlString, token: token)
                        connecting = false
                    }
                } label: {
                    if connecting {
                        ProgressView().frame(maxWidth: .infinity)
                    } else {
                        Text("Connect").frame(maxWidth: .infinity)
                    }
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(token.isEmpty || urlString.isEmpty || connecting)
                .padding(.horizontal)

                Spacer(minLength: 40)
            }
        }
    }
}

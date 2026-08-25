import SwiftUI
import UIKit

struct SettingsView: View {
    @EnvironmentObject private var state: AppState
    @State private var confirmingDisconnect = false

    var body: some View {
        NavigationStack {
            List {
                if let status = state.status {
                    if !status.warnings.isEmpty {
                        Section {
                            ForEach(status.warnings, id: \.self) { warning in
                                CalloutBox(kind: .warn, title: nil, body: warning)
                                    .listRowInsets(EdgeInsets(top: 4, leading: 0,
                                                              bottom: 4, trailing: 0))
                                    .listRowBackground(Color.clear)
                            }
                        }
                    }

                    Section("Status") {
                        LabeledContent("Market", value: status.market)
                        LabeledContent("Listings tracked", value: "\(status.activeListings)")
                        LabeledContent("Open deals", value: "\(status.openDeals)")
                        LabeledContent("AI spend today",
                                       value: Format.money2(status.aiSpendToday.costUsd)
                                            + " of " + Format.money2(status.aiSpendToday.budgetUsd))
                        LabeledContent("Sources",
                                       value: status.collectors.joined(separator: ", "))
                        LabeledContent("Alerts via",
                                       value: status.notifyChannels.joined(separator: ", "))
                        LabeledContent("Scanner",
                                       value: status.scheduler.running ? "running" : "stopped")
                    }
                }

                Section("Notifications") {
                    Button("Enable push notifications") {
                        // Ask only when she taps: an unexplained permission
                        // prompt at first launch gets denied, and iOS will not
                        // ask a second time.
                        (UIApplication.shared.delegate as? AppDelegate)?
                            .requestPushPermission()
                    }
                    Text("Requires an Apple Developer account and APNs keys on "
                         + "the server. If you're using ntfy instead, alerts "
                         + "arrive through the ntfy app and this isn't needed.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section {
                    Text("Thresholds — the profit bar, how far to drive, the "
                         + "quality floor — live on the server so they apply to "
                         + "scanning too. Change them in the web app at "
                         + "/app/#/settings, or in the server's .env file.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                } header: {
                    Text("What counts as a deal")
                }

                Section {
                    Button("Disconnect this device", role: .destructive) {
                        confirmingDisconnect = true
                    }
                }
            }
            .navigationTitle("Settings")
            .refreshable { await state.refresh() }
            .confirmationDialog("Disconnect?", isPresented: $confirmingDisconnect) {
                Button("Disconnect", role: .destructive) { state.disconnect() }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("You'll need the server URL and token again to reconnect.")
            }
        }
        .task { await state.refresh() }
    }
}

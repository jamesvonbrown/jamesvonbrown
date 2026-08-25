import SwiftUI

struct RunsView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            List {
                if state.runs.isEmpty {
                    EmptyStateView(
                        symbol: "car",
                        title: "No runs yet",
                        message: "When two or more deals turn up close together, "
                               + "they show up here as a single trip. One drive, "
                               + "several pickups — that's where the margin on "
                               + "small items comes from.")
                        .listRowSeparator(.hidden)
                }

                ForEach(state.runs) { run in
                    VStack(alignment: .leading, spacing: 7) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(run.label).font(.headline)
                            Spacer()
                            Text(Format.money(run.profitAfterTrip))
                                .font(.title3.bold())
                                .foregroundStyle(Color.flipAccent)
                        }
                        Text("\(run.dealCount) pickups · "
                             + "\(Format.miles(run.distanceFromHome)) each way · "
                             + String(format: "about %.1fh", run.estHours))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text("Trip costs "
                             + Format.money(run.totalNetProfit - run.profitAfterTrip)
                             + ", charged once for the whole loop instead of per item.")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)

                        HStack(spacing: 8) {
                            ForEach(run.dealIds.prefix(4), id: \.self) { dealId in
                                NavigationLink(value: dealId) {
                                    Text("Deal \(dealId)").font(.caption.weight(.semibold))
                                }
                                .buttonStyle(.bordered)
                                .controlSize(.small)
                            }
                        }
                        .padding(.top, 2)
                    }
                    .padding(.vertical, 5)
                }
            }
            .listStyle(.plain)
            .navigationTitle("Pickup runs")
            .navigationDestination(for: Int.self) { DealDetailView(dealId: $0) }
            .refreshable { await state.refreshRuns() }
        }
        .task { await state.refreshRuns() }
    }
}

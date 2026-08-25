import SwiftUI

struct DealListView: View {
    @EnvironmentObject private var state: AppState
    // Shared singleton, so observe it — @StateObject would claim ownership
    // and re-create it.
    @ObservedObject private var router = NotificationRouter.shared
    @State private var scanning = false
    @State private var path = NavigationPath()

    private let sorts: [(String, String)] = [
        ("score", "Best"), ("profit", "Biggest $"),
        ("distance", "Closest"), ("newest", "Newest"),
    ]

    var body: some View {
        NavigationStack(path: $path) {
            List {
                if !state.deals.isEmpty {
                    Section {
                        HStack {
                            summaryTile("Open deals", "\(state.deals.count)")
                            summaryTile("If you got them all", Format.money(state.totalPotential))
                        }
                        .listRowInsets(EdgeInsets())
                        .listRowBackground(Color.clear)
                    }
                }

                if state.deals.isEmpty && !state.isLoading {
                    EmptyStateView(
                        symbol: "magnifyingglass",
                        title: "Nothing yet",
                        message: "Scans run every hour. Pull to refresh, tap the "
                               + "scan button, or lower the profit bar in Settings.")
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.clear)
                }

                ForEach(state.deals) { deal in
                    NavigationLink(value: deal.id) {
                        DealRow(deal: deal)
                    }
                    .swipeActions(edge: .trailing) {
                        Button(role: .destructive) {
                            Task { await state.act(on: deal.id, action: "passed") }
                        } label: { Label("Pass", systemImage: "xmark") }
                    }
                    .swipeActions(edge: .leading) {
                        Button {
                            Task { await state.act(on: deal.id, action: "saved") }
                        } label: { Label("Save", systemImage: "bookmark") }
                        .tint(Color.flipAccent)
                    }
                }
            }
            .listStyle(.plain)
            .navigationTitle(state.showingSaved ? "Saved" : "Deals")
            .navigationDestination(for: Int.self) { DealDetailView(dealId: $0) }
            .refreshable { await state.refresh() }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        Picker("Sort", selection: $state.sort) {
                            ForEach(sorts, id: \.0) { Text($0.1).tag($0.0) }
                        }
                        Toggle("Saved only", isOn: $state.showingSaved)
                    } label: {
                        Image(systemName: "line.3.horizontal.decrease.circle")
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        Task {
                            scanning = true
                            await state.scanNow()
                            scanning = false
                        }
                    } label: {
                        if scanning {
                            ProgressView()
                        } else {
                            Image(systemName: "arrow.clockwise")
                        }
                    }
                    .disabled(scanning)
                }
            }
            .onChange(of: state.sort) { _, _ in Task { await state.refresh() } }
            .onChange(of: state.showingSaved) { _, _ in Task { await state.refresh() } }
            // A tapped notification pushes that deal onto this stack. Using the
            // path avoids stacking a second navigationDestination modifier,
            // which conflicts with the value-based one above.
            .onChange(of: router.pendingDealId) { _, dealId in
                guard let dealId else { return }
                path.append(dealId)
                router.pendingDealId = nil
            }
        }
        .task { await state.refresh() }
    }

    private func summaryTile(_ key: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(key.uppercased())
                .font(.caption2.weight(.bold))
                .foregroundStyle(.tertiary)
            Text(value).font(.title3.bold())
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(Color(.secondarySystemGroupedBackground),
                    in: RoundedRectangle(cornerRadius: 11))
    }
}

struct DealRow: View {
    let deal: DealSummary

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            AsyncImage(url: URL(string: deal.imageUrl ?? "")) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().scaledToFill()
                default:
                    ZStack {
                        Color(.tertiarySystemFill)
                        Image(systemName: "shippingbox")
                            .foregroundStyle(.tertiary)
                    }
                }
            }
            .frame(width: 78, height: 78)
            .clipShape(RoundedRectangle(cornerRadius: 9))

            VStack(alignment: .leading, spacing: 4) {
                Text(deal.title)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(2)

                HStack(alignment: .firstTextBaseline, spacing: 6) {
                    Text(deal.profitText)
                        .font(.title2.bold())
                        .foregroundStyle(Color.flipAccent)
                    Text(Format.percent(deal.roiPct) + " ROI")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Text("buy \(Format.money(deal.buyPrice)) → sells \(Format.money(deal.resaleEstimate))")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                HStack(spacing: 4) {
                    Pill(text: "\(Int(deal.dealScore))", color: .flipAccent)
                    Pill(text: deal.conditionGrade, color: .grade(deal.conditionGrade))
                    Pill(text: Format.miles(deal.distanceMiles))
                    if deal.warningCount > 0 {
                        Pill(text: "⚠ \(deal.warningCount)", color: .flipWarn)
                    }
                    if deal.confidence < 0.35 {
                        Pill(text: "unverified", color: .flipDanger)
                    }
                }

                ConfidenceBar(confidence: deal.confidence)
                    .padding(.top, 2)
            }
        }
        .padding(.vertical, 4)
    }
}

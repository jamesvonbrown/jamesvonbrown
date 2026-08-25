import SwiftUI

struct DealDetailView: View {
    let dealId: Int

    @EnvironmentObject private var state: AppState
    @Environment(\.dismiss) private var dismiss
    @State private var deal: DealDetail?
    @State private var loadError: String?
    @State private var askingBoughtPrice = false
    @State private var boughtPrice = ""

    var body: some View {
        Group {
            if let deal {
                content(deal)
            } else if let loadError {
                EmptyStateView(symbol: "exclamationmark.triangle",
                               title: "Couldn't load", message: loadError)
            } else {
                ProgressView().frame(maxWidth: .infinity, minHeight: 240)
            }
        }
        .navigationTitle("Deal")
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
        .alert("What did you pay?", isPresented: $askingBoughtPrice) {
            TextField("Amount", text: $boughtPrice).keyboardType(.decimalPad)
            Button("Save") {
                Task {
                    await state.act(on: dealId, action: "bought",
                                    buyPrice: Double(boughtPrice))
                    dismiss()
                }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    private func load() async {
        do {
            deal = try await APIClient.shared.deal(dealId)
        } catch {
            loadError = error.localizedDescription
        }
    }

    @ViewBuilder
    private func content(_ deal: DealDetail) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                photoStrip(deal)

                VStack(alignment: .leading, spacing: 4) {
                    Text(deal.title).font(.title3.bold())
                    Text(subtitle(deal)).font(.footnote).foregroundStyle(.secondary)
                }

                // Warnings before the profit number. If something is wrong with
                // a deal she should read it before she gets excited about it.
                ForEach(deal.warnings, id: \.self) { warning in
                    CalloutBox(kind: .warn, title: nil, body: warning)
                }

                profitHeadline(deal)
                actionButtons(deal)
                moneySection(deal)
                driveSection(deal)
                conditionSection(deal)

                if !deal.inspectionChecklist.isEmpty {
                    SectionCard(title: "Check before you pay") {
                        ForEach(deal.inspectionChecklist, id: \.self) { item in
                            Label(item, systemImage: "checkmark.circle")
                                .font(.subheadline)
                        }
                    }
                }

                SectionCard(title: "Why this scored \(Int(deal.dealScore))") {
                    ForEach(deal.reasons, id: \.self) { reason in
                        Text("• " + reason).font(.subheadline)
                    }
                }

                compsSection(deal)
                safetySection(deal)

                if !deal.description.isEmpty {
                    SectionCard(title: "Seller's description") {
                        Text(deal.description).font(.subheadline)
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 32)
        }
    }

    private func subtitle(_ deal: DealDetail) -> String {
        var parts = [deal.location ?? "Unknown location", Format.miles(deal.distanceMiles)]
        parts.append("found " + Format.ago(deal.createdAt))
        if let seller = deal.sellerName { parts.append(seller) }
        return parts.joined(separator: " · ")
    }

    @ViewBuilder
    private func photoStrip(_ deal: DealDetail) -> some View {
        if deal.imageUrls.isEmpty {
            EmptyView()
        } else {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(deal.imageUrls, id: \.self) { url in
                        AsyncImage(url: URL(string: url)) { phase in
                            switch phase {
                            case .success(let image): image.resizable().scaledToFill()
                            case .failure: Color(.tertiarySystemFill)
                            default: ProgressView()
                            }
                        }
                        .frame(width: 260, height: 200)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
            }
            .padding(.top, 8)
        }
    }

    private func profitHeadline(_ deal: DealDetail) -> some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(Format.money(deal.money.netProfit))
                .font(.system(size: 34, weight: .heavy))
                .foregroundStyle(Color.flipAccent)
            VStack(alignment: .leading, spacing: 0) {
                Text(Format.percent(deal.money.roiPct) + " ROI").font(.footnote)
                Text("after everything").font(.footnote).foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(14)
        .background(Color.flipAccent.opacity(0.12),
                    in: RoundedRectangle(cornerRadius: 14))
    }

    private func actionButtons(_ deal: DealDetail) -> some View {
        VStack(spacing: 9) {
            if let url = URL(string: deal.listingUrl) {
                Link(destination: url) {
                    Text("Open the listing").frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
            }
            HStack(spacing: 9) {
                Button("Save") {
                    Task { await state.act(on: deal.id, action: "saved") }
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.bordered)
                .controlSize(.large)

                Button("Pass", role: .destructive) {
                    Task {
                        await state.act(on: deal.id, action: "passed")
                        dismiss()
                    }
                }
                .frame(maxWidth: .infinity)
                .buttonStyle(.bordered)
                .controlSize(.large)
            }
            Button("I bought it") { askingBoughtPrice = true }
                .frame(maxWidth: .infinity)
                .buttonStyle(.bordered)
                .controlSize(.large)
        }
    }

    private func moneySection(_ deal: DealDetail) -> some View {
        let money = deal.money
        return SectionCard(title: "The money") {
            MoneyRow(label: "Asking price", value: money.buyPrice)
            MoneyRow(label: "Expected resale", value: money.resaleEstimate)
            HStack {
                Text("Range").foregroundStyle(.secondary)
                Spacer()
                Text("\(Format.money(money.resaleLow)) – \(Format.money(money.resaleHigh))")
                    .foregroundStyle(.secondary)
                    .monospacedDigit()
            }
            if money.platformFees > 0 {
                MoneyRow(label: "Platform fees", value: money.platformFees, isCost: true)
            }
            if money.shippingCost > 0 {
                MoneyRow(label: "Shipping & supplies", value: money.shippingCost, isCost: true)
            }
            if money.refurbCost > 0 {
                MoneyRow(label: "Clean-up / repair", value: money.refurbCost, isCost: true)
            }
            if money.tripCost > 0 {
                MoneyRow(label: "Getting there", value: money.tripCost, isCost: true)
            }
            Divider()
            MoneyRow(label: "You keep", value: money.netProfit, emphasize: true)
        }
    }

    private func driveSection(_ deal: DealDetail) -> some View {
        SectionCard(title: "The drive") {
            HStack {
                Text("Distance").foregroundStyle(.secondary)
                Spacer()
                Text(Format.miles(deal.distanceMiles)).fontWeight(.semibold)
            }
            HStack {
                Text("Worth driving up to").foregroundStyle(.secondary)
                Spacer()
                Text(Format.miles(deal.maxWorthDrivingMiles)).fontWeight(.semibold)
            }
            HStack {
                Text("Size").foregroundStyle(.secondary)
                Spacer()
                Text(deal.bulkClass.replacingOccurrences(of: "_", with: " "))
                    .fontWeight(.semibold)
            }
        }
    }

    private func conditionSection(_ deal: DealDetail) -> some View {
        let condition = deal.condition
        let title = "Condition — grade \(condition.grade)"
            + (condition.analyzedByAi ? "" : " (from the text only)")
        return SectionCard(title: title) {
            if !condition.summary.isEmpty {
                Text(condition.summary).font(.subheadline)
            }
            if condition.usesStockPhotos {
                CalloutBox(kind: .warn, title: nil,
                           body: "Stock photos — you can't see the actual item.")
            }
            ForEach(condition.damageFlags, id: \.self) { flag in
                Label(flag, systemImage: "exclamationmark.triangle")
                    .font(.subheadline).foregroundStyle(Color.flipWarn)
            }
            ForEach(condition.missingParts, id: \.self) { part in
                Label("Missing: " + part, systemImage: "minus.circle")
                    .font(.subheadline).foregroundStyle(Color.flipWarn)
            }
            ForEach(condition.positiveSignals, id: \.self) { signal in
                Label(signal, systemImage: "checkmark.circle")
                    .font(.subheadline).foregroundStyle(Color.flipAccent)
            }
        }
    }

    private func compsSection(_ deal: DealDetail) -> some View {
        let comps = deal.comps
        return SectionCard(title: "What it's worth") {
            HStack {
                Text("Estimate").foregroundStyle(.secondary)
                Spacer()
                Text("\(Format.money(comps.estimateLow)) – \(Format.money(comps.estimateHigh))")
                    .fontWeight(.semibold).monospacedDigit()
            }
            HStack {
                Text("Based on").foregroundStyle(.secondary)
                Spacer()
                Text("\(comps.sampleSize) comparable\(comps.sampleSize == 1 ? "" : "s")")
                    .fontWeight(.semibold)
            }
            if let days = comps.estDaysToSell {
                HStack {
                    Text("Typical time to sell").foregroundStyle(.secondary)
                    Spacer()
                    Text("\(days) days").fontWeight(.semibold)
                }
            }
            if !comps.method.isEmpty {
                Text(comps.method).font(.caption).foregroundStyle(.secondary)
            }
            ForEach(comps.sources ?? [], id: \.self) { source in
                if let examples = source.examples, !examples.isEmpty {
                    Text(source.provider.uppercased())
                        .font(.caption2.weight(.bold))
                        .foregroundStyle(.tertiary)
                        .padding(.top, 4)
                    ForEach(Array(examples.prefix(4)), id: \.self) { example in
                        HStack {
                            if let url = URL(string: example.url), !example.url.isEmpty {
                                Link(example.title, destination: url)
                                    .font(.caption).lineLimit(1)
                            } else {
                                Text(example.title).font(.caption).lineLimit(1)
                            }
                            Spacer()
                            Text(Format.money(example.price))
                                .font(.caption.weight(.semibold))
                                .foregroundStyle(Color.flipAccent)
                        }
                    }
                }
            }
        }
    }

    private func safetySection(_ deal: DealDetail) -> some View {
        SectionCard(title: "Meeting the seller") {
            CalloutBox(kind: deal.safety.level == "high" ? .danger : .info,
                       title: deal.safety.headline,
                       body: deal.safety.rules.prefix(4)
                           .map { "• " + $0 }.joined(separator: "\n"))
            Text(deal.safety.paymentNote).font(.caption).foregroundStyle(.secondary)
        }
    }
}

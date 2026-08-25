import SwiftUI
import UIKit

extension Color {
    static let flipAccent = Color(red: 0.06, green: 0.72, blue: 0.51)
    static let flipWarn   = Color(red: 0.96, green: 0.62, blue: 0.04)
    static let flipDanger = Color(red: 0.96, green: 0.25, blue: 0.35)

    /// Condition grades read fastest as colour; A is green through F is red.
    static func grade(_ letter: String) -> Color {
        switch letter.uppercased() {
        case "A": return flipAccent
        case "B": return Color(red: 0.29, green: 0.87, blue: 0.50)
        case "C": return Color(red: 0.98, green: 0.75, blue: 0.14)
        case "D": return Color(red: 0.98, green: 0.57, blue: 0.24)
        default:  return flipDanger
        }
    }
}

/// Small rounded label used for score, grade, distance, warnings.
struct Pill: View {
    let text: String
    var color: Color = .secondary
    var filled = false

    var body: some View {
        Text(text)
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 7)
            .padding(.vertical, 3)
            .background(filled ? color.opacity(0.9) : color.opacity(0.14),
                        in: RoundedRectangle(cornerRadius: 6))
            .foregroundStyle(filled ? Color.white : color)
    }
}

/// A labelled money line. `isCost` renders the value as a negative.
struct MoneyRow: View {
    let label: String
    let value: Double
    var isCost = false
    var emphasize = false

    var body: some View {
        HStack {
            Text(label)
                .foregroundStyle(.secondary)
                .font(emphasize ? .body.weight(.semibold) : .body)
            Spacer()
            Text(isCost ? "−" + Format.money2(value) : Format.money2(value))
                .font(emphasize ? .title3.weight(.bold) : .body.weight(.semibold))
                .foregroundStyle(emphasize ? Color.flipAccent
                                 : (isCost ? Color.secondary : Color.primary))
                .monospacedDigit()
        }
    }
}

/// A thin bar communicating comp confidence without making her read a number.
struct ConfidenceBar: View {
    let confidence: Double

    private var color: Color {
        confidence < 0.35 ? .flipDanger : (confidence < 0.6 ? .flipWarn : .flipAccent)
    }

    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                Capsule().fill(Color.secondary.opacity(0.18))
                Capsule().fill(color)
                    .frame(width: max(3, geometry.size.width * confidence))
            }
        }
        .frame(height: 3)
    }
}

struct SectionCard<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title.uppercased())
                .font(.caption2.weight(.bold))
                .foregroundStyle(.tertiary)
                .kerning(0.6)
            VStack(alignment: .leading, spacing: 8) { content }
                .padding(13)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.secondarySystemGroupedBackground),
                            in: RoundedRectangle(cornerRadius: 14))
        }
    }
}

struct CalloutBox: View {
    enum Kind { case warn, danger, info }
    let kind: Kind
    let title: String?
    let body: String

    private var tint: Color {
        switch kind {
        case .warn:   return .flipWarn
        case .danger: return .flipDanger
        case .info:   return .blue
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let title {
                Text(title).font(.subheadline.weight(.bold))
            }
            Text(body).font(.subheadline)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(11)
        .background(tint.opacity(0.12), in: RoundedRectangle(cornerRadius: 11))
        .overlay(RoundedRectangle(cornerRadius: 11).stroke(tint.opacity(0.35), lineWidth: 1))
    }
}

struct EmptyStateView: View {
    let symbol: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 10) {
            Image(systemName: symbol)
                .font(.system(size: 38))
                .foregroundStyle(.tertiary)
            Text(title).font(.headline)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .frame(maxWidth: 300)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 56)
    }
}

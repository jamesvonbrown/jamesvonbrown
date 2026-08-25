import Foundation

// Mirrors of the server's response schemas in server/flipscan/api/schemas.py.
// The decoder converts snake_case automatically, so field names here are the
// camelCase equivalents of the JSON keys.

struct DealSummary: Codable, Identifiable, Hashable {
    let id: Int
    let title: String
    let buyPrice: Double
    let netProfit: Double
    let roiPct: Double
    let resaleEstimate: Double
    let dealScore: Double
    let confidence: Double
    let riskScore: Double
    let distanceMiles: Double
    let maxWorthDrivingMiles: Double
    let worthTheDrive: Bool
    let bulkClass: String
    let conditionGrade: String
    let location: String?
    let imageUrl: String?
    let listingUrl: String
    let status: String
    let category: String?
    let estDaysToSell: Int?
    let warningCount: Int
    let createdAt: Date
    let postedAt: Date?
}

struct MoneyBreakdown: Codable, Hashable {
    let buyPrice: Double
    let resaleEstimate: Double
    let resaleLow: Double
    let resaleHigh: Double
    let grossSpread: Double
    let platformFees: Double
    let shippingCost: Double
    let refurbCost: Double
    let tripCost: Double
    let netProfit: Double
    let roiPct: Double
    let venue: String
}

struct ConditionInfo: Codable, Hashable {
    let grade: String
    let score: Double
    let summary: String
    let functionalStatus: String
    let damageFlags: [String]
    let missingParts: [String]
    let positiveSignals: [String]
    let photoQuality: String
    let photoCaveats: [String]
    let usesStockPhotos: Bool
    let identifiedBrand: String?
    let identifiedModel: String?
    let analyzedByAi: Bool
}

struct CompExample: Codable, Hashable {
    let title: String
    let price: Double
    let url: String
    let sold: Bool
}

struct CompSource: Codable, Hashable {
    let provider: String
    let n: Int
    let median: Double
    let note: String?
    let examples: [CompExample]?
}

struct CompsInfo: Codable, Hashable {
    let estimateLow: Double
    let estimateMid: Double
    let estimateHigh: Double
    let confidence: Double
    let sampleSize: Int
    let estDaysToSell: Int?
    let method: String
    let queryUsed: String
    // The server nests arbitrary provider payloads here. Decoding it loosely
    // keeps a schema change on the server from breaking the whole screen.
    let sources: [CompSource]?

    enum CodingKeys: String, CodingKey {
        case estimateLow, estimateMid, estimateHigh, confidence
        case sampleSize, estDaysToSell, method, queryUsed, sources
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        estimateLow = try c.decodeIfPresent(Double.self, forKey: .estimateLow) ?? 0
        estimateMid = try c.decodeIfPresent(Double.self, forKey: .estimateMid) ?? 0
        estimateHigh = try c.decodeIfPresent(Double.self, forKey: .estimateHigh) ?? 0
        confidence = try c.decodeIfPresent(Double.self, forKey: .confidence) ?? 0
        sampleSize = try c.decodeIfPresent(Int.self, forKey: .sampleSize) ?? 0
        estDaysToSell = try c.decodeIfPresent(Int.self, forKey: .estDaysToSell)
        method = try c.decodeIfPresent(String.self, forKey: .method) ?? ""
        queryUsed = try c.decodeIfPresent(String.self, forKey: .queryUsed) ?? ""
        sources = try? c.decodeIfPresent([CompSource].self, forKey: .sources)
    }
}

struct SafetyInfo: Codable, Hashable {
    let level: String
    let headline: String
    let rules: [String]
    let paymentNote: String
}

struct PricePoint: Codable, Hashable {
    let price: Double
    let at: Date
}

struct DealDetail: Codable, Identifiable, Hashable {
    let id: Int
    let title: String
    let buyPrice: Double
    let netProfit: Double
    let roiPct: Double
    let resaleEstimate: Double
    let dealScore: Double
    let confidence: Double
    let riskScore: Double
    let distanceMiles: Double
    let maxWorthDrivingMiles: Double
    let worthTheDrive: Bool
    let bulkClass: String
    let conditionGrade: String
    let location: String?
    let imageUrl: String?
    let listingUrl: String
    let status: String
    let category: String?
    let estDaysToSell: Int?
    let warningCount: Int
    let createdAt: Date
    let postedAt: Date?

    let description: String
    let sellerName: String?
    let money: MoneyBreakdown
    let condition: ConditionInfo
    let comps: CompsInfo
    let safety: SafetyInfo
    let reasons: [String]
    let warnings: [String]
    let inspectionChecklist: [String]
    let imageUrls: [String]
    let screenshotUrl: String?
    let priceHistory: [PricePoint]
    let firstSeenPrice: Double
}

struct PickupRun: Codable, Identifiable, Hashable {
    var id: String { label + "-" + dealIds.map(String.init).joined(separator: ",") }
    let label: String
    let centerLat: Double
    let centerLon: Double
    let dealIds: [Int]
    let dealCount: Int
    let distanceFromHome: Double
    let totalNetProfit: Double
    let profitAfterTrip: Double
    let estHours: Double
    let summary: String
}

struct AiSpend: Codable, Hashable {
    let costUsd: Double
    let budgetUsd: Double
    let calls: Int
}

struct SchedulerStatus: Codable, Hashable {
    let running: Bool
    let nextRun: String?
    let lastRun: String?
}

struct ServerStatus: Codable, Hashable {
    let activeListings: Int
    let openDeals: Int
    let aiSpendToday: AiSpend
    let scheduler: SchedulerStatus
    let collectors: [String]
    let notifyChannels: [String]
    let market: String
    let warnings: [String]
}

struct FeedbackPayload: Codable {
    var action: String
    var actualBuyPrice: Double?
    var actualSalePrice: Double?
    var actualDaysToSell: Int?
    var soldVenue: String?
    var note: String = ""
}

// MARK: - Presentation helpers

extension DealSummary {
    var profitText: String { Format.money(netProfit) }
    var confidenceLabel: String {
        switch confidence {
        case 0.75...:  return "well supported"
        case 0.5..<0.75: return "reasonable"
        case 0.3..<0.5:  return "thin"
        default:         return "a guess"
        }
    }
}

enum Format {
    static func money(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        formatter.maximumFractionDigits = 0
        return formatter.string(from: NSNumber(value: value)) ?? "$0"
    }

    static func money2(_ value: Double) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "USD"
        formatter.minimumFractionDigits = 2
        formatter.maximumFractionDigits = 2
        return formatter.string(from: NSNumber(value: value)) ?? "$0.00"
    }

    static func miles(_ value: Double) -> String {
        value < 10 ? String(format: "%.1f mi", value) : String(format: "%.0f mi", value)
    }

    static func percent(_ value: Double) -> String { String(format: "%.0f%%", value) }

    static func ago(_ date: Date) -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}

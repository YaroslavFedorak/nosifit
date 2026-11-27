import SwiftUI

/// The design tokens of frontend/src/design/tokens.ts, converted from OKLCH to sRGB.
enum NosiColor {
    static let paper = Color(hex: 0x0B0E14)
    static let paper2 = Color(hex: 0x13171E)
    static let paper3 = Color(hex: 0x1C2128)
    static let paper4 = Color(hex: 0x272D36)
    static let rule = Color(hex: 0x272C32)
    static let ink = Color(hex: 0xECEFF3)
    static let ink2 = Color(hex: 0xC3C8CF)
    static let muted = Color(hex: 0x969CA6)
    static let accent = Color(hex: 0xEAC25A)
    static let accentInk = Color(hex: 0x211A06)
    static let training = Color(hex: 0xEAC25A)
    static let nutrition = Color(hex: 0xB098E7)
    static let recovery = Color(hex: 0x6DC5CA)
    static let water = Color(hex: 0x6DABDF)
    static let success = Color(hex: 0x73CA99)
    static let error = Color(hex: 0xEC7B79)
}

enum NosiSpace {
    static let xs: CGFloat = 8
    static let sm: CGFloat = 12
    static let md: CGFloat = 16
    static let lg: CGFloat = 24
    static let xl: CGFloat = 40
}

extension Color {
    init(hex: UInt32) {
        self.init(
            .sRGB,
            red: Double((hex >> 16) & 0xFF) / 255,
            green: Double((hex >> 8) & 0xFF) / 255,
            blue: Double(hex & 0xFF) / 255
        )
    }
}

/// A card on the paper2 surface, as on the website.
struct CardStyle: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(NosiSpace.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(NosiColor.paper2, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
    }
}

extension View {
    func card() -> some View { modifier(CardStyle()) }
}

/// A user-facing message for a failed call.
func message(for error: Error) -> LocalizedStringKey {
    switch (error as? APIError)?.code {
    case "invalid_credentials": return "error.invalid_credentials"
    case "rate_limited", "too_many_attempts": return "error.rate_limited"
    case "invalid_input": return "error.invalid_input"
    default: return (error as? APIError) == .network ? "error.network" : "error.generic"
    }
}

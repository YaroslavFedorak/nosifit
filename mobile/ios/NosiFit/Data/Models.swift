import Foundation

// Shapes of the NosiFit JSON API (docs/openapi.json). Keys are snake_case on
// the wire and converted by APIClient; unknown fields are ignored.

struct MobileUser: Codable, Equatable {
    let id: Int
    let name: String
    let email: String
}

struct Features: Codable, Equatable {
    var planGeneration: Bool = false
}

struct LoginRequest: Encodable {
    let email: String
    let password: String
    var platform: String = "ios"
    let deviceName: String?
}

struct LoginResponse: Decodable {
    let token: String
    let expiresAt: String
    let user: MobileUser
    let consentRequired: Bool
    let features: Features?
}

struct SessionInfo: Decodable {
    let user: MobileUser
    let consentRequired: Bool
    let features: Features?
}

struct ConsentRequest: Encodable {
    let privacyConsent: Bool
    let healthConsent: Bool
    let ageConfirmed: Bool
}

struct StatusResponse: Decodable {
    let status: String
}

struct EmptyBody: Encodable {}

struct DashboardToday: Decodable, Equatable {
    let date: String
    let dailyScore: Double?
    let training: Training
    let nutrition: Nutrition
    let recovery: Recovery

    struct Training: Decodable, Equatable {
        let completed: Bool
        let duration: Double
        let exerciseCount: Int
        let score: Double?
    }

    struct Nutrition: Decodable, Equatable {
        let calories: Double
        let protein: Double
        let water: Double
        let score: Double?
    }

    struct Recovery: Decodable, Equatable {
        let habitsCompleted: Int
        let habitsTotal: Int
        let sleepHours: Double
        let score: Double?
    }
}

struct APIErrorBody: Decodable {
    let code: String?
    let message: String?
}

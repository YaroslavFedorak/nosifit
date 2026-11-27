import Foundation
import UIKit

enum SessionState: Equatable {
    case loading
    case signedOut
    case signedIn(user: MobileUser, consentRequired: Bool)
}

/// Who is signed in, and the calls that change it. The token stays in the
/// Keychain; only the account shown on screen is cached in UserDefaults so
/// the app opens without waiting for the network.
@MainActor
final class Session: ObservableObject {
    @Published private(set) var state: SessionState = .loading

    private let vault: TokenVault
    private let defaults: UserDefaults
    private let tokenBox: TokenBox
    private(set) var api: APIClient!

    init(vault: TokenVault = KeychainTokenVault(), defaults: UserDefaults = .standard) {
        self.vault = vault
        self.defaults = defaults
        self.tokenBox = TokenBox(vault.read())
        let box = tokenBox
        let defaults = defaults
        self.api = APIClient(
            baseURL: { Session.serverURL(in: defaults) },
            token: { box.value },
            onUnauthorized: { [weak self] in
                Task { @MainActor in self?.forget() }
            }
        )
    }

    var serverURL: URL { Session.serverURL(in: defaults) }

    var serverAddress: String {
        get { serverURL.absoluteString }
        set { defaults.set(Session.normalizeServerAddress(newValue), forKey: Keys.server) }
    }

    /// On launch: show the cached account at once, then ask the server whether the token still works.
    func restore() async {
        guard tokenBox.value != nil,
              let data = defaults.data(forKey: Keys.user),
              let cached = try? JSONDecoder().decode(MobileUser.self, from: data) else {
            forget()
            return
        }
        state = .signedIn(user: cached, consentRequired: defaults.bool(forKey: Keys.consent))
        do {
            let info: SessionInfo = try await api.get("mobile/auth/session")
            remember(info.user, consentRequired: info.consentRequired)
        } catch {
            // Offline: keep the cached account. A rejected token already signed out.
        }
    }

    func signIn(email: String, password: String) async throws {
        let request = LoginRequest(
            email: email.trimmingCharacters(in: .whitespacesAndNewlines),
            password: password,
            deviceName: String(UIDevice.current.name.prefix(64))
        )
        let response: LoginResponse = try await api.post("mobile/auth/login", request)
        tokenBox.value = response.token
        vault.write(response.token)
        remember(response.user, consentRequired: response.consentRequired)
    }

    func giveConsent() async throws {
        let _: StatusResponse = try await api.post(
            "consent",
            ConsentRequest(privacyConsent: true, healthConsent: true, ageConfirmed: true)
        )
        if case let .signedIn(user, _) = state {
            remember(user, consentRequired: false)
        }
    }

    func signOut() async {
        let _: StatusResponse? = try? await api.post("mobile/auth/logout", EmptyBody())
        forget()
    }

    private func remember(_ user: MobileUser, consentRequired: Bool) {
        defaults.set(try? JSONEncoder().encode(user), forKey: Keys.user)
        defaults.set(consentRequired, forKey: Keys.consent)
        state = .signedIn(user: user, consentRequired: consentRequired)
    }

    private func forget() {
        tokenBox.value = nil
        vault.write(nil)
        defaults.removeObject(forKey: Keys.user)
        defaults.removeObject(forKey: Keys.consent)
        state = .signedOut
    }

    // MARK: - Server address

    private enum Keys {
        static let server = "nosifit.server"
        static let user = "nosifit.user"
        static let consent = "nosifit.consentRequired"
    }

    nonisolated static var defaultServerAddress: String {
        (Bundle.main.object(forInfoDictionaryKey: "NosiFitAPIURL") as? String) ?? "http://localhost:5000/"
    }

    nonisolated static func serverURL(in defaults: UserDefaults) -> URL {
        let address = defaults.string(forKey: Keys.server) ?? normalizeServerAddress(defaultServerAddress)
        return URL(string: address) ?? URL(string: "http://localhost:5000/")!
    }

    nonisolated static func normalizeServerAddress(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        let withScheme = trimmed.hasPrefix("http://") || trimmed.hasPrefix("https://") ? trimmed : "https://" + trimmed
        return withScheme.hasSuffix("/") ? withScheme : withScheme + "/"
    }
}

/// The current token, readable from the API client's background work.
final class TokenBox: @unchecked Sendable {
    private let lock = NSLock()
    private var token: String?

    init(_ token: String?) { self.token = token }

    var value: String? {
        get { lock.withLock { token } }
        set { lock.withLock { token = newValue } }
    }
}

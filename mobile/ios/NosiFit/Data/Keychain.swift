import Foundation
import Security

/// Where the sign-in token is kept between launches.
protocol TokenVault: Sendable {
    func read() -> String?
    func write(_ token: String?)
}

/// The token in the Keychain, readable only on this device after its first unlock
/// (not in backups, not moved to a new phone).
struct KeychainTokenVault: TokenVault {
    private let service = "com.nosifit.app.token"
    private let account = "api"

    private var query: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: account]
    }

    func read() -> String? {
        var query = self.query
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func write(_ token: String?) {
        SecItemDelete(query as CFDictionary)
        guard let token else { return }
        var item = query
        item[kSecValueData as String] = Data(token.utf8)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(item as CFDictionary, nil)
    }
}

/// For tests and previews.
final class MemoryTokenVault: TokenVault, @unchecked Sendable {
    private let lock = NSLock()
    private var token: String?

    init(_ token: String? = nil) { self.token = token }

    func read() -> String? { lock.withLock { token } }
    func write(_ token: String?) { lock.withLock { self.token = token } }
}

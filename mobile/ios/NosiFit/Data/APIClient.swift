import Foundation

enum APIError: Error, Equatable {
    /// The server answered with an error; `code` is the API's stable reason ("invalid_credentials").
    case server(status: Int, code: String?, message: String)
    /// No connection, or an answer that is not the API (a captive portal page).
    case network

    var code: String? {
        if case let .server(_, code, _) = self { return code }
        return nil
    }
}

/// Calls the NosiFit JSON API under /api/v1/ with the bearer token.
///
/// The session is ephemeral: no cookies or cache on disk, the app only ever
/// holds the token (in the Keychain).
final class APIClient: @unchecked Sendable {
    private let baseURL: @Sendable () -> URL
    private let token: @Sendable () -> String?
    private let onUnauthorized: @Sendable () -> Void
    private let session: URLSession

    private let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()

    private let encoder: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()

    /// Codes after which the stored token is useless (expired, revoked, password changed).
    private static let sessionLost: Set<String> = ["authentication_required", "session_revoked"]

    init(
        baseURL: @escaping @Sendable () -> URL,
        token: @escaping @Sendable () -> String?,
        onUnauthorized: @escaping @Sendable () -> Void,
        configuration: URLSessionConfiguration = .ephemeral
    ) {
        self.baseURL = baseURL
        self.token = token
        self.onUnauthorized = onUnauthorized
        configuration.timeoutIntervalForRequest = 30
        configuration.httpCookieStorage = nil
        configuration.httpShouldSetCookies = false
        self.session = URLSession(configuration: configuration)
    }

    func get<T: Decodable>(_ path: String, as type: T.Type = T.self) async throws -> T {
        try await send("GET", path, body: nil)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, _ body: B, as type: T.Type = T.self) async throws -> T {
        try await send("POST", path, body: try encoder.encode(body))
    }

    private func send<T: Decodable>(_ method: String, _ path: String, body: Data?) async throws -> T {
        guard let url = URL(string: "api/v1/" + path, relativeTo: baseURL()) else { throw APIError.network }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.setValue(Locale.preferredLanguages.first ?? "en", forHTTPHeaderField: "Accept-Language")
        if let token = token() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if method != "GET" {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = body ?? Data("{}".utf8)
        }

        let result: (Data, URLResponse)
        do {
            result = try await session.data(for: request)
        } catch {
            throw APIError.network
        }
        let (data, response) = result
        guard let http = response as? HTTPURLResponse else { throw APIError.network }

        guard (200..<300).contains(http.statusCode) else {
            let error = try? decoder.decode(APIErrorBody.self, from: data)
            if http.statusCode == 401, let code = error?.code, Self.sessionLost.contains(code) {
                onUnauthorized()
            }
            throw APIError.server(status: http.statusCode, code: error?.code, message: error?.message ?? "HTTP \(http.statusCode)")
        }
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.network
        }
    }
}

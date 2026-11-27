import XCTest
@testable import NosiFit

/// Answers every request of the test session with a canned response.
final class StubProtocol: URLProtocol {
    static var status = 200
    static var body = Data()
    static var lastRequest: URLRequest?
    static var lastBody: Data?

    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest { request }

    override func startLoading() {
        Self.lastRequest = request
        Self.lastBody = request.httpBody ?? request.httpBodyStream.map { stream in
            stream.open()
            defer { stream.close() }
            var data = Data()
            var buffer = [UInt8](repeating: 0, count: 4096)
            while stream.hasBytesAvailable {
                let read = stream.read(&buffer, maxLength: buffer.count)
                if read <= 0 { break }
                data.append(buffer, count: read)
            }
            return data
        }
        let response = HTTPURLResponse(url: request.url!, statusCode: Self.status, httpVersion: nil, headerFields: nil)!
        client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
        client?.urlProtocol(self, didLoad: Self.body)
        client?.urlProtocolDidFinishLoading(self)
    }

    override func stopLoading() {}
}

final class APIClientTests: XCTestCase {
    private var lostSession = false

    private func client(token: String? = nil) -> APIClient {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [StubProtocol.self]
        return APIClient(
            baseURL: { URL(string: "https://nosifit.example/")! },
            token: { token },
            onUnauthorized: { [weak self] in self?.lostSession = true },
            configuration: configuration
        )
    }

    private func stub(_ status: Int, _ json: String) {
        StubProtocol.status = status
        StubProtocol.body = Data(json.utf8)
    }

    func testLoginPostsSnakeCaseJSONToTheV1Path() async throws {
        stub(200, """
        {"token":"nfm_abc","token_type":"Bearer","expires_at":"2027-01-01T00:00:00+00:00",
         "user":{"id":7,"name":"Ann","email":"ann@example.com"},"consent_required":false,
         "features":{"plan_generation":true},"something_new":1}
        """)
        let response: LoginResponse = try await client().post(
            "mobile/auth/login", LoginRequest(email: "ann@example.com", password: "secret", deviceName: "iPhone")
        )

        let request = try XCTUnwrap(StubProtocol.lastRequest)
        XCTAssertEqual(request.httpMethod, "POST")
        XCTAssertEqual(request.url?.absoluteString, "https://nosifit.example/api/v1/mobile/auth/login")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
        let sent = try JSONSerialization.jsonObject(with: XCTUnwrap(StubProtocol.lastBody)) as? [String: Any]
        XCTAssertEqual(sent?["platform"] as? String, "ios")
        XCTAssertEqual(sent?["device_name"] as? String, "iPhone")
        XCTAssertEqual(response.token, "nfm_abc")
        XCTAssertEqual(response.user.id, 7)
        XCTAssertEqual(response.features?.planGeneration, true)
    }

    func testTheTokenIsSentAsBearer() async throws {
        stub(200, """
        {"date":"2026-11-27","daily_score":72.5,
         "training":{"completed":true,"duration":45,"exercise_count":6,"score":80},
         "nutrition":{"calories":1850.4,"protein":120,"water":1.5,"score":null},
         "recovery":{"habits_completed":2,"habits_total":4,"sleep_hours":7.5,"score":65}}
        """)
        let today: DashboardToday = try await client(token: "nfm_xyz").get("dashboard/today")

        XCTAssertEqual(StubProtocol.lastRequest?.value(forHTTPHeaderField: "Authorization"), "Bearer nfm_xyz")
        XCTAssertEqual(today.dailyScore, 72.5)
        XCTAssertEqual(today.training.exerciseCount, 6)
        XCTAssertNil(today.nutrition.score)
    }

    func testErrorsCarryTheAPICode() async {
        stub(401, #"{"code":"invalid_credentials","message":"Wrong email or password"}"#)
        do {
            let _: LoginResponse = try await client().post(
                "mobile/auth/login", LoginRequest(email: "a@b.c", password: "x", deviceName: nil)
            )
            XCTFail("expected an error")
        } catch {
            XCTAssertEqual((error as? APIError)?.code, "invalid_credentials")
        }
        XCTAssertFalse(lostSession, "wrong credentials are not a lost session")
    }

    func testARejectedTokenSignsOut() async {
        stub(401, #"{"code":"authentication_required","message":"x"}"#)
        let _: DashboardToday? = try? await client(token: "nfm_old").get("dashboard/today")
        XCTAssertTrue(lostSession)
    }

    func testAPageInsteadOfJSONIsANetworkError() async {
        stub(200, "<html>captive portal</html>")
        do {
            let _: DashboardToday = try await client().get("dashboard/today")
            XCTFail("expected an error")
        } catch {
            XCTAssertEqual(error as? APIError, .network)
        }
    }

    func testServerAddressesAreNormalized() {
        XCTAssertEqual(Session.normalizeServerAddress(" nosifit.example "), "https://nosifit.example/")
        XCTAssertEqual(Session.normalizeServerAddress("http://localhost:5000"), "http://localhost:5000/")
    }
}

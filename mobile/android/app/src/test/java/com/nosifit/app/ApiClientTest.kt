package com.nosifit.app

import com.nosifit.app.data.ApiClient
import com.nosifit.app.data.ApiException
import com.nosifit.app.data.DashboardToday
import com.nosifit.app.data.LoginRequest
import com.nosifit.app.data.LoginResponse
import com.nosifit.app.data.NetworkException
import com.nosifit.app.data.Session
import kotlinx.coroutines.test.runTest
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test

class ApiClientTest {
    private lateinit var server: MockWebServer
    private var token: String? = null
    private var lostSession = false

    private fun client() = ApiClient(
        baseUrl = { server.url("/").toString() },
        token = { token },
        onUnauthorized = { lostSession = true },
    )

    @Before
    fun setUp() {
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
    }

    @Test
    fun loginPostsJsonToTheV1Path() = runTest {
        server.enqueue(
            MockResponse().setBody(
                """{"token":"nfm_abc","token_type":"Bearer","expires_at":"2027-01-01T00:00:00+00:00",
                   "user":{"id":7,"name":"Ann","email":"ann@example.com"},"consent_required":false,
                   "features":{"plan_generation":true},"something_new":1}""",
            ),
        )
        val response: LoginResponse = client().post("mobile/auth/login", LoginRequest("ann@example.com", "secret", deviceName = "Pixel"))

        val request = server.takeRequest()
        assertEquals("POST", request.method)
        assertEquals("/api/v1/mobile/auth/login", request.path)
        assertNull(request.getHeader("Authorization"))
        val sent = request.body.readUtf8()
        assertTrue(sent, sent.contains("\"platform\":\"android\""))
        assertTrue(sent, sent.contains("\"device_name\":\"Pixel\""))
        assertEquals("nfm_abc", response.token)
        assertEquals(7, response.user.id)
        assertTrue(response.features.planGeneration)
    }

    @Test
    fun theTokenIsSentAsBearer() = runTest {
        token = "nfm_xyz"
        server.enqueue(
            MockResponse().setBody(
                """{"date":"2026-11-27","daily_score":72.5,
                   "training":{"completed":true,"duration":45,"exercise_count":6,"score":80},
                   "nutrition":{"calories":1850.4,"protein":120,"water":1.5,"score":null},
                   "recovery":{"habits_completed":2,"habits_total":4,"sleep_hours":7.5,"score":65}}""",
            ),
        )
        val today: DashboardToday = client().get("dashboard/today")

        assertEquals("Bearer nfm_xyz", server.takeRequest().getHeader("Authorization"))
        assertEquals(72.5, today.dailyScore!!, 0.001)
        assertEquals(6, today.training.exerciseCount)
        assertNull(today.nutrition.score)
    }

    @Test
    fun errorsCarryTheApiCode() = runTest {
        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"code":"invalid_credentials","message":"Wrong email or password"}"""))
        try {
            client().post<LoginRequest, LoginResponse>("mobile/auth/login", LoginRequest("a@b.c", "x"))
            fail("expected an ApiException")
        } catch (e: ApiException) {
            assertEquals(401, e.status)
            assertEquals("invalid_credentials", e.code)
        }
        // Wrong credentials are not a lost session.
        assertEquals(false, lostSession)
    }

    @Test
    fun aRejectedTokenSignsOut() = runTest {
        token = "nfm_old"
        server.enqueue(MockResponse().setResponseCode(401).setBody("""{"code":"authentication_required","message":"x"}"""))
        try {
            client().get<DashboardToday>("dashboard/today")
            fail("expected an ApiException")
        } catch (_: ApiException) {
        }
        assertTrue(lostSession)
    }

    @Test
    fun aPageInsteadOfJsonIsANetworkError() = runTest {
        server.enqueue(MockResponse().setBody("<html>captive portal</html>"))
        try {
            client().get<DashboardToday>("dashboard/today")
            fail("expected a NetworkException")
        } catch (_: NetworkException) {
        }
    }

    @Test
    fun serverAddressesAreNormalized() {
        assertEquals("https://nosifit.example/", Session.normalizeServerUrl(" nosifit.example "))
        assertEquals("http://10.0.2.2:5000/", Session.normalizeServerUrl("http://10.0.2.2:5000"))
    }
}

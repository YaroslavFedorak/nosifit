package com.nosifit.app.data

import android.content.Context
import android.os.Build
import com.nosifit.app.BuildConfig
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

sealed interface SessionState {
    data object Loading : SessionState
    data object SignedOut : SessionState
    data class SignedIn(val user: MobileUser, val consentRequired: Boolean) : SessionState
}

/**
 * Who is signed in, and the calls that change it. The token itself stays in
 * the [TokenVault]; only the account shown on screen is cached in plain
 * preferences so the app opens without waiting for the network.
 */
class Session(
    context: Context,
    private val vault: TokenVault = KeystoreTokenVault(context),
) {
    private val prefs = context.getSharedPreferences("nosifit_session", Context.MODE_PRIVATE)
    private val json = Json { ignoreUnknownKeys = true }

    private val _state = MutableStateFlow<SessionState>(SessionState.Loading)
    val state: StateFlow<SessionState> = _state.asStateFlow()

    @Volatile
    private var token: String? = vault.read()

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER, null) ?: BuildConfig.DEFAULT_API_URL
        set(value) {
            prefs.edit().putString(KEY_SERVER, normalizeServerUrl(value)).apply()
        }

    val api = ApiClient(baseUrl = { serverUrl }, token = { token }, onUnauthorized = ::forget)

    /** On launch: show the cached account at once, then ask the server whether the token still works. */
    suspend fun restore() {
        val cached = prefs.getString(KEY_USER, null)?.let { runCatching { json.decodeFromString<MobileUser>(it) }.getOrNull() }
        if (token == null || cached == null) {
            forget()
            return
        }
        _state.value = SessionState.SignedIn(cached, prefs.getBoolean(KEY_CONSENT, false))
        try {
            val info: SessionInfo = api.get("mobile/auth/session")
            remember(info.user, info.consentRequired)
        } catch (_: NetworkException) {
            // Offline: keep the cached account; the next call will tell.
        } catch (_: ApiException) {
            // 401 already signed out through onUnauthorized; anything else: keep going.
        }
    }

    suspend fun signIn(email: String, password: String) {
        val response: LoginResponse = api.post(
            "mobile/auth/login",
            LoginRequest(email = email.trim(), password = password, deviceName = deviceName()),
        )
        token = response.token
        vault.write(response.token)
        remember(response.user, response.consentRequired)
    }

    suspend fun giveConsent() {
        api.post<ConsentRequest, StatusResponse>(
            "consent",
            ConsentRequest(privacyConsent = true, healthConsent = true, ageConfirmed = true),
        )
        val current = _state.value
        if (current is SessionState.SignedIn) remember(current.user, consentRequired = false)
    }

    suspend fun signOut() {
        runCatching { api.post<Map<String, String>, StatusResponse>("mobile/auth/logout", emptyMap()) }
        forget()
    }

    private fun remember(user: MobileUser, consentRequired: Boolean) {
        prefs.edit()
            .putString(KEY_USER, json.encodeToString(user))
            .putBoolean(KEY_CONSENT, consentRequired)
            .apply()
        _state.value = SessionState.SignedIn(user, consentRequired)
    }

    private fun forget() {
        token = null
        vault.write(null)
        prefs.edit().remove(KEY_USER).remove(KEY_CONSENT).apply()
        _state.value = SessionState.SignedOut
    }

    private fun deviceName(): String = listOf(Build.MANUFACTURER, Build.MODEL)
        .filter { it.isNotBlank() }
        .distinct()
        .joinToString(" ")
        .take(64)

    companion object {
        private const val KEY_SERVER = "server_url"
        private const val KEY_USER = "user"
        private const val KEY_CONSENT = "consent_required"

        fun normalizeServerUrl(value: String): String {
            val trimmed = value.trim()
            val withScheme = if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) trimmed else "https://$trimmed"
            return if (withScheme.endsWith("/")) withScheme else "$withScheme/"
        }
    }
}

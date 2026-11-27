package com.nosifit.app.data

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.DeserializationStrategy
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.Locale
import java.util.concurrent.TimeUnit

/** The server answered with an error. [code] is the API's stable reason ("invalid_credentials"). */
class ApiException(val status: Int, val code: String?, message: String) : Exception(message)

/** The server could not be reached or answered with something that is not the API. */
class NetworkException(cause: Throwable) : Exception(cause)

/**
 * Calls the NosiFit JSON API under /api/v1/ with the bearer token.
 *
 * No cookie jar: the app never holds a session cookie, only the token.
 */
class ApiClient(
    private val baseUrl: () -> String,
    private val token: () -> String?,
    private val onUnauthorized: () -> Unit,
    private val http: OkHttpClient = defaultHttpClient(),
) {
    val json = Json {
        ignoreUnknownKeys = true
        explicitNulls = false
        encodeDefaults = true
    }

    suspend inline fun <reified T> get(path: String): T = request("GET", path, null, serializer<T>())

    suspend inline fun <reified B, reified T> post(path: String, body: B): T =
        request("POST", path, json.encodeToString(serializer<B>(), body), serializer<T>())

    suspend fun <T> request(method: String, path: String, body: String?, reader: DeserializationStrategy<T>): T =
        withContext(Dispatchers.IO) {
            val url = baseUrl().toHttpUrlOrNull()?.resolve("api/v1/$path")
                ?: throw NetworkException(IllegalArgumentException("Bad server address"))
            val builder = Request.Builder()
                .url(url)
                .header("Accept", "application/json")
                .header("Accept-Language", Locale.getDefault().toLanguageTag())
            token()?.let { builder.header("Authorization", "Bearer $it") }
            builder.method(method, body?.toRequestBody(JSON_TYPE) ?: if (method == "GET") null else "{}".toRequestBody(JSON_TYPE))

            val (status, text) = try {
                http.newCall(builder.build()).execute().use { response ->
                    response.code to response.body?.string().orEmpty()
                }
            } catch (e: IOException) {
                throw NetworkException(e)
            }

            if (status !in 200..299) {
                val error = runCatching { json.decodeFromString(ApiErrorBody.serializer(), text) }.getOrNull()
                if (status == 401 && error?.code in SESSION_LOST) onUnauthorized()
                throw ApiException(status, error?.code, error?.message ?: "HTTP $status")
            }
            try {
                json.decodeFromString(reader, text)
            } catch (e: SerializationException) {
                throw NetworkException(e)
            } catch (e: IllegalArgumentException) {
                throw NetworkException(e)
            }
        }

    companion object {
        private val JSON_TYPE = "application/json; charset=utf-8".toMediaType()

        /** Codes after which the stored token is useless (expired, revoked, password changed). */
        private val SESSION_LOST = setOf("authentication_required", "session_revoked")

        fun defaultHttpClient(): OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .followRedirects(false)
            .build()
    }
}

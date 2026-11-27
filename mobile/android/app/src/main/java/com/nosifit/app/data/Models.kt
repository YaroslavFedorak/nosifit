package com.nosifit.app.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Shapes of the NosiFit JSON API (docs/openapi.json). Unknown fields are
// ignored, so the server can add fields without breaking the app.

@Serializable
data class MobileUser(val id: Int, val name: String, val email: String)

@Serializable
data class Features(@SerialName("plan_generation") val planGeneration: Boolean = false)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String,
    val platform: String = "android",
    @SerialName("device_name") val deviceName: String? = null,
)

@Serializable
data class LoginResponse(
    val token: String,
    @SerialName("expires_at") val expiresAt: String,
    val user: MobileUser,
    @SerialName("consent_required") val consentRequired: Boolean,
    val features: Features = Features(),
)

@Serializable
data class SessionInfo(
    val user: MobileUser,
    @SerialName("consent_required") val consentRequired: Boolean,
    val features: Features = Features(),
)

@Serializable
data class ConsentRequest(
    @SerialName("privacy_consent") val privacyConsent: Boolean,
    @SerialName("health_consent") val healthConsent: Boolean,
    @SerialName("age_confirmed") val ageConfirmed: Boolean,
)

@Serializable
data class StatusResponse(val status: String)

@Serializable
data class DashboardToday(
    val date: String,
    @SerialName("daily_score") val dailyScore: Double? = null,
    val training: TrainingToday,
    val nutrition: NutritionToday,
    val recovery: RecoveryToday,
)

@Serializable
data class TrainingToday(
    val completed: Boolean = false,
    val duration: Double = 0.0,
    @SerialName("exercise_count") val exerciseCount: Int = 0,
    val score: Double? = null,
)

@Serializable
data class NutritionToday(
    val calories: Double = 0.0,
    val protein: Double = 0.0,
    val water: Double = 0.0,
    val score: Double? = null,
)

@Serializable
data class RecoveryToday(
    @SerialName("habits_completed") val habitsCompleted: Int = 0,
    @SerialName("habits_total") val habitsTotal: Int = 0,
    @SerialName("sleep_hours") val sleepHours: Double = 0.0,
    val score: Double? = null,
)

@Serializable
data class ApiErrorBody(val code: String? = null, val message: String? = null)

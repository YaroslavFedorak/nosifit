package com.nosifit.app.ui

import androidx.annotation.StringRes
import com.nosifit.app.R
import com.nosifit.app.data.ApiException
import com.nosifit.app.data.NetworkException

/** A user-facing message for a failed call. */
@StringRes
fun messageFor(error: Throwable): Int = when {
    error is NetworkException -> R.string.error_network
    error is ApiException && error.code == "invalid_credentials" -> R.string.error_invalid_credentials
    error is ApiException && error.code in setOf("rate_limited", "too_many_attempts") -> R.string.error_rate_limited
    error is ApiException && error.code == "invalid_input" -> R.string.error_invalid_input
    else -> R.string.error_generic
}

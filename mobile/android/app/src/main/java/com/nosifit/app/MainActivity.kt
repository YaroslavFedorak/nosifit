package com.nosifit.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nosifit.app.data.SessionState
import com.nosifit.app.ui.consent.ConsentScreen
import com.nosifit.app.ui.home.HomeScreen
import com.nosifit.app.ui.login.LoginScreen
import com.nosifit.app.ui.theme.NosiFitTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val app = application as NosiFitApplication
        setContent {
            NosiFitTheme {
                Root(app)
            }
        }
    }
}

@Composable
private fun Root(app: NosiFitApplication) {
    val state by app.session.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        if (app.session.state.value == SessionState.Loading) app.session.restore()
    }

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.background)) {
        when (val current = state) {
            SessionState.Loading -> CircularProgressIndicator(Modifier.align(Alignment.Center))
            SessionState.SignedOut -> LoginScreen(app.session)
            is SessionState.SignedIn ->
                if (current.consentRequired) ConsentScreen(app.session) else HomeScreen(app, current.user)
        }
    }
}

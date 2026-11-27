package com.nosifit.app.ui.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.nosifit.app.R
import com.nosifit.app.data.Session
import com.nosifit.app.ui.messageFor
import com.nosifit.app.ui.theme.NosiColors
import com.nosifit.app.ui.theme.NosiSpace
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(session: Session) {
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var server by rememberSaveable { mutableStateOf(session.serverUrl) }
    var showServer by rememberSaveable { mutableStateOf(false) }
    var busy by rememberSaveable { mutableStateOf(false) }
    var error by rememberSaveable { mutableStateOf<Int?>(null) }
    val scope = rememberCoroutineScope()

    fun submit() {
        if (busy) return
        if (email.isBlank() || password.isEmpty()) {
            error = R.string.error_invalid_input
            return
        }
        busy = true
        error = null
        session.serverUrl = server
        scope.launch {
            try {
                session.signIn(email, password)
            } catch (e: Exception) {
                error = messageFor(e)
            } finally {
                busy = false
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .imePadding()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = NosiSpace.lg, vertical = NosiSpace.xl),
        verticalArrangement = Arrangement.spacedBy(NosiSpace.md),
    ) {
        Text("NosiFit", style = MaterialTheme.typography.displaySmall, color = NosiColors.accent)
        Text(stringResource(R.string.login_subtitle), style = MaterialTheme.typography.bodyLarge, color = NosiColors.muted)
        Spacer(Modifier.height(NosiSpace.md))
        Text(stringResource(R.string.login_title), style = MaterialTheme.typography.titleLarge)

        OutlinedTextField(
            value = email,
            onValueChange = { email = it },
            label = { Text(stringResource(R.string.login_email)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = password,
            onValueChange = { password = it },
            label = { Text(stringResource(R.string.login_password)) },
            singleLine = true,
            visualTransformation = PasswordVisualTransformation(),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
            keyboardActions = KeyboardActions(onDone = { submit() }),
            modifier = Modifier.fillMaxWidth(),
        )

        error?.let { Text(stringResource(it), color = MaterialTheme.colorScheme.error) }

        Button(
            onClick = ::submit,
            enabled = !busy,
            modifier = Modifier.fillMaxWidth().height(48.dp),
        ) {
            if (busy) CircularProgressIndicator(strokeWidth = 2.dp, color = MaterialTheme.colorScheme.onPrimary, modifier = Modifier.size(20.dp))
            else Text(stringResource(R.string.login_submit))
        }

        Text(stringResource(R.string.login_no_account), style = MaterialTheme.typography.bodyMedium, color = NosiColors.muted)

        TextButton(onClick = { showServer = !showServer }) {
            Text(stringResource(R.string.login_server))
        }
        if (showServer) {
            OutlinedTextField(
                value = server,
                onValueChange = { server = it },
                label = { Text(stringResource(R.string.login_server)) },
                supportingText = { Text(stringResource(R.string.login_server_hint)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )
        }
    }
}

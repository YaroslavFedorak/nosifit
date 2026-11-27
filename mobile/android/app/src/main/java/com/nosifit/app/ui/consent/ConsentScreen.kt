package com.nosifit.app.ui.consent

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import com.nosifit.app.R
import com.nosifit.app.data.Session
import com.nosifit.app.ui.messageFor
import com.nosifit.app.ui.theme.NosiColors
import com.nosifit.app.ui.theme.NosiSpace
import kotlinx.coroutines.launch

/** The same three explicit answers as the website's /consent page and the bot. */
@Composable
fun ConsentScreen(session: Session) {
    var privacy by rememberSaveable { mutableStateOf(false) }
    var health by rememberSaveable { mutableStateOf(false) }
    var age by rememberSaveable { mutableStateOf(false) }
    var busy by rememberSaveable { mutableStateOf(false) }
    var error by rememberSaveable { mutableStateOf<Int?>(null) }
    val scope = rememberCoroutineScope()
    val uri = LocalUriHandler.current

    Column(
        modifier = Modifier
            .fillMaxSize()
            .safeDrawingPadding()
            .verticalScroll(rememberScrollState())
            .padding(NosiSpace.lg),
        verticalArrangement = Arrangement.spacedBy(NosiSpace.md),
    ) {
        Text(stringResource(R.string.consent_title), style = MaterialTheme.typography.headlineSmall)
        Text(stringResource(R.string.consent_body), color = NosiColors.ink2)
        TextButton(onClick = { uri.openUri(session.serverUrl + "privacy") }) {
            Text(stringResource(R.string.consent_policy_link))
        }
        CheckRow(R.string.consent_privacy, privacy) { privacy = it }
        CheckRow(R.string.consent_health, health) { health = it }
        CheckRow(R.string.consent_age, age) { age = it }

        error?.let { Text(stringResource(it), color = MaterialTheme.colorScheme.error) }

        Button(
            enabled = privacy && health && age && !busy,
            onClick = {
                busy = true
                error = null
                scope.launch {
                    try {
                        session.giveConsent()
                    } catch (e: Exception) {
                        error = messageFor(e)
                    } finally {
                        busy = false
                    }
                }
            },
            modifier = Modifier.fillMaxWidth().height(48.dp),
        ) { Text(stringResource(R.string.consent_submit)) }

        TextButton(onClick = { scope.launch { session.signOut() } }) {
            Text(stringResource(R.string.profile_logout))
        }
    }
}

@Composable
private fun CheckRow(label: Int, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = Modifier
            .fillMaxWidth()
            .toggleable(value = checked, role = Role.Checkbox, onValueChange = onChange),
    ) {
        Checkbox(checked = checked, onCheckedChange = null)
        Text(stringResource(label), modifier = Modifier.padding(start = NosiSpace.xs))
    }
}

package com.nosifit.app.ui.home

import androidx.annotation.StringRes
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Bedtime
import androidx.compose.material.icons.outlined.FitnessCenter
import androidx.compose.material.icons.outlined.Person
import androidx.compose.material.icons.outlined.Restaurant
import androidx.compose.material.icons.outlined.Today
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.lifecycle.viewmodel.compose.viewModel
import com.nosifit.app.NosiFitApplication
import com.nosifit.app.R
import com.nosifit.app.data.MobileUser
import com.nosifit.app.ui.theme.NosiColors
import com.nosifit.app.ui.theme.NosiSpace
import com.nosifit.app.ui.today.TodayScreen
import com.nosifit.app.ui.today.TodayViewModel
import kotlinx.coroutines.launch

/** The bottom tabs, in the order of the website's phone tab bar. */
enum class Tab(@StringRes val label: Int, val icon: ImageVector, val webPath: String) {
    Today(R.string.tab_today, Icons.Outlined.Today, "app/dashboard"),
    Nutrition(R.string.tab_nutrition, Icons.Outlined.Restaurant, "app/nutrition"),
    Training(R.string.tab_training, Icons.Outlined.FitnessCenter, "app/training"),
    Recovery(R.string.tab_recovery, Icons.Outlined.Bedtime, "app/recovery"),
    Profile(R.string.tab_profile, Icons.Outlined.Person, "app/profile"),
}

@Composable
fun HomeScreen(app: NosiFitApplication, user: MobileUser) {
    var tab by rememberSaveable { mutableStateOf(Tab.Today) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        bottomBar = {
            NavigationBar(containerColor = NosiColors.paper2) {
                Tab.entries.forEach { item ->
                    NavigationBarItem(
                        selected = tab == item,
                        onClick = { tab = item },
                        icon = { Icon(item.icon, contentDescription = null) },
                        label = { Text(stringResource(item.label), maxLines = 1) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NosiColors.accentInk,
                            indicatorColor = NosiColors.accent,
                            selectedTextColor = NosiColors.ink,
                            unselectedIconColor = NosiColors.muted,
                            unselectedTextColor = NosiColors.muted,
                        ),
                    )
                }
            }
        },
    ) { padding ->
        Column(Modifier.padding(padding)) {
            when (tab) {
                // Keyed by account: after signing in as someone else the old data must not show.
                Tab.Today -> TodayScreen(viewModel(key = "today-${user.id}") { TodayViewModel(app.dashboard) })
                Tab.Profile -> ProfileScreen(app, user)
                else -> ComingSoon(app.session.serverUrl + tab.webPath)
            }
        }
    }
}

@Composable
private fun ComingSoon(webUrl: String) {
    val uri = LocalUriHandler.current
    Column(
        modifier = Modifier.fillMaxSize().padding(NosiSpace.lg),
        verticalArrangement = Arrangement.spacedBy(NosiSpace.md),
    ) {
        Text(stringResource(R.string.coming_soon), color = NosiColors.ink2)
        OutlinedButton(onClick = { uri.openUri(webUrl) }) { Text(stringResource(R.string.open_website)) }
    }
}

@Composable
private fun ProfileScreen(app: NosiFitApplication, user: MobileUser) {
    val scope = rememberCoroutineScope()
    Column(
        modifier = Modifier.fillMaxSize().padding(NosiSpace.lg),
        verticalArrangement = Arrangement.spacedBy(NosiSpace.sm),
    ) {
        Text(stringResource(R.string.profile_signed_in_as), color = NosiColors.muted)
        Text(user.name, style = MaterialTheme.typography.titleLarge)
        Text(user.email, color = NosiColors.ink2)
        OutlinedButton(onClick = { scope.launch { app.session.signOut() } }) {
            Text(stringResource(R.string.profile_logout))
        }
    }
}

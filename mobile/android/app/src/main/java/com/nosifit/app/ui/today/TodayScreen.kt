package com.nosifit.app.ui.today

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.nosifit.app.R
import com.nosifit.app.data.DashboardToday
import com.nosifit.app.ui.theme.NosiColors
import com.nosifit.app.ui.theme.NosiSpace
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TodayScreen(viewModel: TodayViewModel) {
    val state by viewModel.state.collectAsStateWithLifecycle()

    PullToRefreshBox(
        isRefreshing = state.loading,
        onRefresh = viewModel::refresh,
        modifier = Modifier.fillMaxSize(),
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(NosiSpace.md),
            verticalArrangement = Arrangement.spacedBy(NosiSpace.md),
        ) {
            Text(stringResource(R.string.today_title), style = MaterialTheme.typography.headlineSmall)
            val today = state.today
            when {
                today != null -> TodayContent(today)
                state.error != null -> ErrorBlock(state.error!!, viewModel::refresh)
            }
        }
    }
}

@Composable
private fun TodayContent(today: DashboardToday) {
    ScoreCard(today.dailyScore)
    ModuleCard(
        title = stringResource(R.string.today_training),
        tone = NosiColors.training,
        score = today.training.score,
        detail = if (today.training.completed) {
            stringResource(R.string.today_training_done, today.training.duration.roundToInt(), today.training.exerciseCount)
        } else {
            stringResource(R.string.today_training_none)
        },
    )
    ModuleCard(
        title = stringResource(R.string.today_nutrition),
        tone = NosiColors.nutrition,
        score = today.nutrition.score,
        detail = stringResource(
            R.string.today_nutrition_value,
            today.nutrition.calories.roundToInt(),
            today.nutrition.protein.roundToInt(),
            today.nutrition.water,
        ),
    )
    ModuleCard(
        title = stringResource(R.string.today_recovery),
        tone = NosiColors.recovery,
        score = today.recovery.score,
        detail = stringResource(
            R.string.today_recovery_value,
            today.recovery.habitsCompleted,
            today.recovery.habitsTotal,
            today.recovery.sleepHours,
        ),
    )
}

@Composable
private fun ScoreCard(score: Double?) {
    Card(colors = CardDefaults.cardColors(containerColor = NosiColors.paper2), shape = RoundedCornerShape(12.dp)) {
        Column(Modifier.fillMaxWidth().padding(NosiSpace.md)) {
            Text(stringResource(R.string.today_score), style = MaterialTheme.typography.labelLarge, color = NosiColors.muted)
            if (score != null) {
                Text("${score.roundToInt()}", style = MaterialTheme.typography.displaySmall, color = NosiColors.accent)
                Spacer(Modifier.height(NosiSpace.xs))
                ScoreBar(score, NosiColors.accent)
            } else {
                Text(stringResource(R.string.today_no_score), style = MaterialTheme.typography.titleMedium)
            }
        }
    }
}

@Composable
private fun ModuleCard(title: String, tone: Color, score: Double?, detail: String) {
    Card(colors = CardDefaults.cardColors(containerColor = NosiColors.paper2), shape = RoundedCornerShape(12.dp)) {
        Row(Modifier.fillMaxWidth().padding(NosiSpace.md)) {
            Box(Modifier.width(4.dp).height(44.dp).background(tone, RoundedCornerShape(2.dp)))
            Column(Modifier.padding(start = NosiSpace.sm).weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(detail, style = MaterialTheme.typography.bodyMedium, color = NosiColors.ink2)
                if (score != null) {
                    Spacer(Modifier.height(NosiSpace.xs))
                    ScoreBar(score, tone)
                }
            }
            if (score != null) {
                Text("${score.roundToInt()}", style = MaterialTheme.typography.titleLarge, color = tone)
            }
        }
    }
}

@Composable
private fun ScoreBar(score: Double, tone: Color) {
    LinearProgressIndicator(
        progress = { (score / 100.0).toFloat().coerceIn(0f, 1f) },
        color = tone,
        trackColor = NosiColors.paper4,
        modifier = Modifier.fillMaxWidth().height(6.dp),
    )
}

@Composable
private fun ErrorBlock(message: Int, onRetry: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(NosiSpace.sm)) {
        Text(stringResource(message), color = MaterialTheme.colorScheme.error)
        OutlinedButton(onClick = onRetry) { Text(stringResource(R.string.retry)) }
    }
}

package com.nosifit.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** The design tokens of frontend/src/design/tokens.ts, converted from OKLCH to sRGB. */
object NosiColors {
    val paper = Color(0xFF0B0E14)
    val paper2 = Color(0xFF13171E)
    val paper3 = Color(0xFF1C2128)
    val paper4 = Color(0xFF272D36)
    val rule = Color(0xFF272C32)
    val edge = Color(0xFF646972)
    val ink = Color(0xFFECEFF3)
    val ink2 = Color(0xFFC3C8CF)
    val muted = Color(0xFF969CA6)
    val accent = Color(0xFFEAC25A)
    val accentInk = Color(0xFF211A06)
    val training = Color(0xFFEAC25A)
    val nutrition = Color(0xFFB098E7)
    val recovery = Color(0xFF6DC5CA)
    val water = Color(0xFF6DABDF)
    val success = Color(0xFF73CA99)
    val warn = Color(0xFFEBAC6C)
    val error = Color(0xFFEC7B79)
}

object NosiSpace {
    val xs = 8.dp
    val sm = 12.dp
    val md = 16.dp
    val lg = 24.dp
    val xl = 40.dp
}

private val colors = darkColorScheme(
    primary = NosiColors.accent,
    onPrimary = NosiColors.accentInk,
    secondary = NosiColors.recovery,
    background = NosiColors.paper,
    onBackground = NosiColors.ink,
    surface = NosiColors.paper2,
    onSurface = NosiColors.ink,
    surfaceVariant = NosiColors.paper3,
    onSurfaceVariant = NosiColors.muted,
    surfaceContainer = NosiColors.paper2,
    surfaceContainerHigh = NosiColors.paper3,
    surfaceContainerHighest = NosiColors.paper4,
    outline = NosiColors.edge,
    outlineVariant = NosiColors.rule,
    error = NosiColors.error,
)

// The type scale of the web interface (1.2 ratio at 16 px).
private val typography = Typography(
    displaySmall = TextStyle(fontSize = 39.8.sp, fontWeight = FontWeight.SemiBold, lineHeight = 44.sp),
    headlineSmall = TextStyle(fontSize = 27.6.sp, fontWeight = FontWeight.SemiBold, lineHeight = 32.sp),
    titleLarge = TextStyle(fontSize = 23.sp, fontWeight = FontWeight.SemiBold, lineHeight = 28.sp),
    titleMedium = TextStyle(fontSize = 19.2.sp, fontWeight = FontWeight.Medium, lineHeight = 24.sp),
    bodyLarge = TextStyle(fontSize = 16.sp, lineHeight = 24.sp),
    bodyMedium = TextStyle(fontSize = 14.sp, lineHeight = 20.sp),
    labelLarge = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium, lineHeight = 20.sp),
    labelMedium = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Medium, lineHeight = 16.sp),
)

@Composable
fun NosiFitTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = colors, typography = typography, content = content)
}

package com.yourco.driverAA.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.core.view.WindowCompat
import androidx.compose.ui.graphics.Color

// OrderOps Light Theme
private val LightColorScheme = lightColorScheme(
    primary = OrderOpsBlue,
    onPrimary = TextOnPrimary,
    primaryContainer = OrderOpsLightBlue,
    onPrimaryContainer = TextPrimary,
    
    secondary = OrderOpsOrange,
    onSecondary = TextOnPrimary,
    secondaryContainer = OrderOpsLightOrange,
    onSecondaryContainer = TextPrimary,
    
    tertiary = StatusActive,
    onTertiary = TextOnPrimary,
    
    error = ErrorRed,
    onError = TextOnPrimary,
    errorContainer = Color(0xFFFFDAD6),
    onErrorContainer = Color(0xFF410002),
    
    background = SurfaceLight,
    onBackground = TextPrimary,
    
    surface = CardSurface,
    onSurface = TextOnSurface,
    surfaceVariant = Color(0xFFF5F5F5),
    onSurfaceVariant = TextSecondary,
    
    outline = BorderLight,
    outlineVariant = DividerLight,
    
    inverseSurface = TextPrimary,
    inverseOnSurface = SurfaceLight,
    inversePrimary = OrderOpsLightBlue,
)

// OrderOps Dark Theme
private val DarkColorScheme = darkColorScheme(
    primary = OrderOpsLightBlue,
    onPrimary = Color(0xFF003258),
    primaryContainer = OrderOpsBlueVariant,
    onPrimaryContainer = Color(0xFFD1E4FF),
    
    secondary = OrderOpsLightOrange,
    onSecondary = Color(0xFF402D00),
    secondaryContainer = OrderOpsOrangeVariant,
    onSecondaryContainer = Color(0xFFFFDDB3),
    
    tertiary = Color(0xFF69DD72),
    onTertiary = Color(0xFF003909),
    
    error = Color(0xFFFFB4AB),
    onError = Color(0xFF690005),
    errorContainer = Color(0xFF93000A),
    onErrorContainer = Color(0xFFFFDAD6),
    
    background = SurfaceDark,
    onBackground = Color(0xFFE6E1E5),
    
    surface = CardSurfaceDark,
    onSurface = Color(0xFFE6E1E5),
    surfaceVariant = Color(0xFF49454F),
    onSurfaceVariant = Color(0xFFCAC4D0),
    
    outline = BorderDark,
    outlineVariant = DividerDark,
    
    inverseSurface = Color(0xFFE6E1E5),
    inverseOnSurface = Color(0xFF1C1B1F),
    inversePrimary = OrderOpsBlue,
)

@Composable
fun OrderOpsDriverTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    // Dynamic color is available on Android 12+
    dynamicColor: Boolean = false, // Disabled to maintain brand consistency
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }

        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }
    
    val context = LocalContext.current
    if (context is Activity) {
        SideEffect {
            val window = context.window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, window.decorView).isAppearanceLightStatusBars = !darkTheme
        }
    }

    MaterialTheme(
        colorScheme = colorScheme,
        typography = OrderOpsTypography,
        content = content
    )
}
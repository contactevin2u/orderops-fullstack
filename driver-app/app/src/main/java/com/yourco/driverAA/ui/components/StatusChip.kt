package com.yourco.driverAA.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.yourco.driverAA.ui.theme.*

@Composable
fun OrderStatusChip(
    status: String,
    modifier: Modifier = Modifier
) {
    val (backgroundColor, textColor) = when (status.uppercase()) {
        "ACTIVE", "ASSIGNED", "IN_PROGRESS", "IN_TRANSIT" -> StatusActive to Color.White
        "PENDING", "NEW" -> StatusPending to Color.White  
        "COMPLETED", "DELIVERED", "SUCCESS" -> StatusCompleted to Color.White
        "CANCELLED" -> StatusCancelled to Color.White
        "ON_HOLD" -> StatusOnHold to Color.White
        else -> MaterialTheme.colorScheme.surfaceVariant to MaterialTheme.colorScheme.onSurfaceVariant
    }
    
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(backgroundColor)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = status.uppercase(),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = textColor
        )
    }
}

@Composable
fun PriorityChip(
    priority: String,
    modifier: Modifier = Modifier
) {
    val (backgroundColor, textColor) = when (priority.uppercase()) {
        "HIGH", "URGENT" -> ErrorRed to Color.White
        "MEDIUM" -> WarningOrange to Color.White
        "LOW" -> SuccessGreen to Color.White
        else -> MaterialTheme.colorScheme.surfaceVariant to MaterialTheme.colorScheme.onSurfaceVariant
    }
    
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(backgroundColor)
            .padding(horizontal = 8.dp, vertical = 4.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = priority.uppercase(),
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Medium,
            color = textColor
        )
    }
}

@Composable
fun InfoChip(
    text: String,
    backgroundColor: Color = MaterialTheme.colorScheme.primaryContainer,
    textColor: Color = MaterialTheme.colorScheme.onPrimaryContainer,
    modifier: Modifier = Modifier
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        color = backgroundColor,
        contentColor = textColor
    ) {
        Text(
            text = text,
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
        )
    }
}

@Composable
fun StatusChip(
    status: String,
    modifier: Modifier = Modifier
) {
    val (backgroundColor, textColor) = when {
        status.contains("🤖") -> MaterialTheme.colorScheme.primary to Color.White // AI badges
        status.contains("💰") -> WarningOrange to Color.White // Cash related
        status.contains("🏦") -> SuccessGreen to Color.White // Bank transfer
        status.contains("⚠️") -> ErrorRed to Color.White // Warning/Required
        status.contains("👥") -> MaterialTheme.colorScheme.tertiary to Color.White // Dual driver
        status.contains("📸") -> MaterialTheme.colorScheme.secondary to Color.White // Photos
        status.contains("⚡") -> SuccessGreen to Color.White // Instant
        status.uppercase().contains("PENDING") -> StatusPending to Color.White
        status.uppercase().contains("RELEASED") -> StatusCompleted to Color.White
        status.uppercase().contains("CANCELLED") -> StatusCancelled to Color.White
        status.uppercase().contains("EARNED") -> StatusPending to Color.White // New AI system
        status.uppercase().contains("PAID") -> StatusCompleted to Color.White // New AI system
        else -> MaterialTheme.colorScheme.surfaceVariant to MaterialTheme.colorScheme.onSurfaceVariant
    }
    
    Box(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .background(backgroundColor)
            .padding(horizontal = 12.dp, vertical = 6.dp),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = status.uppercase(),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.Bold,
            color = textColor
        )
    }
}
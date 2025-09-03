package com.yourco.driverAA.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay

@Composable
fun MalayErrorMessage(
    message: String?,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null,
    autoDismiss: Boolean = false,
    autoDismissDelay: Long = 5000L
) {
    if (message != null) {
        LaunchedEffect(message) {
            if (autoDismiss && onDismiss != null) {
                delay(autoDismissDelay)
                onDismiss()
            }
        }
        
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.errorContainer
            ),
            shape = RoundedCornerShape(8.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Error,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.error,
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f)
                )
                
                if (onDismiss != null) {
                    TextButton(
                        onClick = onDismiss,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.error
                        )
                    ) {
                        Text("Tutup")
                    }
                }
            }
        }
    }
}

@Composable
fun MalaySuccessMessage(
    message: String?,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null,
    autoDismiss: Boolean = true,
    autoDismissDelay: Long = 3000L
) {
    if (message != null) {
        LaunchedEffect(message) {
            if (autoDismiss && onDismiss != null) {
                delay(autoDismissDelay)
                onDismiss()
            }
        }
        
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            ),
            shape = RoundedCornerShape(8.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f)
                )
                
                if (onDismiss != null) {
                    TextButton(
                        onClick = onDismiss,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Text("OK")
                    }
                }
            }
        }
    }
}

@Composable
fun MalayWarningMessage(
    message: String?,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null
) {
    if (message != null) {
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = Color(0xFFFFF3CD) // Light yellow
            ),
            shape = RoundedCornerShape(8.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = Color(0xFF856404), // Dark yellow
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = message,
                    color = Color(0xFF856404),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f)
                )
                
                if (onDismiss != null) {
                    TextButton(
                        onClick = onDismiss,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = Color(0xFF856404)
                        )
                    ) {
                        Text("Faham")
                    }
                }
            }
        }
    }
}

@Composable
fun MalayInfoMessage(
    message: String?,
    modifier: Modifier = Modifier,
    onDismiss: (() -> Unit)? = null
) {
    if (message != null) {
        Card(
            modifier = modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surfaceVariant
            ),
            shape = RoundedCornerShape(8.dp)
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Icon(
                    imageVector = Icons.Default.Info,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(24.dp)
                )
                
                Spacer(modifier = Modifier.width(12.dp))
                
                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f)
                )
                
                if (onDismiss != null) {
                    TextButton(
                        onClick = onDismiss,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    ) {
                        Text("OK")
                    }
                }
            }
        }
    }
}

@Composable
fun MalayStatusBadge(
    status: String?,
    modifier: Modifier = Modifier
) {
    val (backgroundColor, contentColor, displayText) = when (status) {
        "ASSIGNED" -> Triple(
            Color(0xFFE3F2FD), // Light blue
            Color(0xFF1976D2), // Blue
            "Ditugaskan"
        )
        "STARTED" -> Triple(
            Color(0xFFE8F5E8), // Light green
            Color(0xFF2E7D32), // Green
            "Dalam Perjalanan"
        )
        "DELIVERED" -> Triple(
            Color(0xFFE8F5E8), // Light green
            Color(0xFF1B5E20), // Dark green
            "Dihantar"
        )
        "ON_HOLD" -> Triple(
            Color(0xFFFFF3E0), // Light orange
            Color(0xFFE65100), // Orange
            "Ditangguhkan"
        )
        "CANCELLED" -> Triple(
            Color(0xFFFFEBEE), // Light red
            Color(0xFFC62828), // Red
            "Dibatalkan"
        )
        else -> Triple(
            MaterialTheme.colorScheme.surfaceVariant,
            MaterialTheme.colorScheme.onSurfaceVariant,
            "Tidak Diketahui"
        )
    }
    
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(12.dp),
        color = backgroundColor
    ) {
        Text(
            text = displayText,
            color = contentColor,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
        )
    }
}

@Composable
fun MalayActionButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
    isDestructive: Boolean = false,
    isPrimary: Boolean = false
) {
    val colors = when {
        isDestructive -> ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.error,
            contentColor = MaterialTheme.colorScheme.onError,
            disabledContainerColor = MaterialTheme.colorScheme.error.copy(alpha = 0.3f),
            disabledContentColor = MaterialTheme.colorScheme.onError.copy(alpha = 0.3f)
        )
        isPrimary -> ButtonDefaults.buttonColors(
            containerColor = MaterialTheme.colorScheme.primary,
            contentColor = MaterialTheme.colorScheme.onPrimary
        )
        else -> ButtonDefaults.outlinedButtonColors(
            contentColor = MaterialTheme.colorScheme.primary
        )
    }
    
    if (isPrimary || isDestructive) {
        Button(
            onClick = onClick,
            modifier = modifier,
            enabled = enabled,
            colors = colors
        ) {
            Text(text)
        }
    } else {
        OutlinedButton(
            onClick = onClick,
            modifier = modifier,
            enabled = enabled,
            colors = colors
        ) {
            Text(text)
        }
    }
}
package com.yourco.driverAA.ui.components

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.yourco.driverAA.domain.OfflineStatus

@Composable
fun OfflineStatusBar(
    offlineStatus: OfflineStatus,
    onSyncClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val backgroundColor = if (offlineStatus.isOnline) {
        if (offlineStatus.hasPendingWork) MaterialTheme.colorScheme.primaryContainer
        else Color.Green.copy(alpha = 0.1f)
    } else {
        MaterialTheme.colorScheme.errorContainer
    }
    
    val contentColor = if (offlineStatus.isOnline) {
        if (offlineStatus.hasPendingWork) MaterialTheme.colorScheme.onPrimaryContainer
        else Color.Green.copy(alpha = 0.8f)
    } else {
        MaterialTheme.colorScheme.onErrorContainer
    }
    
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 8.dp)
            .animateContentSize(),
        colors = CardDefaults.cardColors(containerColor = backgroundColor)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Start
            ) {
                Icon(
                    imageVector = when {
                        !offlineStatus.isOnline -> Icons.Default.CloudOff
                        offlineStatus.hasPendingWork -> Icons.Default.Sync
                        else -> Icons.Default.CloudDone
                    },
                    contentDescription = null,
                    tint = contentColor,
                    modifier = Modifier.size(20.dp)
                )
                
                Spacer(modifier = Modifier.width(8.dp))
                
                Column {
                    Text(
                        text = when {
                            !offlineStatus.isOnline -> "Offline Mode"
                            offlineStatus.hasPendingWork -> "Sync Pending"
                            else -> "Online & Synced"
                        },
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        color = contentColor
                    )
                    
                    if (offlineStatus.hasPendingWork) {
                        val pendingItems = buildList {
                            if (offlineStatus.pendingOperations > 0) {
                                add("${offlineStatus.pendingOperations} operations")
                            }
                            if (offlineStatus.pendingPhotos > 0) {
                                add("${offlineStatus.pendingPhotos} photos")
                            }
                            if (offlineStatus.pendingScans > 0) {
                                add("${offlineStatus.pendingScans} scans")
                            }
                        }.joinToString(", ")
                        
                        Text(
                            text = "Pending: $pendingItems",
                            fontSize = 12.sp,
                            color = contentColor.copy(alpha = 0.8f)
                        )
                    }
                    
                    if (offlineStatus.failedOperations > 0) {
                        Text(
                            text = "${offlineStatus.failedOperations} failed operations",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.error
                        )
                    }
                }
            }
            
            if (offlineStatus.isOnline && offlineStatus.hasPendingWork) {
                IconButton(
                    onClick = onSyncClick,
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "Sync now",
                        tint = contentColor,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun OfflineJobCard(
    jobTitle: String,
    subtitle: String,
    isPending: Boolean = false,
    modifier: Modifier = Modifier,
    onClick: () -> Unit = {}
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        onClick = onClick,
        colors = CardDefaults.cardColors(
            containerColor = if (isPending) {
                MaterialTheme.colorScheme.secondaryContainer.copy(alpha = 0.7f)
            } else {
                MaterialTheme.colorScheme.surface
            }
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = jobTitle,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Medium
                    )
                    
                    if (isPending) {
                        Spacer(modifier = Modifier.width(8.dp))
                        Box(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.1f))
                                .padding(horizontal = 6.dp, vertical = 2.dp)
                        ) {
                            Text(
                                text = "PENDING SYNC",
                                fontSize = 10.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
                
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }
            
            if (isPending) {
                Icon(
                    imageVector = Icons.Default.Schedule,
                    contentDescription = "Pending sync",
                    tint = MaterialTheme.colorScheme.primary.copy(alpha = 0.7f),
                    modifier = Modifier.size(20.dp)
                )
            }
        }
    }
}
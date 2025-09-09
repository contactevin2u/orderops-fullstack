package com.yourco.driverAA.ui.delivery

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import com.yourco.driverAA.data.api.UIDActionDto
import com.yourco.driverAA.ui.stockverification.StockQRScannerScreen
import com.yourco.driverAA.ui.theme.AppColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeliveryCompletionScreen(
    job: JobDto,
    onCompleteDelivery: (List<UIDActionDto>) -> Unit,
    onCancel: () -> Unit
) {
    var showQRScanner by remember { mutableStateOf(false) }
    var scannedUIDs by remember { mutableStateOf<List<String>>(emptyList()) }
    var uidActions by remember { mutableStateOf<Map<String, UIDActionDto>>(emptyMap()) }
    var showActionSelector by remember { mutableStateOf(false) }
    var selectedUIDForAction by remember { mutableStateOf<String?>(null) }
    
    // Calculate expected UIDs from job items
    val expectedUIDs = remember(job) {
        job.items?.mapNotNull { item -> 
            // Extract UIDs from item if available, or generate placeholder
            item.uid?.let { listOf(it) } ?: emptyList()
        }?.flatten() ?: emptyList()
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Header
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = AppColors.primary)
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Icon(
                    Icons.Default.QrCodeScanner,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Delivery Completion",
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Text(
                    text = "Scan all delivered items before completing order #${job.code}",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.9f),
                    textAlign = TextAlign.Center
                )
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Order Items Summary
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Order Items",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                LazyColumn(
                    modifier = Modifier.heightIn(max = 200.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    items(job.items ?: emptyList()) { item ->
                        OrderItemRow(
                            item = item,
                            isScanned = item.uid?.let { scannedUIDs.contains(it) } ?: false
                        )
                    }
                }
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Scanning Section
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Scanned Items",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Text(
                        text = "${uidActions.size} / ${job.items?.size ?: 0} completed",
                        style = MaterialTheme.typography.bodyMedium,
                        color = if (uidActions.size == job.items?.size ?: 0) AppColors.success else AppColors.warning,
                        fontWeight = FontWeight.Medium
                    )
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                // Scan button
                Button(
                    onClick = { showQRScanner = true },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AppColors.primary
                    )
                ) {
                    Icon(Icons.Default.QrCodeScanner, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Scan Delivered Items")
                }
                
                // Scanned UIDs list with actions
                if (scannedUIDs.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    LazyColumn(
                        modifier = Modifier.heightIn(max = 200.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(scannedUIDs) { uid ->
                            val action = uidActions[uid]
                            UIDActionCard(
                                uid = uid,
                                action = action,
                                onEditAction = {
                                    selectedUIDForAction = uid
                                    showActionSelector = true
                                },
                                onRemove = {
                                    scannedUIDs = scannedUIDs - uid
                                    uidActions = uidActions - uid
                                }
                            )
                        }
                    }
                }
            }
        }
        
        Spacer(modifier = Modifier.weight(1f))
        
        // Action Buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier.weight(1f)
            ) {
                Icon(Icons.Default.Close, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text("Cancel")
            }
            
            Button(
                onClick = { 
                    onCompleteDelivery(uidActions.values.toList())
                },
                modifier = Modifier.weight(1f),
                enabled = uidActions.isNotEmpty(), // Require at least one UID with action
                colors = ButtonDefaults.buttonColors(
                    containerColor = AppColors.success
                )
            ) {
                Icon(Icons.Default.CheckCircle, contentDescription = null)
                Spacer(modifier = Modifier.width(4.dp))
                Text("Complete Delivery")
            }
        }
        
        // Status message
        Spacer(modifier = Modifier.height(8.dp))
        
        val itemCount = job.items?.size ?: 0
        val statusMessage = when {
            uidActions.isEmpty() -> "Scan items and set their actions to complete delivery"
            uidActions.size < itemCount -> "Warning: ${itemCount - uidActions.size} items still need actions"
            scannedUIDs.any { uidActions[it] == null } -> "Some scanned items need actions assigned"
            else -> "All items processed - ready to complete delivery"
        }
        
        val statusColor = when {
            uidActions.isEmpty() -> AppColors.error
            uidActions.size < itemCount || scannedUIDs.any { uidActions[it] == null } -> AppColors.warning
            else -> AppColors.success
        }
        
        Text(
            text = statusMessage,
            style = MaterialTheme.typography.bodySmall,
            color = statusColor,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth()
        )
    }
    
    // QR Scanner
    if (showQRScanner) {
        StockQRScannerScreen(
            title = "Scan Delivered Items",
            onUIDScanned = { uid ->
                if (!scannedUIDs.contains(uid)) {
                    scannedUIDs = scannedUIDs + uid
                    // Open action selector for this UID
                    selectedUIDForAction = uid
                    showActionSelector = true
                }
            },
            scannedUIDs = scannedUIDs,
            onDismiss = { showQRScanner = false }
        )
    }
    
    // UID Action Selector Dialog
    if (showActionSelector && selectedUIDForAction != null) {
        UIDActionSelectorDialog(
            uid = selectedUIDForAction!!,
            currentAction = uidActions[selectedUIDForAction!!],
            jobItems = job.items ?: emptyList(),
            onDismiss = {
                showActionSelector = false
                selectedUIDForAction = null
            },
            onActionSelected = { action ->
                uidActions = uidActions + (selectedUIDForAction!! to action)
                showActionSelector = false
                selectedUIDForAction = null
            }
        )
    }
}

@Composable
private fun OrderItemRow(
    item: JobItemDto,
    isScanned: Boolean
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = item.name ?: "Unknown Item",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
            if (item.uid != null) {
                Text(
                    text = "UID: ${item.uid}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        
        Icon(
            if (isScanned) Icons.Default.CheckCircle else Icons.Default.RadioButtonUnchecked,
            contentDescription = null,
            tint = if (isScanned) AppColors.success else MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(20.dp)
        )
    }
}

@Composable
private fun UIDActionCard(
    uid: String,
    action: UIDActionDto?,
    onEditAction: () -> Unit,
    onRemove: () -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = if (action != null) AppColors.success.copy(alpha = 0.1f) 
                           else AppColors.warning.copy(alpha = 0.1f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = uid,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                Text(
                    text = action?.action ?: "No action selected",
                    style = MaterialTheme.typography.bodySmall,
                    color = if (action != null) AppColors.success else AppColors.warning
                )
            }
            
            Row {
                IconButton(
                    onClick = onEditAction,
                    modifier = Modifier.size(24.dp)
                ) {
                    Icon(
                        Icons.Default.Edit,
                        contentDescription = "Edit Action",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(16.dp)
                    )
                }
                
                IconButton(
                    onClick = onRemove,
                    modifier = Modifier.size(24.dp)
                ) {
                    Icon(
                        Icons.Default.Close,
                        contentDescription = "Remove",
                        tint = AppColors.error,
                        modifier = Modifier.size(16.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun UIDActionSelectorDialog(
    uid: String,
    currentAction: UIDActionDto?,
    jobItems: List<JobItemDto>,
    onDismiss: () -> Unit,
    onActionSelected: (UIDActionDto) -> Unit
) {
    val availableActions = listOf("DELIVER", "COLLECT", "REPAIR", "SWAP")
    var selectedAction by remember { mutableStateOf(currentAction?.action ?: "DELIVER") }
    var notes by remember { mutableStateOf(currentAction?.notes ?: "") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "Select Action for UID",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                    )
                ) {
                    Text(
                        text = uid,
                        modifier = Modifier.padding(12.dp),
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Text(
                    text = "Action:",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                // Action buttons
                availableActions.forEach { action ->
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        RadioButton(
                            selected = selectedAction == action,
                            onClick = { selectedAction = action }
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = getActionDisplayName(action),
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.clickable { selectedAction = action }
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
                
                OutlinedTextField(
                    value = notes,
                    onValueChange = { notes = it },
                    label = { Text("Notes (optional)") },
                    modifier = Modifier.fillMaxWidth(),
                    maxLines = 2
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val action = UIDActionDto(
                        uid = uid,
                        action = selectedAction,
                        sku_id = findItemSkuByUID(jobItems, uid),
                        notes = notes.takeIf { it.isNotBlank() }
                    )
                    onActionSelected(action)
                }
            ) {
                Text("Set Action")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

private fun getActionDisplayName(action: String): String {
    return when (action) {
        "DELIVER" -> "Deliver - Item successfully delivered"
        "COLLECT" -> "Collect - Item collected from customer"
        "REPAIR" -> "Repair - Item needs repair"
        "SWAP" -> "Swap - Item needs to be swapped"
        else -> action
    }
}

// Helper function to find SKU ID by UID (currently JobItemDto doesn't have uid field)
private fun findItemSkuByUID(items: List<JobItemDto>, uid: String): Int? {
    // For now, return null since JobItemDto doesn't have uid or sku_id fields
    // This would need to be implemented when the backend provides item UIDs
    return null
}
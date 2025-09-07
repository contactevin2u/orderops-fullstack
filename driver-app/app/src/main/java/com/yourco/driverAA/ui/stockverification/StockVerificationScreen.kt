package com.yourco.driverAA.ui.stockverification

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.hilt.navigation.compose.hiltViewModel
import com.google.android.gms.location.*
import com.yourco.driverAA.ui.components.*
import com.yourco.driverAA.ui.theme.AppColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockVerificationScreen(
    onNavigateToOrders: () -> Unit,
    viewModel: StockVerificationViewModel = hiltViewModel()
) {
    val context = LocalContext.current
    val uiState by viewModel.uiState.collectAsState()
    val scannedUIDs by viewModel.scannedUIDs.collectAsState()
    
    var showUIDInput by remember { mutableStateOf(false) }
    var currentLocation by remember { mutableStateOf<Pair<Double, Double>?>(null) }
    var locationName by remember { mutableStateOf("") }
    
    // Location permission launcher
    val locationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            getCurrentLocation(context) { lat, lng, name ->
                currentLocation = Pair(lat, lng)
                locationName = name
            }
        }
    }
    
    // Get location when screen loads
    LaunchedEffect(Unit) {
        if (ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        ) {
            getCurrentLocation(context) { lat, lng, name ->
                currentLocation = Pair(lat, lng)
                locationName = name
            }
        } else {
            locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }
    
    // Navigate to orders when clock-in is complete
    LaunchedEffect(uiState.canAccessOrders) {
        if (uiState.canAccessOrders) {
            onNavigateToOrders()
        }
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
                    Icons.Default.Assignment,
                    contentDescription = null,
                    tint = Color.White,
                    modifier = Modifier.size(48.dp)
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "Morning Stock Verification",
                    style = MaterialTheme.typography.headlineSmall,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    textAlign = TextAlign.Center
                )
                Text(
                    text = "Scan all UIDs in your assigned lorry before starting work",
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = 0.9f),
                    textAlign = TextAlign.Center
                )
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        when {
            uiState.isLoading -> {
                Box(
                    modifier = Modifier.fillMaxWidth(),
                    contentAlignment = Alignment.Center
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        CircularProgressIndicator()
                        Spacer(modifier = Modifier.height(8.dp))
                        Text("Loading assignment...")
                    }
                }
            }
            
            !uiState.hasAssignment -> {
                ErrorCard(
                    message = uiState.error ?: "No lorry assignment for today. Contact your dispatcher.",
                    isRecoverable = true,
                    onRetry = { viewModel.retry() }
                )
            }
            
            uiState.hasAssignment -> {
                // Assignment info
                uiState.lorryAssignment?.let { assignment ->
                    AssignmentCard(assignment = assignment)
                    
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    if (assignment.stock_verified) {
                        // Already verified
                        Card(
                            colors = CardDefaults.cardColors(containerColor = AppColors.success.copy(alpha = 0.1f))
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp),
                                horizontalAlignment = Alignment.CenterHorizontally
                            ) {
                                Icon(
                                    Icons.Default.CheckCircle,
                                    contentDescription = null,
                                    tint = AppColors.success,
                                    modifier = Modifier.size(48.dp)
                                )
                                Spacer(modifier = Modifier.height(8.dp))
                                Text(
                                    text = "Stock Already Verified",
                                    style = MaterialTheme.typography.titleMedium,
                                    color = AppColors.success,
                                    fontWeight = FontWeight.Bold
                                )
                                Text(
                                    text = "You can now access your orders",
                                    style = MaterialTheme.typography.bodyMedium,
                                    textAlign = TextAlign.Center
                                )
                                
                                Spacer(modifier = Modifier.height(16.dp))
                                
                                Button(
                                    onClick = onNavigateToOrders,
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Text("Go to Orders")
                                }
                            }
                        }
                    } else {
                        // Need to verify stock
                        StockVerificationSection(
                            scannedUIDs = scannedUIDs,
                            onAddUID = { viewModel.addScannedUID(it) },
                            onRemoveUID = { viewModel.removeScannedUID(it) },
                            onClearAll = { viewModel.clearAllScannedUIDs() },
                            onClockIn = { lat, lng, locName ->
                                viewModel.clockInWithStockVerification(lat, lng, locName)
                            },
                            currentLocation = currentLocation,
                            locationName = locationName,
                            isProcessing = uiState.isProcessing,
                            canClockIn = uiState.canClockIn
                        )
                    }
                }
            }
        }
        
        // Error display
        uiState.error?.let { error ->
            Spacer(modifier = Modifier.height(16.dp))
            ErrorCard(
                message = error,
                isRecoverable = true,
                onRetry = { viewModel.clearError() }
            )
        }
    }
    
    // UID Input Dialog
    if (showUIDInput) {
        UIDInputDialog(
            onDismiss = { showUIDInput = false },
            onUIDScanned = { uid ->
                viewModel.addScannedUID(uid)
                showUIDInput = false
            }
        )
    }
}

@Composable
private fun AssignmentCard(assignment: com.yourco.driverAA.data.api.LorryAssignmentResponse) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Assigned Lorry",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (assignment.stock_verified) AppColors.success else AppColors.warning
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = if (assignment.stock_verified) "VERIFIED" else "PENDING",
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.White,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Lorry ID:",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = assignment.lorry_id,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
            }
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "Date:",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = assignment.assignment_date,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
            }
        }
    }
}

@Composable
private fun StockVerificationSection(
    scannedUIDs: List<String>,
    onAddUID: (String) -> Unit,
    onRemoveUID: (String) -> Unit,
    onClearAll: () -> Unit,
    onClockIn: (Double, Double, String?) -> Unit,
    currentLocation: Pair<Double, Double>?,
    locationName: String,
    isProcessing: Boolean,
    canClockIn: Boolean
) {
    var showUIDInput by remember { mutableStateOf(false) }
    
    Column {
        // UID Scanning Section
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(16.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Scanned UIDs",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    
                    Text(
                        text = "${scannedUIDs.size} items",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Medium
                    )
                }
                
                Spacer(modifier = Modifier.height(12.dp))
                
                // Scan buttons
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = { showUIDInput = true },
                        modifier = Modifier.weight(1f)
                    ) {
                        Icon(Icons.Default.QrCodeScanner, contentDescription = null)
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("Scan UID")
                    }
                    
                    if (scannedUIDs.isNotEmpty()) {
                        OutlinedButton(
                            onClick = onClearAll,
                            colors = ButtonDefaults.outlinedButtonColors(
                                contentColor = AppColors.error
                            )
                        ) {
                            Icon(Icons.Default.Clear, contentDescription = null)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Clear All")
                        }
                    }
                }
                
                if (scannedUIDs.isNotEmpty()) {
                    Spacer(modifier = Modifier.height(12.dp))
                    
                    // Scanned UIDs list
                    LazyColumn(
                        modifier = Modifier.heightIn(max = 200.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(scannedUIDs) { uid ->
                            Card(
                                colors = CardDefaults.cardColors(
                                    containerColor = AppColors.success.copy(alpha = 0.1f)
                                )
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 12.dp, vertical = 8.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = uid,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.Medium
                                    )
                                    
                                    IconButton(
                                        onClick = { onRemoveUID(uid) },
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
                }
            }
        }
        
        Spacer(modifier = Modifier.height(16.dp))
        
        // Clock-in button
        Button(
            onClick = {
                currentLocation?.let { (lat, lng) ->
                    onClockIn(lat, lng, locationName)
                }
            },
            modifier = Modifier.fillMaxWidth(),
            enabled = canClockIn && !isProcessing && currentLocation != null,
            colors = ButtonDefaults.buttonColors(
                containerColor = AppColors.success
            )
        ) {
            if (isProcessing) {
                CircularProgressIndicator(
                    modifier = Modifier.size(16.dp),
                    color = Color.White,
                    strokeWidth = 2.dp
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text("Processing...")
            } else {
                Icon(Icons.Default.PlayArrow, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Clock In & Verify Stock")
            }
        }
        
        if (!canClockIn) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "Complete stock verification to clock in",
                style = MaterialTheme.typography.bodySmall,
                color = AppColors.warning,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
    
    // UID Input Dialog
    if (showUIDInput) {
        UIDInputDialog(
            onDismiss = { showUIDInput = false },
            onUIDScanned = { uid ->
                onAddUID(uid)
                showUIDInput = false
            }
        )
    }
}

// Helper function to get current location (simplified)
private fun getCurrentLocation(
    context: android.content.Context,
    onLocationReceived: (Double, Double, String) -> Unit
) {
    // For now, using a placeholder implementation
    // In a real app, you'd use FusedLocationProviderClient
    onLocationReceived(0.0, 0.0, "Current Location")
}
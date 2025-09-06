package com.yourco.driverAA.ui.jobdetail

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
// import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.Image
import androidx.compose.ui.graphics.asImageBitmap
import android.graphics.BitmapFactory
import androidx.core.content.ContextCompat
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.compose.foundation.clickable
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.background
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import java.io.File

// Utility functions for WhatsApp integration
private fun normalizePhoneNumber(phone: String?): String? {
    if (phone.isNullOrBlank()) return null
    
    // Remove all non-digit characters except +
    val cleanPhone = phone.replace(Regex("[^\\d+]"), "")
    
    // Remove + and get digits only
    val digitsOnly = cleanPhone.replace("+", "")
    
    return when {
        // Already has Malaysia country code (60)
        digitsOnly.startsWith("60") && (digitsOnly.length == 12 || digitsOnly.length == 13) -> {
            digitsOnly
        }
        // Malaysian number starting with 0 (local format)
        digitsOnly.startsWith("0") && (digitsOnly.length == 10 || digitsOnly.length == 11) -> {
            "60" + digitsOnly.substring(1) // Remove 0 and add 60
        }
        // Malaysian mobile without leading 0 (10-11 digits starting with 1)
        digitsOnly.startsWith("1") && (digitsOnly.length == 9 || digitsOnly.length == 10) -> {
            "60$digitsOnly" // Add 60 prefix
        }
        // Other international numbers (already formatted)
        digitsOnly.length >= 10 -> {
            digitsOnly
        }
        // Too short, probably invalid
        else -> null
    }
}

private fun openWhatsApp(context: android.content.Context, phone: String) {
    val normalizedPhone = normalizePhoneNumber(phone) ?: return
    
    try {
        // Try to open WhatsApp directly
        val intent = Intent(Intent.ACTION_VIEW).apply {
            data = Uri.parse("https://api.whatsapp.com/send?phone=$normalizedPhone")
            setPackage("com.whatsapp")
        }
        context.startActivity(intent)
    } catch (e: Exception) {
        // If WhatsApp is not installed, open in browser
        try {
            val browserIntent = Intent(Intent.ACTION_VIEW).apply {
                data = Uri.parse("https://web.whatsapp.com/send?phone=$normalizedPhone")
            }
            context.startActivity(browserIntent)
        } catch (e2: Exception) {
            // Fallback to regular phone call
            try {
                val callIntent = Intent(Intent.ACTION_DIAL).apply {
                    data = Uri.parse("tel:$phone")
                }
                context.startActivity(callIntent)
            } catch (e3: Exception) {
                // Ignore if all fail
            }
        }
    }
}

private fun makePhoneCall(context: android.content.Context, phone: String) {
    try {
        val intent = Intent(Intent.ACTION_DIAL).apply {
            data = Uri.parse("tel:$phone")
        }
        context.startActivity(intent)
    } catch (e: Exception) {
        // Ignore if fails
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JobDetailScreen(
    jobId: String,
    onNavigateToActiveOrders: () -> Unit = {},
    viewModel: JobDetailViewModel = hiltViewModel()
) {
    val job by viewModel.job.collectAsState()
    val loading by viewModel.loading.collectAsState()
    val error by viewModel.error.collectAsState()
    val showOnHoldDialog by viewModel.showOnHoldDialog.collectAsState()
    val showUpsellDialog by viewModel.showUpsellDialog.collectAsState()
    val selectedUpsellItem by viewModel.selectedUpsellItem.collectAsState()
    val uploadingPhotos by viewModel.uploadingPhotos.collectAsState()
    val uploadedPhotos by viewModel.uploadedPhotos.collectAsState()
    val uploadedPhotoFiles by viewModel.uploadedPhotoFiles.collectAsState()
    val inventoryConfig by viewModel.inventoryConfig.collectAsState()
    val showUIDScanDialog by viewModel.showUIDScanDialog.collectAsState()
    val scannedUIDs by viewModel.scannedUIDs.collectAsState()
    val uidScanLoading by viewModel.uidScanLoading.collectAsState()

    LaunchedEffect(jobId) {
        viewModel.loadJob(jobId)
    }

    Column(modifier = Modifier.fillMaxSize()) {
        when {
            loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            }
            error != null -> {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text(
                        text = "Error: $error",
                        modifier = Modifier.padding(16.dp),
                        color = MaterialTheme.colorScheme.error
                    )
                }
            }
            job != null -> {
                JobDetailContent(
                    job = job!!,
                    onStatusUpdate = viewModel::updateStatus,
                    onUploadPhoto = viewModel::uploadPodPhoto,
                    onNavigateToActiveOrders = onNavigateToActiveOrders,
                    onUpsellItem = viewModel::showUpsellDialog,
                    uploadingPhotos = uploadingPhotos,
                    uploadedPhotos = uploadedPhotos,
                    uploadedPhotoFiles = uploadedPhotoFiles,
                    inventoryConfig = inventoryConfig,
                    scannedUIDs = scannedUIDs,
                    onShowUIDScan = viewModel::showUIDScanDialog
                )
            }
        }
    }
    
    // On-hold dialog
    if (showOnHoldDialog) {
        OnHoldDialog(
            onDismiss = { viewModel.dismissOnHoldDialog() },
            onResponse = { customerAvailable, deliveryDate -> 
                viewModel.handleOnHoldResponse(customerAvailable, deliveryDate)
            }
        )
    }
    
    // Upsell dialog
    if (showUpsellDialog && selectedUpsellItem != null) {
        UpsellDialog(
            item = selectedUpsellItem!!,
            onDismiss = { viewModel.dismissUpsellDialog() },
            onUpsell = { item, upsellType, newName, newPrice, installmentMonths ->
                viewModel.upsellItem(item, upsellType, newName, newPrice, installmentMonths)
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun JobDetailContent(
    job: JobDto,
    onStatusUpdate: (String) -> Unit,
    onUploadPhoto: (File, Int) -> Unit,
    onNavigateToActiveOrders: () -> Unit = {},
    onUpsellItem: ((JobItemDto) -> Unit)? = null,
    uploadingPhotos: Set<Int> = emptySet(),
    uploadedPhotos: Set<Int> = emptySet(),
    uploadedPhotoFiles: Map<Int, File> = emptyMap(),
    inventoryConfig: com.yourco.driverAA.data.api.InventoryConfigResponse? = null,
    scannedUIDs: List<com.yourco.driverAA.data.api.UIDScanResponse> = emptyList(),
    onShowUIDScan: () -> Unit = {}
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        item {
            // Header Card
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(
                            text = "Order #${job.code ?: job.id}",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold
                        )
                        AssistChip(
                            onClick = { },
                            label = { 
                                Text(
                                    text = job.status?.uppercase() ?: "UNKNOWN",
                                    style = MaterialTheme.typography.labelMedium
                                ) 
                            }
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    job.type?.let { type ->
                        Text(
                            text = "Type: $type",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }

        item {
            // Customer Info Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text(
                        text = "Customer Information",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    job.customer_name?.let { name ->
                        DetailRow(
                            icon = Icons.Default.Person,
                            label = "Name",
                            value = name
                        )
                    }
                    
                    job.customer_phone?.let { phone ->
                        CustomerPhoneSection(phone = phone)
                    }
                    
                    job.address?.let { address ->
                        DetailRow(
                            icon = Icons.Default.LocationOn,
                            label = "Address",
                            value = address
                        )
                    }
                    
                    job.delivery_date?.let { date ->
                        DetailRow(
                            icon = Icons.Default.DateRange,
                            label = "Delivery Date",
                            value = date
                        )
                    }
                }
            }
        }

        item {
            // Financial Info Card
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                ) {
                    Text(
                        text = "Financial Details",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(bottom = 8.dp)
                    )
                    
                    job.total?.let { total ->
                        DetailRow(
                            icon = Icons.Default.Star,
                            label = "Total",
                            value = "$$total"
                        )
                    }
                    
                    job.paid_amount?.let { paid ->
                        DetailRow(
                            icon = Icons.Default.Star,
                            label = "Paid",
                            value = "$$paid"
                        )
                    }
                    
                    job.balance?.let { balance ->
                        if (balance != "0.00") {
                            DetailRow(
                                icon = Icons.Default.Star,
                                label = "Balance",
                                value = "$$balance",
                                valueColor = MaterialTheme.colorScheme.error
                            )
                        }
                    }
                }
            }
        }

        job.items?.let { items ->
            if (items.isNotEmpty()) {
                item {
                    // Items Card
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            Text(
                                text = "Items (${items.size})",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(bottom = 8.dp)
                            )
                        }
                    }
                }
                
                items(items) { item ->
                    ItemCard(
                        item = item,
                        onUpsell = onUpsellItem
                    )
                }
            }
        }

        job.notes?.let { notes ->
            if (notes.isNotEmpty()) {
                item {
                    // Notes Card
                    Card(modifier = Modifier.fillMaxWidth()) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(16.dp)
                        ) {
                            Text(
                                text = "Notes",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(bottom = 8.dp)
                            )
                            Text(
                                text = notes,
                                style = MaterialTheme.typography.bodyMedium
                            )
                        }
                    }
                }
            }
        }

        // Show PoD photo section for IN_TRANSIT status
        if (job.status?.uppercase() == "IN_TRANSIT") {
            item {
                PodPhotosSection(
                    jobId = job.id,
                    onUploadPhoto = onUploadPhoto,
                    uploadingPhotos = uploadingPhotos,
                    uploadedPhotos = uploadedPhotos,
                    uploadedPhotoFiles = uploadedPhotoFiles
                )
            }
        }
        
        // Show UID scanning section after POD photos when enabled and order is delivered
        if (inventoryConfig?.uid_inventory_enabled == true && 
            job.status?.uppercase() == "DELIVERED" &&
            uploadedPhotos.isNotEmpty()) {
            item {
                UIDScanSection(
                    scannedUIDs = scannedUIDs,
                    isRequired = inventoryConfig.uid_scan_required_after_pod,
                    onShowUIDScan = onShowUIDScan
                )
            }
        }

        item {
            // Status Action Buttons
            StatusActionButtons(
                currentStatus = job.status ?: "assigned",
                onStatusUpdate = onStatusUpdate,
                onNavigateToActiveOrders = onNavigateToActiveOrders
            )
        }
    }
}

@Composable
private fun DetailRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String,
    valueColor: Color = Color.Unspecified
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            icon,
            contentDescription = null,
            modifier = Modifier.size(20.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(modifier = Modifier.width(12.dp))
        Text(
            text = "$label: ",
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.weight(0.3f)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(0.7f),
            color = valueColor
        )
    }
}

@Composable
private fun ItemCard(
    item: JobItemDto,
    onUpsell: ((JobItemDto) -> Unit)? = null
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = item.name ?: "Unknown Item",
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium
                    )
                    item.unit_price?.let { price ->
                        Text(
                            text = "RM$price seunit",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                Text(
                    text = "Kuantiti: ${item.qty ?: 0}",
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium
                )
            }
            
            // Upsell button
            if (onUpsell != null) {
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(
                    onClick = { onUpsell(item) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(Icons.Default.Star, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Upsell Barang")
                }
            }
        }
    }
}

@Composable
private fun StatusActionButtons(
    currentStatus: String,
    onStatusUpdate: (String) -> Unit,
    onNavigateToActiveOrders: () -> Unit = {}
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Order Actions",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 12.dp)
            )
            
            when (currentStatus.uppercase()) {
                "ASSIGNED" -> {
                    Button(
                        onClick = { onStatusUpdate("IN_TRANSIT") },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Start Order")
                    }
                }
                "IN_TRANSIT" -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = { onStatusUpdate("ON_HOLD") },
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.secondary
                            )
                        ) {
                            Icon(Icons.Default.Star, contentDescription = null)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Hold")
                        }
                        Button(
                            onClick = { onStatusUpdate("DELIVERED") },
                            modifier = Modifier.weight(1f),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.tertiary
                            )
                        ) {
                            Icon(Icons.Default.CheckCircle, contentDescription = null)
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Complete")
                        }
                    }
                }
                "ON_HOLD" -> {
                    Button(
                        onClick = { onStatusUpdate("IN_TRANSIT") },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.primary
                        )
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Resume Order")
                    }
                }
                "DELIVERED", "SUCCESS" -> {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.primaryContainer
                            )
                        ) {
                            Text(
                                text = "✓ Order Completed Successfully",
                                modifier = Modifier.padding(12.dp),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onPrimaryContainer,
                                fontWeight = FontWeight.Medium
                            )
                        }
                        Button(
                            onClick = onNavigateToActiveOrders,
                            modifier = Modifier.fillMaxWidth(),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = MaterialTheme.colorScheme.secondary
                            )
                        ) {
                            Icon(Icons.Default.List, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("View Active Orders")
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PodPhotosSection(
    jobId: String,
    onUploadPhoto: (File, Int) -> Unit,
    uploadingPhotos: Set<Int>,
    uploadedPhotos: Set<Int>,
    uploadedPhotoFiles: Map<Int, File> = emptyMap()
) {
    val context = LocalContext.current
    var photoFiles by remember { mutableStateOf(mutableMapOf<Int, File?>()) }
    var selectedPhotoForPreview by remember { mutableStateOf<File?>(null) }
    var hasCameraPermission by remember { 
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED
        )
    }
    
    // Permission launcher
    val requestCameraPermission = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        hasCameraPermission = isGranted
    }
    
    // Create persistent file for camera (stored in app's private storage)
    fun createImageFile(photoNumber: Int): File {
        val fileName = "POD_${jobId}_${photoNumber}_${System.currentTimeMillis()}.jpg"
        val photosDir = File(context.filesDir, "pod_photos")
        
        // Ensure directory exists (File.mkdirs() is thread-safe)
        if (!photosDir.exists()) {
            val created = photosDir.mkdirs()
            android.util.Log.d("PhotoUpload", "Created pod_photos directory: $created, path: ${photosDir.absolutePath}")
        }
        
        val file = File(photosDir, fileName)
        android.util.Log.d("PhotoUpload", "Created image file path: ${file.absolutePath}")
        return file
    }
    
    // Camera launcher for each photo slot
    val takePicture1 = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            photoFiles[1]?.let { file ->
                onUploadPhoto(file, 1)
            }
        }
    }
    
    val takePicture2 = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            photoFiles[2]?.let { file ->
                onUploadPhoto(file, 2)
            }
        }
    }
    
    val takePicture3 = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            photoFiles[3]?.let { file ->
                onUploadPhoto(file, 3)
            }
        }
    }
    
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = "Proof of Delivery Photos",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 12.dp)
            )
            
            Text(
                text = "Take up to 3 photos as proof of delivery. Photos are required to complete the order.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 16.dp)
            )
            
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(3) { index ->
                    val photoNumber = index + 1
                    PhotoCaptureButton(
                        photoNumber = photoNumber,
                        photoFile = uploadedPhotoFiles[photoNumber] ?: photoFiles[photoNumber],
                        isUploading = uploadingPhotos.contains(photoNumber),
                        isUploaded = uploadedPhotos.contains(photoNumber),
                        onTakePhoto = {
                            if (hasCameraPermission) {
                                try {
                                    val file = createImageFile(photoNumber)
                                    photoFiles[photoNumber] = file
                                    
                                    android.util.Log.d("PhotoUpload", "Attempting to create URI for file: ${file.absolutePath}")
                                    android.util.Log.d("PhotoUpload", "Package name: ${context.packageName}")
                                    android.util.Log.d("PhotoUpload", "Application ID: ${context.applicationInfo.packageName}")
                                    
                                    val authority = "com.yourco.driverAA.fileprovider"
                                    val uri = FileProvider.getUriForFile(
                                        context,
                                        authority,
                                        file
                                    )
                                    
                                    android.util.Log.d("PhotoUpload", "Created URI: $uri")
                                    
                                    when (photoNumber) {
                                        1 -> takePicture1.launch(uri)
                                        2 -> takePicture2.launch(uri)
                                        3 -> takePicture3.launch(uri)
                                    }
                                } catch (e: Exception) {
                                    android.util.Log.e("PhotoUpload", "Error launching camera for photo $photoNumber", e)
                                    android.util.Log.e("PhotoUpload", "Error details: ${e.message}")
                                    e.printStackTrace()
                                }
                            } else {
                                requestCameraPermission.launch(Manifest.permission.CAMERA)
                            }
                        },
                        onPreviewPhoto = { file ->
                            selectedPhotoForPreview = file
                        }
                    )
                }
            }
        }
    }
    
    // Large photo preview dialog
    selectedPhotoForPreview?.let { photoFile ->
        PhotoPreviewDialog(
            photoFile = photoFile,
            onDismiss = { selectedPhotoForPreview = null }
        )
    }
}

@Composable
private fun PhotoCaptureButton(
    photoNumber: Int,
    photoFile: File?,
    onTakePhoto: () -> Unit,
    isUploading: Boolean = false,
    isUploaded: Boolean = false,
    onPreviewPhoto: ((File) -> Unit)? = null
) {
    OutlinedCard(
        modifier = Modifier
            .size(100.dp), // Increased size for better preview
        onClick = if (!isUploading) onTakePhoto else { {} },
        colors = CardDefaults.outlinedCardColors(
            containerColor = if (isUploaded) 
                MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
            else MaterialTheme.colorScheme.surface
        )
    ) {
        if (photoFile != null && photoFile.exists()) {
            // Show photo preview using BitmapFactory (load bitmap in remember to avoid recomposition issues)
            val bitmap = remember(photoFile) {
                try {
                    if (photoFile.exists() && photoFile.length() > 0) {
                        BitmapFactory.decodeFile(photoFile.absolutePath)
                    } else {
                        android.util.Log.w("PhotoUpload", "Photo file does not exist or is empty: ${photoFile.absolutePath}")
                        null
                    }
                } catch (e: Exception) {
                    android.util.Log.e("PhotoUpload", "Error loading bitmap from ${photoFile.absolutePath}", e)
                    null
                }
            }
            
            if (bitmap != null) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .then(
                            if (onPreviewPhoto != null && !isUploading) {
                                Modifier.clickable { onPreviewPhoto(photoFile) }
                            } else {
                                Modifier
                            }
                        )
                ) {
                    Image(
                        bitmap = bitmap.asImageBitmap(),
                        contentDescription = "Photo $photoNumber preview",
                        modifier = Modifier
                            .fillMaxSize()
                            .clip(MaterialTheme.shapes.small),
                        contentScale = ContentScale.Crop
                    )
                    
                    // Upload status overlay
                    if (isUploading) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(
                                    Color.Black.copy(alpha = 0.5f),
                                    MaterialTheme.shapes.small
                                ),
                            contentAlignment = Alignment.Center
                        ) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(24.dp),
                                color = MaterialTheme.colorScheme.primary,
                                strokeWidth = 2.dp
                            )
                        }
                    } else if (isUploaded) {
                        Box(
                            modifier = Modifier
                                .padding(4.dp)
                                .align(Alignment.TopEnd)
                                .background(
                                    MaterialTheme.colorScheme.primary,
                                    CircleShape
                                )
                                .size(20.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                Icons.Default.Check,
                                contentDescription = "Uploaded",
                                modifier = Modifier.size(12.dp),
                                tint = MaterialTheme.colorScheme.onPrimary
                            )
                        }
                    }
                }
            } else {
                // Fallback if bitmap loading fails
                Text(
                    "📷\nPhoto $photoNumber\nTaken",
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        } else {
            // Show placeholder with add icon
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "📷",
                        style = MaterialTheme.typography.headlineMedium
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "Photo $photoNumber",
                        style = MaterialTheme.typography.labelSmall
                    )
                }
            }
        }
    }
}

@Composable
private fun CustomerPhoneSection(phone: String) {
    val context = LocalContext.current
    
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        // Phone number display
        DetailRow(
            icon = Icons.Default.Phone,
            label = "Phone",
            value = phone
        )
        
        // Contact buttons
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            // WhatsApp button
            Button(
                onClick = { openWhatsApp(context, phone) },
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(
                    containerColor = Color(0xFF25D366) // WhatsApp green
                ),
                contentPadding = PaddingValues(8.dp)
            ) {
                Text(
                    "💬",
                    style = MaterialTheme.typography.labelSmall
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    "WhatsApp",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White
                )
            }
            
            // Call button
            Button(
                onClick = { makePhoneCall(context, phone) },
                modifier = Modifier.weight(1f),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.primary
                ),
                contentPadding = PaddingValues(8.dp)
            ) {
                Icon(
                    Icons.Default.Phone,
                    contentDescription = "Call",
                    modifier = Modifier.size(16.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    "Call",
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun OnHoldDialog(
    onDismiss: () -> Unit,
    onResponse: (customerAvailable: Boolean, deliveryDate: String?) -> Unit
) {
    var selectedDate by remember { mutableStateOf("") }
    var selectedDateLabel by remember { mutableStateOf("") }
    var showDatePicker by remember { mutableStateOf(false) }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "Customer Not Available",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "Did the customer give you a specific date for delivery?",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                if (selectedDateLabel.isNotEmpty()) {
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    ) {
                        Text(
                            text = "Selected: $selectedDateLabel",
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        },
        confirmButton = {
            Column(
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Yes, customer gave specific date
                Button(
                    onClick = { showDatePicker = true },
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.primary
                    )
                ) {
                    Icon(Icons.Default.DateRange, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Yes - Select Date")
                }
                
                // Submit with selected date
                if (selectedDate.isNotEmpty()) {
                    Button(
                        onClick = { onResponse(true, selectedDate) },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = MaterialTheme.colorScheme.tertiary
                        )
                    ) {
                        Icon(Icons.Default.CheckCircle, contentDescription = null)
                        Spacer(modifier = Modifier.width(8.dp))
                        Text("Confirm Date")
                    }
                }
                
                // No, customer has no preference
                OutlinedButton(
                    onClick = { onResponse(false, null) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.Star, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("No Specific Date - Tomorrow")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
    
    // Simple date picker using AlertDialog
    if (showDatePicker) {
        AlertDialog(
            onDismissRequest = { showDatePicker = false },
            title = { Text("Select Delivery Date") },
            text = {
                Column {
                    Text("When does customer want delivery?")
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    // Quick date options
                    val today = java.time.LocalDate.now()
                    val options = listOf(
                        "Today" to today.toString(),
                        "Tomorrow" to today.plusDays(1).toString(),
                        "Day After Tomorrow" to today.plusDays(2).toString(),
                        "Next Week" to today.plusWeeks(1).toString()
                    )
                    
                    options.forEach { (label, dateValue) ->
                        TextButton(
                            onClick = {
                                selectedDate = dateValue
                                selectedDateLabel = label
                                showDatePicker = false
                            },
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(label, modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showDatePicker = false }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UpsellDialog(
    item: JobItemDto,
    onDismiss: () -> Unit,
    onUpsell: (JobItemDto, String, String?, Double, Int?) -> Unit
) {
    var selectedUpsellType by remember { mutableStateOf("BELI_TERUS") }
    var newName by remember { mutableStateOf(item.name ?: "") }
    var newPriceText by remember { mutableStateOf("") }
    var installmentMonths by remember { mutableStateOf("12") }
    
    // Current item price for reference
    val currentPrice = (item.unit_price?.let { it.toDoubleOrNull() } ?: 0.0) * (item.qty ?: 1)
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "Upsell Barang",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Item info
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant
                    )
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Text(
                            text = "Barang Asal:",
                            style = MaterialTheme.typography.labelMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = item.name ?: "Unknown Item",
                            style = MaterialTheme.typography.bodyMedium,
                            fontWeight = FontWeight.Medium
                        )
                        Text(
                            text = "Harga Asal: RM${String.format("%.2f", currentPrice)}",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                
                // Upsell type selection
                Text(
                    text = "Pilih Jenis Upsell:",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Medium
                )
                
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Beli Terus option
                    FilterChip(
                        onClick = { selectedUpsellType = "BELI_TERUS" },
                        label = { Text("Beli Terus") },
                        selected = selectedUpsellType == "BELI_TERUS",
                        modifier = Modifier.weight(1f)
                    )
                    
                    // Ansuran option  
                    FilterChip(
                        onClick = { selectedUpsellType = "ANSURAN" },
                        label = { Text("Ansuran") },
                        selected = selectedUpsellType == "ANSURAN",
                        modifier = Modifier.weight(1f)
                    )
                }
                
                // New item name
                OutlinedTextField(
                    value = newName,
                    onValueChange = { newName = it },
                    label = { Text("Nama Barang Baru (Opsyenal)") },
                    modifier = Modifier.fillMaxWidth()
                )
                
                // New price
                OutlinedTextField(
                    value = newPriceText,
                    onValueChange = { newPriceText = it },
                    label = { Text("Harga Baru (RM)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    modifier = Modifier.fillMaxWidth(),
                    placeholder = { Text("cth: 1000") }
                )
                
                // Installment months (only for ANSURAN)
                if (selectedUpsellType == "ANSURAN") {
                    OutlinedTextField(
                        value = installmentMonths,
                        onValueChange = { installmentMonths = it },
                        label = { Text("Tempoh Ansuran (Bulan)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        modifier = Modifier.fillMaxWidth(),
                        placeholder = { Text("cth: 12") }
                    )
                    
                    // Show monthly calculation
                    val newPrice = newPriceText.toDoubleOrNull() ?: 0.0
                    val months = installmentMonths.toIntOrNull() ?: 1
                    if (newPrice > 0 && months > 0) {
                        val monthlyAmount = newPrice / months
                        Text(
                            text = "Bayaran Bulanan: RM${String.format("%.2f", monthlyAmount)} x $months bulan",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Medium
                        )
                    }
                }
            }
        },
        confirmButton = {
            val newPrice = newPriceText.toDoubleOrNull()
            val months = if (selectedUpsellType == "ANSURAN") installmentMonths.toIntOrNull() else null
            val isValid = newPrice != null && newPrice > 0 && 
                         (selectedUpsellType == "BELI_TERUS" || (months != null && months > 0))
            
            Button(
                onClick = {
                    if (isValid) {
                        onUpsell(
                            item,
                            selectedUpsellType,
                            newName.takeIf { it != item.name },
                            newPrice!!,
                            months
                        )
                    }
                },
                enabled = isValid
            ) {
                Text("${if (selectedUpsellType == "BELI_TERUS") "Beli Terus" else "Ansuran"} RM${newPrice?.let { String.format("%.2f", it) } ?: "0.00"}")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Batal")
            }
        }
    )
}

@Composable
private fun PhotoPreviewDialog(
    photoFile: File,
    onDismiss: () -> Unit
) {
    val bitmap = remember(photoFile) {
        try {
            if (photoFile.exists() && photoFile.length() > 0) {
                BitmapFactory.decodeFile(photoFile.absolutePath)
            } else {
                android.util.Log.w("PhotoUpload", "Preview photo file does not exist or is empty: ${photoFile.absolutePath}")
                null
            }
        } catch (e: Exception) {
            android.util.Log.e("PhotoUpload", "Error loading preview bitmap from ${photoFile.absolutePath}", e)
            null
        }
    }
    
    Dialog(
        onDismissRequest = onDismiss,
        properties = DialogProperties(
            dismissOnBackPress = true,
            dismissOnClickOutside = true,
            usePlatformDefaultWidth = false
        )
    ) {
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            shape = MaterialTheme.shapes.large
        ) {
            Column {
                // Header
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "Photo Preview",
                        style = MaterialTheme.typography.titleLarge,
                        fontWeight = FontWeight.Bold
                    )
                    IconButton(onClick = onDismiss) {
                        Icon(Icons.Default.Close, contentDescription = "Close")
                    }
                }
                
                // Photo
                if (bitmap != null) {
                    Image(
                        bitmap = bitmap.asImageBitmap(),
                        contentDescription = "Full size photo preview",
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(max = 400.dp)
                            .padding(horizontal = 16.dp),
                        contentScale = ContentScale.Fit
                    )
                } else {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(200.dp)
                            .padding(16.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "Unable to load photo",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                
                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
    
    // UID Scan dialog
    if (showUIDScanDialog) {
        UIDScanDialog(
            onDismiss = { viewModel.dismissUIDScanDialog() },
            onScanUID = { uid -> 
                viewModel.scanUID(uid)
                viewModel.dismissUIDScanDialog()
            },
            isLoading = uidScanLoading
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UIDScanSection(
    scannedUIDs: List<com.yourco.driverAA.data.api.UIDScanResponse>,
    isRequired: Boolean,
    onShowUIDScan: () -> Unit
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "UID Tracking",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                
                if (isRequired) {
                    AssistChip(
                        onClick = { },
                        label = { 
                            Text(
                                text = "DIPERLUKAN",
                                style = MaterialTheme.typography.labelSmall
                            ) 
                        },
                        colors = AssistChipDefaults.assistChipColors(
                            containerColor = MaterialTheme.colorScheme.errorContainer,
                            labelColor = MaterialTheme.colorScheme.onErrorContainer
                        )
                    )
                } else {
                    AssistChip(
                        onClick = { },
                        label = { 
                            Text(
                                text = "PILIHAN",
                                style = MaterialTheme.typography.labelSmall
                            ) 
                        }
                    )
                }
            }
            
            Spacer(modifier = Modifier.height(8.dp))
            
            Text(
                text = if (isRequired) {
                    "Sila imbas UID barang yang dihantar. UID diperlukan untuk melengkapkan pesanan ini."
                } else {
                    "Sila imbas UID barang yang dihantar untuk tujuan inventori (pilihan)."
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(bottom = 16.dp)
            )
            
            // Show scanned UIDs
            if (scannedUIDs.isNotEmpty()) {
                Text(
                    text = "UID Diimbas (${scannedUIDs.size})",
                    style = MaterialTheme.typography.labelMedium,
                    fontWeight = FontWeight.Medium,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                
                scannedUIDs.forEach { scanned ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 2.dp),
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = scanned.uid,
                                    style = MaterialTheme.typography.bodyMedium,
                                    fontWeight = FontWeight.Medium
                                )
                                scanned.sku_name?.let { name ->
                                    Text(
                                        text = name,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                            Icon(
                                Icons.Default.CheckCircle,
                                contentDescription = "Scanned",
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(12.dp))
            }
            
            // Scan button
            Button(
                onClick = onShowUIDScan,
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = if (isRequired && scannedUIDs.isEmpty()) {
                        MaterialTheme.colorScheme.primary
                    } else {
                        MaterialTheme.colorScheme.secondary
                    }
                )
            ) {
                Icon(Icons.Default.Add, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Imbas UID")
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun UIDScanDialog(
    onDismiss: () -> Unit,
    onScanUID: (String) -> Unit,
    isLoading: Boolean = false
) {
    var uidText by remember { mutableStateOf("") }
    
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "Imbas UID",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
        },
        text = {
            Column(
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    text = "Masukkan atau imbas UID barang yang dihantar:",
                    style = MaterialTheme.typography.bodyMedium
                )
                
                OutlinedTextField(
                    value = uidText,
                    onValueChange = { uidText = it },
                    label = { Text("UID") },
                    placeholder = { Text("cth: AA123456789") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    enabled = !isLoading
                )
                
                if (isLoading) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Center,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        CircularProgressIndicator(
                            modifier = Modifier.size(16.dp),
                            strokeWidth = 2.dp
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "Memproses...",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        },
        confirmButton = {
            Button(
                onClick = { 
                    if (uidText.isNotBlank()) {
                        onScanUID(uidText)
                        uidText = ""
                    }
                },
                enabled = uidText.isNotBlank() && !isLoading
            ) {
                Text("Rekod UID")
            }
        },
        dismissButton = {
            TextButton(
                onClick = onDismiss,
                enabled = !isLoading
            ) {
                Text("Batal")
            }
        }
    )
}

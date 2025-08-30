package com.yourco.driverAA.ui.jobdetail

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.Image
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
import androidx.compose.ui.unit.dp
import coil.compose.rememberAsyncImagePainter
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import java.io.File

// Utility functions for WhatsApp integration
private fun normalizePhoneNumber(phone: String?): String? {
    if (phone.isNullOrBlank()) return null
    
    // Remove all non-digit characters
    val digitsOnly = phone.replace(Regex("[^\\d]"), "")
    
    return when {
        // If it starts with country code (e.g., 234), use as is
        digitsOnly.length > 10 && (digitsOnly.startsWith("234") || digitsOnly.startsWith("1") || digitsOnly.startsWith("44")) -> {
            digitsOnly
        }
        // If it's a typical Nigerian number starting with 0, replace with 234
        digitsOnly.startsWith("0") && digitsOnly.length == 11 -> {
            "234" + digitsOnly.substring(1)
        }
        // If it's 10 digits, assume Nigerian and add 234
        digitsOnly.length == 10 -> {
            "234$digitsOnly"
        }
        // For other patterns, return as is if it looks valid
        digitsOnly.length >= 10 -> digitsOnly
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
                    onNavigateToActiveOrders = onNavigateToActiveOrders
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun JobDetailContent(
    job: JobDto,
    onStatusUpdate: (String) -> Unit,
    onUploadPhoto: (File, Int) -> Unit,
    onNavigateToActiveOrders: () -> Unit = {}
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
                    ItemCard(item = item)
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
                    onUploadPhoto = onUploadPhoto
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
private fun ItemCard(item: JobItemDto) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
        )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
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
                        text = "$$price each",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Text(
                text = "Qty: ${item.qty ?: 0}",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium
            )
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
    onUploadPhoto: (File, Int) -> Unit
) {
    val context = LocalContext.current
    var photoFiles by remember { mutableStateOf(mutableMapOf<Int, File?>()) }
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
    
    // Create temp file for camera
    fun createImageFile(photoNumber: Int): File {
        val fileName = "POD_${jobId}_${photoNumber}_${System.currentTimeMillis()}.jpg"
        return File(context.cacheDir, fileName)
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
                        photoFile = photoFiles[photoNumber],
                        onTakePhoto = {
                            if (hasCameraPermission) {
                                val file = createImageFile(photoNumber)
                                photoFiles[photoNumber] = file
                                val uri = FileProvider.getUriForFile(
                                    context,
                                    "${context.packageName}.fileprovider",
                                    file
                                )
                                when (photoNumber) {
                                    1 -> takePicture1.launch(uri)
                                    2 -> takePicture2.launch(uri)
                                    3 -> takePicture3.launch(uri)
                                }
                            } else {
                                requestCameraPermission.launch(Manifest.permission.CAMERA)
                            }
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun PhotoCaptureButton(
    photoNumber: Int,
    photoFile: File?,
    onTakePhoto: () -> Unit
) {
    OutlinedCard(
        modifier = Modifier
            .size(80.dp),
        onClick = onTakePhoto
    ) {
        if (photoFile != null && photoFile.exists()) {
            // Show photo preview
            Image(
                painter = rememberAsyncImagePainter(photoFile),
                contentDescription = "Photo $photoNumber preview",
                modifier = Modifier
                    .fillMaxSize()
                    .clip(MaterialTheme.shapes.small),
                contentScale = ContentScale.Crop
            )
            // Add a small camera icon overlay to indicate it can be retaken
            Box(
                modifier = Modifier.fillMaxSize(),
                contentAlignment = Alignment.TopEnd
            ) {
                Icon(
                    Icons.Default.PhotoCamera,
                    contentDescription = "Retake photo $photoNumber",
                    modifier = Modifier
                        .size(16.dp)
                        .padding(2.dp),
                    tint = Color.White
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
                    Icon(
                        Icons.Default.Add,
                        contentDescription = "Take photo $photoNumber",
                        modifier = Modifier.size(24.dp)
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
                Icon(
                    Icons.Default.Chat, // Using chat icon as proxy for WhatsApp
                    contentDescription = "WhatsApp",
                    modifier = Modifier.size(16.dp),
                    tint = Color.White
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

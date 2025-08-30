package com.yourco.driverAA.ui.jobdetail

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun JobDetailScreen(
    jobId: String,
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
                    onUploadPhoto = viewModel::uploadPodPhoto
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
    onUploadPhoto: (File, Int) -> Unit
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
                        DetailRow(
                            icon = Icons.Default.Phone,
                            label = "Phone",
                            value = phone
                        )
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
                onStatusUpdate = onStatusUpdate
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
    onStatusUpdate: (String) -> Unit
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
                    Card(
                        colors = CardDefaults.cardColors(
                            containerColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    ) {
                        Text(
                            text = "Order Completed",
                            modifier = Modifier.padding(12.dp),
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onPrimaryContainer
                        )
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
                        onTakePhoto = {
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
    onTakePhoto: () -> Unit
) {
    OutlinedCard(
        modifier = Modifier
            .size(80.dp),
        onClick = onTakePhoto
    ) {
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

package com.yourco.driverAA.ui.stockverification

import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import com.google.zxing.BarcodeFormat
import com.google.zxing.DecodeHintType
import com.google.zxing.MultiFormatReader
import com.google.zxing.common.HybridBinarizer
import com.google.zxing.BinaryBitmap
import com.google.zxing.RGBLuminanceSource
import androidx.camera.core.ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.RectangleShape
import com.yourco.driverAA.ui.theme.AppColors
import java.nio.ByteBuffer
import java.util.concurrent.Executors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StockQRScannerScreen(
    onDismiss: () -> Unit,
    onUIDScanned: (String) -> Unit,
    scannedUIDs: List<String> = emptyList(),
    title: String = "Scan Stock UIDs"
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    var hasFlash by remember { mutableStateOf(false) }
    var flashEnabled by remember { mutableStateOf(false) }
    var lastScannedUID by remember { mutableStateOf<String?>(null) }
    var showValidationDialog by remember { mutableStateOf(false) }
    var validationUID by remember { mutableStateOf("") }
    var isValidUID by remember { mutableStateOf(false) }
    
    LaunchedEffect(Unit) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        val cameraProvider = cameraProviderFuture.get()
        hasFlash = cameraProvider.hasCamera(CameraSelector.DEFAULT_BACK_CAMERA)
    }
    
    // Handle scan validation
    val handleUIDScanned = { uid: String ->
        if (uid != lastScannedUID) { // Prevent duplicate rapid scans
            lastScannedUID = uid
            validationUID = uid
            isValidUID = uid.isNotBlank() && !scannedUIDs.contains(uid)
            showValidationDialog = true
        }
    }
    
    Scaffold(
        topBar = {
            TopAppBar(
                title = { 
                    Column {
                        Text(
                            text = title,
                            color = Color.White
                        )
                        Text(
                            text = "${scannedUIDs.size} UIDs scanned",
                            color = Color.White.copy(alpha = 0.8f),
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onDismiss) {
                        Icon(
                            Icons.Default.Close, 
                            contentDescription = "Close",
                            tint = Color.White
                        )
                    }
                },
                actions = {
                    if (hasFlash) {
                        IconButton(onClick = { flashEnabled = !flashEnabled }) {
                            Icon(
                                if (flashEnabled) Icons.Default.FlashOn else Icons.Default.FlashOff,
                                contentDescription = if (flashEnabled) "Turn off flash" else "Turn on flash",
                                tint = Color.White
                            )
                        }
                    }
                    
                    // Done button
                    TextButton(
                        onClick = onDismiss,
                        colors = ButtonDefaults.textButtonColors(
                            contentColor = Color.White
                        )
                    ) {
                        Text("DONE")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color.Black.copy(alpha = 0.8f)
                )
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black)
                .padding(paddingValues)
        ) {
            // Camera Preview
            ContinuousCameraPreview(
                onQRCodeScanned = handleUIDScanned,
                flashEnabled = flashEnabled,
                modifier = Modifier.fillMaxSize(),
                isPaused = showValidationDialog
            )
            
            // Scan Area Overlay
            ScanOverlay(
                modifier = Modifier.fillMaxSize()
            )
            
            // Instructions
            Card(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp)
                    .fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = Color.Black.copy(alpha = 0.8f)
                ),
                shape = RoundedCornerShape(12.dp)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "Point camera at QR code to scan",
                        color = Color.White,
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.bodyMedium
                    )
                    
                    if (scannedUIDs.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Recent: ${scannedUIDs.takeLast(3).joinToString(", ")}",
                            color = AppColors.success,
                            textAlign = TextAlign.Center,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }
    }
    
    // UID Validation Dialog
    if (showValidationDialog) {
        UIDValidationDialog(
            uid = validationUID,
            isValid = isValidUID,
            isDuplicate = scannedUIDs.contains(validationUID),
            onConfirm = {
                if (isValidUID) {
                    onUIDScanned(validationUID)
                }
                showValidationDialog = false
                lastScannedUID = null // Allow scanning same UID again if needed
            },
            onRetry = {
                showValidationDialog = false
                lastScannedUID = null // Allow re-scanning
            }
        )
    }
}

@Composable
private fun ContinuousCameraPreview(
    onQRCodeScanned: (String) -> Unit,
    flashEnabled: Boolean,
    isPaused: Boolean,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val cameraExecutor = remember { Executors.newSingleThreadExecutor() }
    var camera by remember { mutableStateOf<Camera?>(null) }
    
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            val previewView = PreviewView(ctx)
            val cameraProviderFuture = ProcessCameraProvider.getInstance(ctx)
            
            cameraProviderFuture.addListener({
                val cameraProvider = cameraProviderFuture.get()
                
                val preview = Preview.Builder().build().also {
                    it.setSurfaceProvider(previewView.surfaceProvider)
                }
                
                val imageAnalyzer = ImageAnalysis.Builder()
                    .setBackpressureStrategy(STRATEGY_KEEP_ONLY_LATEST)
                    .build()
                    .also {
                        it.setAnalyzer(cameraExecutor, ContinuousQRCodeAnalyzer(
                            onQRCodeScanned = onQRCodeScanned,
                            isPaused = { isPaused }
                        ))
                    }
                
                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
                
                try {
                    cameraProvider.unbindAll()
                    camera = cameraProvider.bindToLifecycle(
                        lifecycleOwner,
                        cameraSelector,
                        preview,
                        imageAnalyzer
                    )
                } catch (exc: Exception) {
                    // Handle error
                }
            }, ContextCompat.getMainExecutor(ctx))
            
            previewView
        }
    )
    
    // Control flash
    LaunchedEffect(flashEnabled) {
        camera?.cameraControl?.enableTorch(flashEnabled)
    }
}

@Composable
private fun ScanOverlay(modifier: Modifier = Modifier) {
    Box(modifier = modifier) {
        // Semi-transparent overlay
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Black.copy(alpha = 0.5f))
        )
        
        // Scan area cutout
        Box(
            modifier = Modifier
                .size(250.dp)
                .align(Alignment.Center)
                .border(2.dp, Color.White, RoundedCornerShape(12.dp))
                .clip(RoundedCornerShape(12.dp))
        ) {
            // Corner indicators
            val cornerSize = 20.dp
            val cornerThickness = 3.dp
            
            // Top-left corner
            Box(
                modifier = Modifier
                    .size(cornerSize)
                    .align(Alignment.TopStart)
                    .background(Color.Transparent)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(cornerThickness)
                        .background(Color.White)
                )
                Box(
                    modifier = Modifier
                        .width(cornerThickness)
                        .fillMaxHeight()
                        .background(Color.White)
                )
            }
            
            // Top-right corner
            Box(
                modifier = Modifier
                    .size(cornerSize)
                    .align(Alignment.TopEnd)
                    .background(Color.Transparent)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(cornerThickness)
                        .background(Color.White)
                )
                Box(
                    modifier = Modifier
                        .width(cornerThickness)
                        .fillMaxHeight()
                        .align(Alignment.TopEnd)
                        .background(Color.White)
                )
            }
            
            // Bottom-left corner
            Box(
                modifier = Modifier
                    .size(cornerSize)
                    .align(Alignment.BottomStart)
                    .background(Color.Transparent)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(cornerThickness)
                        .align(Alignment.BottomStart)
                        .background(Color.White)
                )
                Box(
                    modifier = Modifier
                        .width(cornerThickness)
                        .fillMaxHeight()
                        .background(Color.White)
                )
            }
            
            // Bottom-right corner
            Box(
                modifier = Modifier
                    .size(cornerSize)
                    .align(Alignment.BottomEnd)
                    .background(Color.Transparent)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(cornerThickness)
                        .align(Alignment.BottomStart)
                        .background(Color.White)
                )
                Box(
                    modifier = Modifier
                        .width(cornerThickness)
                        .fillMaxHeight()
                        .align(Alignment.TopEnd)
                        .background(Color.White)
                )
            }
        }
    }
}

@Composable
private fun UIDValidationDialog(
    uid: String,
    isValid: Boolean,
    isDuplicate: Boolean,
    onConfirm: () -> Unit,
    onRetry: () -> Unit
) {
    AlertDialog(
        onDismissRequest = { /* Prevent dismissing by tapping outside */ },
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    if (isValid) Icons.Default.CheckCircle else Icons.Default.Error,
                    contentDescription = null,
                    tint = if (isValid) AppColors.success else AppColors.error,
                    modifier = Modifier.size(24.dp)
                )
                Text(
                    text = if (isValid) "Valid UID Scanned" else if (isDuplicate) "Duplicate UID" else "Invalid UID",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            Column {
                Card(
                    colors = CardDefaults.cardColors(
                        containerColor = if (isValid) AppColors.success.copy(alpha = 0.1f) 
                                      else AppColors.error.copy(alpha = 0.1f)
                    )
                ) {
                    Text(
                        text = uid,
                        modifier = Modifier.padding(12.dp),
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                }
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = when {
                        isDuplicate -> "This UID has already been scanned."
                        !isValid -> "This UID is invalid or empty."
                        else -> "UID is valid and ready to be added."
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (isValid) AppColors.success else AppColors.error
                )
            }
        },
        confirmButton = {
            if (isValid) {
                Button(
                    onClick = onConfirm,
                    colors = ButtonDefaults.buttonColors(
                        containerColor = AppColors.success
                    )
                ) {
                    Icon(Icons.Default.Check, contentDescription = null)
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("YES - Add UID")
                }
            }
        },
        dismissButton = {
            OutlinedButton(
                onClick = onRetry,
                colors = ButtonDefaults.outlinedButtonColors(
                    contentColor = if (isValid) MaterialTheme.colorScheme.primary else AppColors.error
                )
            ) {
                Icon(
                    if (isValid) Icons.Default.CameraAlt else Icons.Default.Refresh, 
                    contentDescription = null
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(if (isValid) "Continue Scanning" else "NO - Retry")
            }
        }
    )
}

private class ContinuousQRCodeAnalyzer(
    private val onQRCodeScanned: (String) -> Unit,
    private val isPaused: () -> Boolean
) : ImageAnalysis.Analyzer {
    
    private val reader = MultiFormatReader().apply {
        setHints(
            mapOf(
                DecodeHintType.POSSIBLE_FORMATS to arrayListOf(
                    BarcodeFormat.QR_CODE,
                    BarcodeFormat.CODE_128,
                    BarcodeFormat.CODE_39
                )
            )
        )
    }
    
    override fun analyze(imageProxy: ImageProxy) {
        // Skip analysis if paused (dialog is showing)
        if (isPaused()) {
            imageProxy.close()
            return
        }
        
        val buffer = imageProxy.planes[0].buffer
        val data = buffer.toByteArray()
        val pixels = IntArray(data.size)
        
        for (i in data.indices) {
            val grey = data[i].toInt() and 0xff
            pixels[i] = 0xff000000.toInt() or (grey * 0x00010101)
        }
        
        val source = RGBLuminanceSource(
            imageProxy.width,
            imageProxy.height,
            pixels
        )
        val bitmap = BinaryBitmap(HybridBinarizer(source))
        
        try {
            val result = reader.decode(bitmap)
            onQRCodeScanned(result.text)
        } catch (e: Exception) {
            // No QR code found in this frame
        } finally {
            imageProxy.close()
        }
    }
    
    private fun ByteBuffer.toByteArray(): ByteArray {
        rewind()
        val data = ByteArray(remaining())
        get(data)
        return data
    }
}
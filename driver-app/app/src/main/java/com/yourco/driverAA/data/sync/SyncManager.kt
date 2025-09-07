package com.yourco.driverAA.data.sync

import android.util.Log
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.OrderStatusUpdateDto
import com.yourco.driverAA.data.api.OrderPatchDto
import com.yourco.driverAA.data.api.UpsellRequest
import com.yourco.driverAA.data.api.UIDScanRequest
import com.yourco.driverAA.data.db.*
import com.yourco.driverAA.data.network.ConnectivityManager
import kotlinx.coroutines.*
import kotlinx.serialization.json.Json
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.pow

@Singleton
class SyncManager @Inject constructor(
    private val api: DriverApi,
    private val jobsDao: JobsDao,
    private val outboxDao: OutboxDao,
    private val photosDao: PhotosDao,
    private val uidScansDao: UIDScansDao,
    private val connectivityManager: ConnectivityManager
) {
    private val TAG = "SyncManager"
    private var syncJob: Job? = null
    
    suspend fun syncAll(statusFilter: String = "active"): Boolean {
        Log.i(TAG, "syncAll() called with statusFilter=$statusFilter - ConnectivityManager.isOnline(): ${connectivityManager.isOnline()}")
        
        // Note: When called from WorkManager, network availability is already guaranteed by NetworkType.CONNECTED constraint
        // When called directly (e.g. manual sync), we still want to check connectivity
        // However, we should trust WorkManager's network constraints over our own connectivity check
        
        return try {
            Log.i(TAG, "Starting full sync with statusFilter=$statusFilter...")
            
            // 1. Download latest jobs from server (pull)
            Log.d(TAG, "Step 1: Syncing jobs from server...")
            syncJobsFromServer(statusFilter)
            
            // 2. Process outbox operations (push)
            Log.d(TAG, "Step 2: Processing outbox operations...")
            processOutboxOperations()
            
            // 3. Upload pending photos
            Log.d(TAG, "Step 3: Uploading pending photos...")
            uploadPendingPhotos()
            
            // 4. Sync UID scans
            Log.d(TAG, "Step 4: Syncing UID scans...")
            syncPendingUIDScans()
            
            Log.i(TAG, "Full sync completed successfully with statusFilter=$statusFilter")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Sync failed", e)
            false
        }
    }
    
    private suspend fun syncJobsFromServer(statusFilter: String = "active") {
        try {
            Log.d(TAG, "Syncing jobs from server with statusFilter=$statusFilter...")
            val serverJobs = api.getJobs(statusFilter)
            
            // Convert to entities and insert/update locally
            val jobEntities = serverJobs.map { JobEntity.fromDto(it).copy(syncStatus = "SYNCED") }
            jobsDao.insertAll(jobEntities)
            
            Log.d(TAG, "Synced ${jobEntities.size} jobs from server with statusFilter=$statusFilter")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to sync jobs from server", e)
            throw e
        }
    }
    
    private suspend fun processOutboxOperations() {
        val pendingOperations = outboxDao.getPendingOperations()
        Log.d(TAG, "Processing ${pendingOperations.size} pending operations")
        
        for (operation in pendingOperations) {
            try {
                executeOperation(operation)
            } catch (e: Exception) {
                handleOperationFailure(operation, e)
            }
        }
    }
    
    private suspend fun executeOperation(operation: OutboxEntity) {
        Log.d(TAG, "Executing operation: ${operation.operation} for entity ${operation.entityId}")
        
        when (operation.operation) {
            "UPDATE_STATUS" -> executeStatusUpdate(operation)
            "UPDATE_STATUS_WITH_UIDS" -> executeStatusUpdateWithUIDs(operation)
            "UPSELL_ORDER" -> executeUpsellOrder(operation)
            "UPLOAD_POD" -> executePhotoUpload(operation)
            "SCAN_UID" -> executeUIDScan(operation)
            "CLOCK_IN" -> executeClockIn(operation)
            "CLOCK_OUT" -> executeClockOut(operation)
            else -> {
                Log.w(TAG, "Unknown operation type: ${operation.operation}")
                outboxDao.markFailed(operation.id, "Unknown operation type")
            }
        }
    }
    
    private suspend fun executeStatusUpdate(operation: OutboxEntity) {
        // Check if this is a patch operation (ON_HOLD, etc.) or status update
        if (operation.endpoint.contains("driver-update")) {
            // Handle PATCH /orders/{id}/driver-update (returns ApiResponse<OrderDto>)
            val update = Json.decodeFromString<OrderPatchDto>(operation.payload)
            val response = api.patchOrder(operation.entityId, update)
            
            // Unwrap ApiResponse and update local job
            val jobEntity = JobEntity.fromDto(
                JobDto(
                    id = response.data.id.toString(),
                    code = response.data.code,
                    status = response.data.status,
                    customer_name = response.data.customer?.name,
                    customer_phone = response.data.customer?.phone,
                    address = response.data.customer?.address,
                    delivery_date = response.data.delivery_date,
                    notes = response.data.notes,
                    total = response.data.total,
                    paid_amount = response.data.paid_amount,
                    balance = response.data.balance,
                    type = response.data.type
                )
            ).copy(syncStatus = "SYNCED")
            jobsDao.update(jobEntity)
        } else {
            // Handle PATCH /drivers/orders/{id} (returns JobDto directly)
            val update = Json.decodeFromString<OrderStatusUpdateDto>(operation.payload)
            val response = api.updateOrderStatus(operation.entityId, update)
            
            // Update local job with server response
            val jobEntity = JobEntity.fromDto(response).copy(syncStatus = "SYNCED")
            jobsDao.update(jobEntity)
        }
        
        // Mark operation as completed
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "Status update completed for job ${operation.entityId}")
    }
    
    private suspend fun executeStatusUpdateWithUIDs(operation: OutboxEntity) {
        Log.d(TAG, "Executing integrated status update with UIDs for job ${operation.entityId}")
        
        // Decode the integrated payload
        val update = Json.decodeFromString<OrderStatusUpdateDto>(operation.payload)
        
        // Call the existing drivers API endpoint with UID actions
        val response = api.updateOrderStatus(operation.entityId, update)
        
        Log.d(TAG, "Server response for integrated update: $response")
        
        // Update local job with server response
        val jobEntity = JobEntity.fromDto(response).copy(syncStatus = "SYNCED")
        jobsDao.update(jobEntity)
        
        // Update UID scans status if they were successful
        update.uid_actions?.forEach { uidAction ->
            // Find the scan record and mark as synced
            val scans = uidScansDao.getScansBySyncStatus("PENDING")
            val matchingScan = scans.find { it.uid == uidAction.uid && it.orderId == operation.entityId.toInt() }
            matchingScan?.let {
                uidScansDao.updateSyncStatus(it.id, "SYNCED", System.currentTimeMillis())
                Log.d(TAG, "Marked UID ${uidAction.uid} as synced for order ${operation.entityId}")
            }
        }
        
        // Mark operation as completed
        outboxDao.markCompleted(operation.id)
        
        // Log UID processing results if available
        response.uid_processing?.let { result ->
            Log.d(TAG, "UID processing results: ${result.success_count}/${result.total_requested} successful")
            if (result.errors.isNotEmpty()) {
                Log.w(TAG, "UID processing errors: ${result.errors}")
            }
        }
        
        Log.d(TAG, "Integrated status update completed for job ${operation.entityId}")
    }
    
    private suspend fun executeUpsellOrder(operation: OutboxEntity) {
        val upsellRequest = Json.decodeFromString<UpsellRequest>(operation.payload)
        val response = api.upsellOrder(operation.entityId, upsellRequest)
        
        // Unwrap ApiResponse and handle the upsell response
        if (response.data.success && response.data.order != null) {
            // Update local job with the updated order data
            val jobEntity = JobEntity.fromDto(
                JobDto(
                    id = response.data.order.id.toString(),
                    code = response.data.order.code,
                    status = response.data.order.status,
                    customer_name = response.data.order.customer?.name,
                    customer_phone = response.data.order.customer?.phone,
                    address = response.data.order.customer?.address,
                    delivery_date = response.data.order.delivery_date,
                    notes = response.data.order.notes,
                    total = response.data.order.total,
                    paid_amount = response.data.order.paid_amount,
                    balance = response.data.order.balance,
                    type = response.data.order.type
                )
            ).copy(syncStatus = "SYNCED")
            jobsDao.update(jobEntity)
        }
        
        // Mark operation as completed
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "Upsell order completed for job ${operation.entityId}: ${response.data.message}")
    }
    
    private suspend fun executePhotoUpload(operation: OutboxEntity) {
        val payload = Json.decodeFromString<Map<String, Any>>(operation.payload)
        val photoId = payload["photoId"] as String
        val photoNumber = (payload["photoNumber"] as Double).toInt()
        
        val photo = photosDao.getPhotosByUploadStatus("PENDING").find { it.id == photoId }
            ?: throw Exception("Photo not found: $photoId")
        
        val photoFile = File(photo.localPath)
        if (!photoFile.exists()) {
            throw Exception("Photo file not found: ${photo.localPath}")
        }
        
        // Update photo status to uploading
        photosDao.updateUploadStatus(photo.id, "UPLOADING", null, null)
        
        val requestBody = photoFile.readBytes().toRequestBody("image/jpeg".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", photoFile.name, requestBody)
        val response = api.uploadPodPhoto(operation.entityId, part, photoNumber)
        
        // Update photo with success
        photosDao.updateUploadStatus(
            photo.id, 
            "UPLOADED", 
            System.currentTimeMillis(), 
            response.url
        )
        
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "Photo upload completed for order ${operation.entityId}")
    }
    
    private suspend fun executeUIDScan(operation: OutboxEntity) {
        val scanRequest = Json.decodeFromString<UIDScanRequest>(operation.payload)
        val response = api.scanUID(scanRequest)
        
        // Update local scan status
        val scans = uidScansDao.getPendingScans()
        val matchingScan = scans.find { 
            it.orderId == scanRequest.order_id && 
            it.uid == scanRequest.uid && 
            it.action == scanRequest.action 
        }
        
        matchingScan?.let {
            uidScansDao.updateSyncStatus(it.id, "SYNCED", System.currentTimeMillis())
        }
        
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "UID scan completed for order ${scanRequest.order_id}")
    }
    
    private suspend fun executeClockIn(operation: OutboxEntity) {
        // Clock in/out operations would be handled here
        // Implementation depends on your clock system
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "Clock in completed")
    }
    
    private suspend fun executeClockOut(operation: OutboxEntity) {
        // Clock out operations would be handled here
        outboxDao.markCompleted(operation.id)
        Log.d(TAG, "Clock out completed")
    }
    
    private suspend fun uploadPendingPhotos() {
        val pendingPhotos = photosDao.getPendingPhotos()
        Log.d(TAG, "Uploading ${pendingPhotos.size} pending photos")
        
        for (photo in pendingPhotos) {
            try {
                val photoFile = File(photo.localPath)
                if (!photoFile.exists()) {
                    photosDao.markUploadFailed(photo.id, "File not found")
                    continue
                }
                
                photosDao.updateUploadStatus(photo.id, "UPLOADING", null, null)
                
                val requestBody = photoFile.readBytes().toRequestBody("image/jpeg".toMediaTypeOrNull())
                val part = MultipartBody.Part.createFormData("file", photoFile.name, requestBody)
                val response = api.uploadPodPhoto(photo.orderId, part, photo.photoNumber)
                
                photosDao.updateUploadStatus(
                    photo.id, 
                    "UPLOADED", 
                    System.currentTimeMillis(), 
                    response.url
                )
                
            } catch (e: Exception) {
                photosDao.markUploadFailed(photo.id, e.message ?: "Upload failed")
                Log.e(TAG, "Failed to upload photo ${photo.id}", e)
            }
        }
    }
    
    private suspend fun syncPendingUIDScans() {
        val pendingScans = uidScansDao.getPendingScans()
        Log.d(TAG, "Syncing ${pendingScans.size} pending UID scans")
        
        for (scan in pendingScans) {
            try {
                val request = UIDScanRequest(
                    order_id = scan.orderId,
                    action = scan.action,
                    uid = scan.uid,
                    sku_id = scan.skuId,
                    notes = scan.notes
                )
                
                val response = api.scanUID(request)
                uidScansDao.updateSyncStatus(scan.id, "SYNCED", System.currentTimeMillis())
                
            } catch (e: Exception) {
                uidScansDao.markSyncFailed(scan.id, e.message ?: "Sync failed")
                Log.e(TAG, "Failed to sync UID scan ${scan.id}", e)
            }
        }
    }
    
    private suspend fun handleOperationFailure(operation: OutboxEntity, error: Exception) {
        val newRetryCount = operation.retryCount + 1
        val nextRetryAt = calculateNextRetry(newRetryCount)
        
        if (newRetryCount >= operation.maxRetries) {
            outboxDao.markFailed(operation.id, error.message ?: "Max retries exceeded")
            Log.e(TAG, "Operation ${operation.id} failed permanently after ${operation.maxRetries} retries")
        } else {
            outboxDao.incrementRetry(
                operation.id, 
                System.currentTimeMillis(), 
                nextRetryAt, 
                error.message
            )
            Log.w(TAG, "Operation ${operation.id} failed, retry ${newRetryCount}/${operation.maxRetries} scheduled for ${nextRetryAt}")
        }
    }
    
    private fun calculateNextRetry(retryCount: Int): Long {
        // Exponential backoff: 1min, 2min, 4min, 8min, 16min
        val delayMinutes = (2.0.pow((retryCount - 1).toDouble())).toLong().coerceAtMost(16)
        return System.currentTimeMillis() + (delayMinutes * 60 * 1000)
    }
    
    fun startPeriodicSync() {
        syncJob?.cancel()
        syncJob = CoroutineScope(Dispatchers.IO).launch {
            while (isActive) {
                try {
                    if (connectivityManager.isOnline()) {
                        syncAll()
                    }
                    delay(5 * 60 * 1000) // Sync every 5 minutes
                } catch (e: Exception) {
                    Log.e(TAG, "Periodic sync error", e)
                    delay(2 * 60 * 1000) // Wait 2 minutes before retry on error
                }
            }
        }
    }
    
    fun stopPeriodicSync() {
        syncJob?.cancel()
        syncJob = null
    }
    
    suspend fun cleanupOldData() {
        try {
            val sevenDaysAgo = System.currentTimeMillis() - (7 * 24 * 60 * 60 * 1000)
            
            // Clean up old completed operations
            outboxDao.deleteCompletedOlderThan(sevenDaysAgo)
            
            // Clean up old failed operations (after 7 days)
            outboxDao.deleteFailedOlderThan(sevenDaysAgo)
            
            // Clean up old uploaded photos
            photosDao.deleteUploadedOlderThan(sevenDaysAgo)
            
            // Clean up old synced UID scans
            uidScansDao.deleteSyncedOlderThan(sevenDaysAgo)
            
            Log.d(TAG, "Cleaned up old sync data")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to cleanup old data", e)
        }
    }
}
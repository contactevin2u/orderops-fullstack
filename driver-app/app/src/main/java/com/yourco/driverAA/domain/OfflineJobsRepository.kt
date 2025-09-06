package com.yourco.driverAA.domain

import android.util.Log
import com.yourco.driverAA.data.api.*
import com.yourco.driverAA.data.db.*
import com.yourco.driverAA.data.network.ConnectivityManager
import com.yourco.driverAA.data.sync.SyncManager
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.*
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class OfflineJobsRepository @Inject constructor(
    private val api: DriverApi,
    private val jobsDao: JobsDao,
    private val outboxDao: OutboxDao,
    private val photosDao: PhotosDao,
    private val uidScansDao: UIDScansDao,
    private val syncManager: SyncManager,
    private val connectivityManager: ConnectivityManager
) {
    private val TAG = "OfflineJobsRepository"
    
    /**
     * Get jobs - always return local data first, sync in background
     */
    fun getJobs(statusFilter: String = "active"): Flow<Result<List<JobDto>>> {
        return if (statusFilter == "active") {
            jobsDao.getActiveJobs()
        } else {
            jobsDao.getJobsByStatus(statusFilter)
        }.map { entities -> 
            Result.Success(entities.map { it.toDto() }) as Result<List<JobDto>>
        }.onStart {
            // Trigger background sync if online
            if (connectivityManager.isOnline()) {
                try {
                    syncManager.syncAll()
                } catch (e: Exception) {
                    Log.e(TAG, "Background sync failed", e)
                }
            }
        }.catch { e ->
            emit(Result.error<List<JobDto>>(e as? Exception ?: Exception(e.message ?: "Unknown error"), "load_jobs"))
        }
    }
    
    /**
     * Get single job - return local data first
     */
    suspend fun getJob(id: String): Result<JobDto> {
        return try {
            val localJob = jobsDao.getJobById(id)
            if (localJob != null) {
                // Return local data immediately
                Result.Success(localJob.toDto())
            } else if (connectivityManager.isOnline()) {
                // Try to fetch from server if online
                try {
                    val serverJob = api.getJob(id)
                    val jobEntity = JobEntity.fromDto(serverJob)
                    jobsDao.insert(jobEntity)
                    Result.Success(serverJob)
                } catch (e: Exception) {
                    Result.error(e, "load_jobs")
                }
            } else {
                Result.error(Exception("Job not found locally and device is offline"), "load_jobs")
            }
        } catch (e: Exception) {
            Result.error(e, "load_jobs")
        }
    }
    
    /**
     * Update order status - offline-first approach
     */
    suspend fun updateOrderStatus(orderId: String, status: String): Result<JobDto> {
        return try {
            // Update local database immediately
            jobsDao.updateJobStatus(orderId, status, "PENDING")
            
            // Queue for background sync
            val operation = OutboxEntity(
                operation = "UPDATE_STATUS",
                entityId = orderId,
                payload = Json.encodeToString(OrderStatusUpdateDto(status)),
                endpoint = "drivers/orders/$orderId",
                httpMethod = "PATCH",
                priority = 1 // High priority for status updates
            )
            outboxDao.insert(operation)
            
            // Try immediate sync if online
            if (connectivityManager.isOnline()) {
                try {
                    syncManager.syncAll()
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate sync failed, will retry later", e)
                }
            }
            
            // Return updated local data
            val updatedJob = jobsDao.getJobById(orderId)?.toDto()
                ?: throw Exception("Job not found after update")
            
            Result.Success(updatedJob)
        } catch (e: Exception) {
            Result.error(e, "update_status")
        }
    }
    
    /**
     * Upload POD photo with offline support
     */
    suspend fun uploadPodPhoto(orderId: String, photoFile: File, photoNumber: Int): Result<PodUploadResponse> {
        return try {
            // Store photo locally immediately
            val photoEntity = PhotoEntity(
                orderId = orderId,
                localPath = photoFile.absolutePath,
                photoNumber = photoNumber,
                fileSize = photoFile.length(),
                mimeType = "image/jpeg"
            )
            photosDao.insert(photoEntity)
            
            // Queue for upload when online
            val operation = OutboxEntity(
                operation = "UPLOAD_POD",
                entityId = orderId,
                payload = Json.encodeToString(mapOf(
                    "photoId" to photoEntity.id,
                    "photoNumber" to photoNumber
                )),
                endpoint = "drivers/orders/$orderId/pod-photo",
                httpMethod = "POST",
                priority = 2 // Medium priority for photos
            )
            outboxDao.insert(operation)
            
            // Try immediate upload if online
            if (connectivityManager.isOnline()) {
                try {
                    syncManager.syncAll()
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate photo upload failed, will retry later", e)
                }
            }
            
            // Return success with local reference
            Result.Success(PodUploadResponse(
                url = "local://${photoEntity.id}", // Temporary local URL
                photo_number = photoNumber
            ))
        } catch (e: Exception) {
            Result.error(e, "upload_photo")
        }
    }
    
    /**
     * Handle on-hold response offline
     */
    suspend fun handleOnHoldResponse(orderId: String, deliveryDate: String? = null): Result<JobDto> {
        return try {
            Log.i(TAG, "Putting order $orderId on hold with delivery_date: $deliveryDate")
            
            // Update local database immediately
            val currentJob = jobsDao.getJobById(orderId)
            if (currentJob != null) {
                val updatedJob = currentJob.copy(
                    status = "ON_HOLD",
                    deliveryDate = deliveryDate,
                    syncStatus = "PENDING",
                    lastModified = System.currentTimeMillis()
                )
                jobsDao.update(updatedJob)
            }
            
            // Queue for sync
            val operation = OutboxEntity(
                operation = "UPDATE_STATUS",
                entityId = orderId,
                payload = Json.encodeToString(OrderPatchDto(status = "ON_HOLD", delivery_date = deliveryDate)),
                endpoint = "orders/$orderId/driver-update",
                httpMethod = "PATCH",
                priority = 1
            )
            outboxDao.insert(operation)
            
            // Try immediate sync
            if (connectivityManager.isOnline()) {
                try {
                    syncManager.syncAll()
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate sync failed for on-hold", e)
                }
            }
            
            val updatedJob = jobsDao.getJobById(orderId)?.toDto()
                ?: throw Exception("Job not found after on-hold update")
            
            Result.Success(updatedJob)
        } catch (e: Exception) {
            Result.error(e, "update_status")
        }
    }
    
    /**
     * Upsell order offline
     */
    suspend fun upsellOrder(orderId: String, request: UpsellRequest): Result<UpsellResponse> {
        return try {
            // Queue the upsell request
            val operation = OutboxEntity(
                operation = "UPSELL_ORDER",
                entityId = orderId,
                payload = Json.encodeToString(request),
                endpoint = "orders/$orderId/upsell",
                httpMethod = "POST",
                priority = 1
            )
            outboxDao.insert(operation)
            
            // Try immediate sync
            if (connectivityManager.isOnline()) {
                try {
                    val response = api.upsellOrder(orderId, request)
                    outboxDao.markCompleted(operation.id)
                    
                    // Update local job if we have it
                    response.data.order?.let { updatedOrder ->
                        val jobEntity = JobEntity.fromDto(JobDto(
                            id = updatedOrder.id.toString(),
                            code = updatedOrder.code,
                            status = updatedOrder.status,
                            customer_name = updatedOrder.customer?.name,
                            customer_phone = updatedOrder.customer?.phone,
                            address = updatedOrder.customer?.address,
                            total = updatedOrder.total,
                            paid_amount = updatedOrder.paid_amount,
                            balance = updatedOrder.balance,
                            type = updatedOrder.type,
                            items = updatedOrder.items.map { 
                                JobItemDto(
                                    id = it.id.toString(),
                                    name = it.name,
                                    qty = it.qty,
                                    unit_price = it.unit_price
                                )
                            }
                        ))
                        jobsDao.insert(jobEntity)
                    }
                    
                    return Result.Success(response.data)
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate upsell failed, will retry later", e)
                }
            }
            
            // Return optimistic response for offline
            Result.Success(UpsellResponse(
                success = true,
                order_id = orderId.toInt(),
                message = "Upsell queued for processing when online",
                new_total = "0.00" // Will be updated after sync
            ))
        } catch (e: Exception) {
            Result.error(e, "submit_report")
        }
    }
    
    /**
     * Scan UID offline
     */
    suspend fun scanUID(request: UIDScanRequest): Result<UIDScanResponse> {
        return try {
            // Store scan locally
            val scanEntity = UIDScanEntity(
                orderId = request.order_id,
                action = request.action,
                uid = request.uid,
                skuId = request.sku_id,
                notes = request.notes
            )
            uidScansDao.insert(scanEntity)
            
            // Queue for sync
            val operation = OutboxEntity(
                operation = "SCAN_UID",
                entityId = request.order_id.toString(),
                payload = Json.encodeToString(request),
                endpoint = "inventory/uid/scan",
                httpMethod = "POST",
                priority = 2
            )
            outboxDao.insert(operation)
            
            // Try immediate sync
            if (connectivityManager.isOnline()) {
                try {
                    val response = api.scanUID(request)
                    outboxDao.markCompleted(operation.id)
                    uidScansDao.updateSyncStatus(scanEntity.id, "SYNCED", System.currentTimeMillis())
                    return Result.Success(response)
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate UID scan failed, will retry later", e)
                }
            }
            
            // Return optimistic response
            Result.Success(UIDScanResponse(
                success = true,
                message = "UID scan recorded locally, will sync when online",
                uid = request.uid,
                action = request.action
            ))
        } catch (e: Exception) {
            Result.error(e, "uid_scan")
        }
    }
    
    /**
     * Get commissions - try online first, fallback to cached data
     */
    suspend fun getCommissions(): List<CommissionMonthDto> {
        return try {
            if (connectivityManager.isOnline()) {
                api.getCommissions()
            } else {
                // Return empty list or cached data if available
                emptyList()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get commissions", e)
            emptyList()
        }
    }
    
    /**
     * Get driver orders with local caching
     */
    suspend fun getDriverOrders(month: String? = null): List<JobDto> {
        return try {
            if (connectivityManager.isOnline()) {
                val serverOrders = api.getDriverOrders(month)
                // Cache the orders locally
                val entities = serverOrders.map { JobEntity.fromDto(it) }
                jobsDao.insertAll(entities)
                serverOrders
            } else {
                // Return local data
                jobsDao.getAllJobs().first().map { it.toDto() }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to get driver orders", e)
            // Fallback to local data
            jobsDao.getAllJobs().first().map { it.toDto() }
        }
    }
    
    /**
     * Get offline status info
     */
    fun getOfflineStatus(): Flow<OfflineStatus> {
        return combine(
            connectivityManager.isOnlineFlow(),
            outboxDao.getPendingCount(),
            outboxDao.getFailedCount(),
            photosDao.getPendingPhotosCount(),
            uidScansDao.getPendingScansCount()
        ) { isOnline, pendingOps, failedOps, pendingPhotos, pendingScans ->
            OfflineStatus(
                isOnline = isOnline,
                pendingOperations = pendingOps,
                failedOperations = failedOps,
                pendingPhotos = pendingPhotos,
                pendingScans = pendingScans
            )
        }
    }
}

data class OfflineStatus(
    val isOnline: Boolean,
    val pendingOperations: Int,
    val failedOperations: Int,
    val pendingPhotos: Int,
    val pendingScans: Int
) {
    val hasPendingWork: Boolean
        get() = pendingOperations > 0 || pendingPhotos > 0 || pendingScans > 0
}
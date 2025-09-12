package com.yourco.driverAA.domain

import android.util.Log
import com.yourco.driverAA.data.api.*
import com.yourco.driverAA.data.db.*
import com.yourco.driverAA.data.network.ConnectivityManager
import com.yourco.driverAA.data.repository.UserRepository
import com.yourco.driverAA.data.sync.SyncManager
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.*
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class JobsRepository @Inject constructor(
    private val api: DriverApi,
    private val jobsDao: JobsDao,
    private val outboxDao: OutboxDao,
    private val photosDao: PhotosDao,
    private val uidScansDao: UIDScansDao,
    private val syncManager: SyncManager,
    private val connectivityManager: ConnectivityManager,
    private val userRepository: UserRepository
) {
    private val TAG = "JobsRepository"
    fun getJobs(statusFilter: String = "active"): Flow<Result<List<JobDto>>> {
        return flow {
            // First emit loading state
            emit(Result.Loading)
            
            // If online, sync first then emit data
            if (connectivityManager.isOnline()) {
                try {
                    Log.d(TAG, "Online - syncing jobs from server with statusFilter=$statusFilter before returning data")
                    syncManager.syncAll(statusFilter)
                    Log.d(TAG, "Sync completed, now emitting local data")
                } catch (e: Exception) {
                    Log.e(TAG, "Sync failed, will return local data", e)
                }
            }
            
            // Now emit the local data (fresh from sync if online)
            val localJobs = when (statusFilter) {
                "active" -> jobsDao.getActiveJobs().first()
                "completed" -> jobsDao.getCompletedJobs().first()
                else -> jobsDao.getJobsByStatus(statusFilter).first()
            }
            
            Log.d(TAG, "Emitting ${localJobs.size} jobs for statusFilter=$statusFilter")
            emit(Result.Success(localJobs.map { it.toDto() }))
            
            // Continue observing local database changes
            when (statusFilter) {
                "active" -> jobsDao.getActiveJobs()
                "completed" -> jobsDao.getCompletedJobs()
                else -> jobsDao.getJobsByStatus(statusFilter)
            }.collect { entities ->
                emit(Result.Success(entities.map { it.toDto() }))
            }
        }.catch { e ->
            emit(Result.error<List<JobDto>>(e as? Exception ?: Exception(e.message ?: "Unknown error"), "load_jobs"))
        }
    }
    
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
     * Update order status with integrated UID actions - new workflow
     */
    suspend fun updateOrderStatusWithUIDActions(
        orderId: String, 
        status: String, 
        uidActions: List<UIDActionDto>
    ): Result<JobDto> {
        return try {
            Log.d(TAG, "Updating order $orderId to $status with ${uidActions.size} UID actions")
            
            // Update local database immediately
            jobsDao.updateJobStatus(orderId, status, "PENDING")
            
            // Store UID actions locally (for offline support)
            uidActions.forEach { uidAction ->
                val uidScan = UIDScanEntity(
                    orderId = orderId.toInt(),
                    uid = uidAction.uid,
                    action = uidAction.action,
                    skuId = uidAction.sku_id,
                    syncStatus = "PENDING",
                    notes = uidAction.notes
                )
                uidScansDao.insert(uidScan)
            }
            
            // Queue integrated operation for background sync
            val operation = OutboxEntity(
                operation = "UPDATE_STATUS_WITH_UIDS",
                entityId = orderId,
                payload = Json.encodeToString(OrderStatusUpdateDto(status, uidActions)),
                endpoint = "drivers/orders/$orderId",
                httpMethod = "PATCH",
                priority = 1 // High priority for status updates
            )
            outboxDao.insert(operation)
            
            Log.d(TAG, "Queued integrated operation for sync")
            
            // Try immediate sync if online
            if (connectivityManager.isOnline()) {
                try {
                    Log.d(TAG, "Online - attempting immediate sync for UID actions")
                    syncManager.syncAll()
                } catch (e: Exception) {
                    Log.w(TAG, "Immediate sync failed, will retry later", e)
                }
            }
            
            // Return updated local data
            val updatedJob = jobsDao.getJobById(orderId)?.toDto()
                ?: throw Exception("Job not found after update")
            
            Log.d(TAG, "Successfully updated order with UID actions")
            Result.Success(updatedJob)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to update order status with UID actions", e)
            Result.error(e, "update_status_with_uids")
        }
    }
    
    suspend fun uploadPodPhoto(orderId: String, photoFile: File, photoNumber: Int = 1): Result<PodUploadResponse> = try {
        val requestBody = photoFile.readBytes().toRequestBody("image/jpeg".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", photoFile.name, requestBody)
        val response = api.uploadPodPhoto(orderId, part, photoNumber)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "upload_photo")
    }
    
    suspend fun getCommissions(): List<CommissionMonthDto> = api.getCommissions()
    
    suspend fun getUpsellIncentives(month: String? = null, status: String? = null): UpsellIncentivesDto = 
        api.getUpsellIncentives(month, status)
    
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
    
    suspend fun upsellOrder(orderId: String, request: UpsellRequest): Result<UpsellResponse> = try {
        val response = api.upsellOrder(orderId, request)
        Result.Success(response.data)
    } catch (e: Exception) {
        Result.error(e, "submit_report")
    }
    
    // UID Inventory methods
    suspend fun getInventoryConfig(): Result<InventoryConfigResponse> = try {
        val config = api.getInventoryConfig()
        Result.Success(config)
    } catch (e: Exception) {
        Result.error(e, "load_config")
    }
    
    suspend fun scanUID(request: UIDScanRequest): Result<UIDScanResponse> = try {
        val response = api.scanUID(request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "uid_scan")
    }
    
    suspend fun getLorryStock(date: String): Result<LorryStockResponse> = try {
        val userInfo = userRepository.getCurrentUserInfo().getOrThrow()
        val response = api.getLorryStock(userInfo.id, date)
        Result.Success(response.data) // Unwrap ApiResponse<LorryStockResponse>
    } catch (e: Exception) {
        Result.error(e, "load_stock")
    }
    
    suspend fun resolveSKU(request: SKUResolveRequest): Result<SKUResolveResponse> = try {
        val response = api.resolveSKU(request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "resolve_sku")
    }
    
    // Lorry Management methods
    suspend fun getMyLorryAssignment(date: String? = null): Result<LorryAssignmentResponse?> = try {
        val response = api.getMyLorryAssignment(date)
        Result.Success(response.data.assignment)
    } catch (e: Exception) {
        Result.error(e, "load_assignment")
    }
    
    
    suspend fun clockIn(request: ClockInRequest): Result<ShiftResponse> = try {
        val response = api.clockIn(request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "clock_in")
    }
    
    suspend fun clockOut(request: ClockOutRequest): Result<ShiftResponse> = try {
        val response = api.clockOut(request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "clock_out")
    }
    
    suspend fun getDriverStatus(): Result<DriverStatusResponse> = try {
        val response = api.getDriverStatus()
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "driver_status")
    }
    
    // New helper functions for date-scoped operations and hold management
    private val ISO = DateTimeFormatter.ISO_LOCAL_DATE
    
    suspend fun getTodayLorryStock(): Result<LorryStockResponse> =
        try {
            val today = LocalDate.now().format(ISO)
            getLorryStock(today) // you already have getLorryStock(date)
        } catch (e: Exception) {
            Result.error(e, "load_stock")
        }
    
    suspend fun getDriverHolds(): Result<DriverStatusResponse> =
        try {
            val status = api.getDriverStatus()
            Result.Success(status)
        } catch (e: Exception) {
            Result.error(e, "driver_status")
        }
    
    suspend fun getStockStatusFor(date: String): Result<StockStatusResponse> =
        try {
            val me = userRepository.getCurrentUserInfo().getOrThrow()
            val resp = api.getStockStatus(me.id, date)
            Result.Success(resp.data ?: StockStatusResponse(driver_id = me.id))
        } catch (e: Exception) {
            Result.error(e, "stock_status")
        }

    suspend fun uploadStockCount(asOfDate: String, skuCounts: Map<Int, Int>): Result<Unit> =
        try {
            val me = userRepository.getCurrentUserInfo().getOrThrow()
            val lines = skuCounts.map { (skuId, count) ->
                StockCountLine(sku_id = skuId, counted = count)
            }
            val request = StockCountUpload(as_of_date = asOfDate, lines = lines)
            api.uploadStockCount(me.id, request)
            Result.Success(Unit)
        } catch (e: Exception) {
            Result.error(e, "upload_stock")
        }
}

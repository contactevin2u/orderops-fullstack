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
        val stock = api.getLorryStock(userInfo.id, date)
        Result.Success(stock)
    } catch (e: Exception) {
        Result.error(e, "load_stock")
    }
    
    suspend fun resolveSKU(request: SKUResolveRequest): Result<SKUResolveResponse> = try {
        val response = api.resolveSKU(request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "resolve_sku")
    }
}

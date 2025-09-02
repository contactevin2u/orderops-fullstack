package com.yourco.driverAA.domain

import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.OrderStatusUpdateDto
import com.yourco.driverAA.data.api.PodUploadResponse
import com.yourco.driverAA.data.api.CommissionMonthDto
import com.yourco.driverAA.data.api.OrderPatchDto
import com.yourco.driverAA.data.api.OrderDto
import com.yourco.driverAA.data.api.UpsellRequest
import com.yourco.driverAA.data.api.UpsellResponse
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class JobsRepository @Inject constructor(
    private val api: DriverApi
) {
    fun getJobs(statusFilter: String = "active"): Flow<Result<List<JobDto>>> = flow {
        emit(Result.Loading)
        try {
            val jobs = api.getJobs(statusFilter)
            emit(Result.Success(jobs))
        } catch (e: Exception) {
            emit(Result.error<List<JobDto>>(e, "load_jobs"))
        }
    }
    
    suspend fun getJob(id: String): Result<JobDto> = try {
        val job = api.getJob(id)
        Result.Success(job)
    } catch (e: Exception) {
        Result.error(e, "load_jobs")
    }
    
    suspend fun updateOrderStatus(orderId: String, status: String): Result<JobDto> = try {
        val updatedJob = api.updateOrderStatus(orderId, OrderStatusUpdateDto(status))
        Result.Success(updatedJob)
    } catch (e: Exception) {
        Result.error(e, "update_status")
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
    
    suspend fun handleOnHoldResponse(orderId: String, deliveryDate: String? = null): Result<JobDto> = try {
        // Update the order via PATCH endpoint
        api.patchOrder(orderId, OrderPatchDto(status = "ON_HOLD", delivery_date = deliveryDate))
        // Return the updated job by refetching it
        val updatedJob = api.getJob(orderId)
        Result.Success(updatedJob)
    } catch (e: Exception) {
        Result.error(e, "update_status")
    }
    
    suspend fun upsellOrder(orderId: String, request: UpsellRequest): Result<UpsellResponse> = try {
        val response = api.upsellOrder(orderId, request)
        Result.Success(response)
    } catch (e: Exception) {
        Result.error(e, "submit_report")
    }
}

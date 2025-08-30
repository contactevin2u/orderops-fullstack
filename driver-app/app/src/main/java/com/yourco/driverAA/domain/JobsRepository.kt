package com.yourco.driverAA.domain

import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.OrderStatusUpdateDto
import com.yourco.driverAA.data.api.PodUploadResponse
import com.yourco.driverAA.data.api.CommissionMonthDto
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
            emit(Result.Error(e))
        }
    }
    
    suspend fun getJob(id: String): Result<JobDto> = try {
        val job = api.getJob(id)
        Result.Success(job)
    } catch (e: Exception) {
        Result.Error(e)
    }
    
    suspend fun updateOrderStatus(orderId: String, status: String): Result<JobDto> = try {
        val updatedJob = api.updateOrderStatus(orderId, OrderStatusUpdateDto(status))
        Result.Success(updatedJob)
    } catch (e: Exception) {
        Result.Error(e)
    }
    
    suspend fun uploadPodPhoto(orderId: String, photoFile: File, photoNumber: Int = 1): Result<PodUploadResponse> = try {
        val requestBody = photoFile.readBytes().toRequestBody("image/jpeg".toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", photoFile.name, requestBody)
        val response = api.uploadPodPhoto(orderId, part, photoNumber)
        Result.Success(response)
    } catch (e: Exception) {
        Result.Error(e)
    }
    
    suspend fun getCommissions(): List<CommissionMonthDto> = api.getCommissions()
}

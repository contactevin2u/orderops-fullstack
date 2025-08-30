package com.yourco.driverAA.domain

import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class JobsRepository @Inject constructor(
    private val api: DriverApi
) {
    fun getJobs(): Flow<Result<List<JobDto>>> = flow {
        emit(Result.Loading)
        try {
            val jobs = api.getJobs()
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
}

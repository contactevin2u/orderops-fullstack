package com.yourco.driverAA.domain

import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class JobsRepository @Inject constructor(
    private val api: DriverApi
) {
    fun getJobs(): Flow<Result<List<String>>> = flow {
        emit(Result.Loading)
        try {
            val jobs = api.getJobs()
            emit(Result.Success(jobs.map { it.id }))
        } catch (e: Exception) {
            emit(Result.Error(e))
        }
    }
    
    suspend fun getJob(id: String): Result<String> = try {
        val job = api.getJob(id)
        Result.Success(job.id)
    } catch (e: Exception) {
        Result.Error(e)
    }
}

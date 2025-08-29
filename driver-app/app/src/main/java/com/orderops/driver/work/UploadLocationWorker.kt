package com.orderops.driver.work

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.orderops.driver.data.api.DriverApi
import com.orderops.driver.data.api.LocationPingDto
import com.orderops.driver.data.db.LocationPingDao
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject

@HiltWorker
class UploadLocationWorker @AssistedInject constructor(
    @Assisted appContext: Context,
    @Assisted params: WorkerParameters,
    private val dao: LocationPingDao,
    private val api: DriverApi
) : CoroutineWorker(appContext, params) {
    override suspend fun doWork(): Result {
        val pings = dao.pending()
        if (pings.isEmpty()) return Result.success()
        return try {
            api.postLocations(pings.map { LocationPingDto(it.lat, it.lng, it.accuracy, it.speed, it.ts) })
            dao.markUploaded(pings.map { it.id })
            Result.success()
        } catch (e: Exception) {
            Result.retry()
        }
    }
}

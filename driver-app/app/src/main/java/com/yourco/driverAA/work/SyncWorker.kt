package com.yourco.driverAA.work

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.*
import com.yourco.driverAA.data.network.ConnectivityManager
import com.yourco.driverAA.data.sync.SyncManager
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import java.util.concurrent.TimeUnit

@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val syncManager: SyncManager,
    private val connectivityManager: ConnectivityManager
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        Log.d(TAG, "Starting background sync...")
        
        return try {
            // WorkManager already handles network connectivity with NetworkType.CONNECTED constraint
            // No need to double-check with connectivityManager.isOnline()
            val syncSuccess = syncManager.syncAll()
            if (syncSuccess) {
                Log.d(TAG, "Background sync completed successfully")
                Result.success()
            } else {
                Log.w(TAG, "Background sync completed with errors")
                Result.retry()
            }
        } catch (e: Exception) {
            Log.e(TAG, "Background sync failed", e)
            if (runAttemptCount < MAX_RETRIES) {
                Result.retry()
            } else {
                Result.failure()
            }
        }
    }

    companion object {
        private const val TAG = "SyncWorker"
        private const val MAX_RETRIES = 3
        const val WORK_NAME = "sync_work"
        
        fun enqueuePeriodicSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .setRequiresBatteryNotLow(true)
                .build()

            val syncRequest = PeriodicWorkRequestBuilder<SyncWorker>(
                15, TimeUnit.MINUTES, // Repeat every 15 minutes
                5, TimeUnit.MINUTES   // Flex interval of 5 minutes
            )
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()

            WorkManager.getInstance(context).enqueueUniquePeriodicWork(
                WORK_NAME,
                ExistingPeriodicWorkPolicy.KEEP,
                syncRequest
            )
            
            Log.d(TAG, "Periodic sync work enqueued")
        }
        
        fun enqueueImmediateSync(context: Context) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()

            val syncRequest = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    WorkRequest.MIN_BACKOFF_MILLIS,
                    TimeUnit.MILLISECONDS
                )
                .build()

            WorkManager.getInstance(context).enqueueUniqueWork(
                "immediate_sync",
                ExistingWorkPolicy.REPLACE,
                syncRequest
            )
            
            Log.d(TAG, "Immediate sync work enqueued")
        }
        
        fun cancelPeriodicSync(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(WORK_NAME)
            Log.d(TAG, "Periodic sync work cancelled")
        }
    }
}
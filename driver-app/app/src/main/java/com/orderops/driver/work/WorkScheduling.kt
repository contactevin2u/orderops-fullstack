package com.orderops.driver.work

import android.content.Context
import androidx.work.*
import java.util.concurrent.TimeUnit

object WorkScheduling {
    fun scheduleUpload(context: Context) {
        val request = PeriodicWorkRequestBuilder<UploadLocationWorker>(15, TimeUnit.MINUTES)
            .setConstraints(
                Constraints.Builder()
                    .setRequiredNetworkType(NetworkType.CONNECTED)
                    .build()
            )
            .addTag("upload-locations")
            .build()
        WorkManager.getInstance(context).enqueueUniquePeriodicWork(
            "upload-locations",
            ExistingPeriodicWorkPolicy.UPDATE,
            request
        )
    }
}


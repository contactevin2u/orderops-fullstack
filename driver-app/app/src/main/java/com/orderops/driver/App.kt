package com.orderops.driver

import android.app.Application
import androidx.work.Configuration
import com.orderops.driver.work.WorkScheduling
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import androidx.hilt.work.HiltWorkerFactory
import timber.log.Timber

@HiltAndroidApp
class App : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        Timber.plant(Timber.DebugTree())
        // Schedule periodic upload job (15m) at app start
        WorkScheduling.scheduleUpload(this)
    }

    override fun getWorkManagerConfiguration(): Configuration =
        Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}


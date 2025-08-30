package com.yourco.driverAA

import android.app.Application
import androidx.work.Configuration
import com.yourco.driverAA.work.WorkScheduling
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import androidx.hilt.work.HiltWorkerFactory
import timber.log.Timber
import com.yourco.driverAA.BuildConfig
import androidx.work.Configuration

@HiltAndroidApp
class App : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        // schedule periodic upload (15m) on app start
        WorkScheduling.scheduleUpload(this)
    }

    override fun getWorkManagerConfiguration(): Configuration =
        Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}

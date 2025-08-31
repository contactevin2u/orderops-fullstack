package com.yourco.driverAA

import android.app.Application
import android.util.Log
import androidx.hilt.work.HiltWorkerFactory
import androidx.work.Configuration
import com.google.firebase.Firebase
import com.google.firebase.appcheck.appCheck
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory
import com.google.firebase.initialize
import com.yourco.driverAA.work.WorkScheduling
import com.yourco.driverAA.notifications.Notifications
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import timber.log.Timber

@HiltAndroidApp
class App : Application(), Configuration.Provider {

    @Inject lateinit var workerFactory: HiltWorkerFactory

    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.DEBUG) {
            Timber.plant(Timber.DebugTree())
        }
        
        // Initialize Firebase App Check with debug provider for development
        try {
            Firebase.initialize(this)
            Firebase.appCheck.installAppCheckProviderFactory(
                DebugAppCheckProviderFactory.getInstance()
            )
            Log.d("App", "Firebase App Check initialized with debug provider")
        } catch (e: Exception) {
            Log.e("App", "Failed to initialize App Check", e)
        }
        
        // Initialize notification channels
        Notifications.createJobsChannel(this)
        // schedule periodic upload (15m) on app start
        WorkScheduling.scheduleUpload(this)
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}

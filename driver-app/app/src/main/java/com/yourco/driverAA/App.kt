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
        
        // === COMPREHENSIVE RUNTIME DEBUG INFO ===
        Log.i("App", "=== APP STARTUP DEBUG INFO ===")
        Log.i("App", "BuildConfig.DEBUG: ${BuildConfig.DEBUG}")
        Log.i("App", "BuildConfig.BUILD_TYPE: ${BuildConfig.BUILD_TYPE}")
        Log.i("App", "BuildConfig.APPLICATION_ID: ${BuildConfig.APPLICATION_ID}")
        Log.i("App", "BuildConfig.VERSION_NAME: ${BuildConfig.VERSION_NAME}")
        Log.i("App", "BuildConfig.VERSION_CODE: ${BuildConfig.VERSION_CODE}")
        Log.i("App", "BuildConfig.API_BASE: '${BuildConfig.API_BASE}'")
        Log.i("App", "Package name: ${packageName}")
        Log.i("App", "Build fingerprint: ${android.os.Build.FINGERPRINT}")
        Log.i("App", "=== END STARTUP DEBUG INFO ===")
        
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
        
        Log.i("App", "App onCreate() completed successfully")
    }

    override val workManagerConfiguration: Configuration
        get() = Configuration.Builder()
            .setWorkerFactory(workerFactory)
            .build()
}

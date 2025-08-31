package com.yourco.driverAA

import android.app.Application
import android.util.Log
import com.google.firebase.Firebase
import com.google.firebase.appcheck.appCheck
import com.google.firebase.appcheck.debug.DebugAppCheckProviderFactory
import com.google.firebase.initialize
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class DriverAAApplication : Application() {
    
    override fun onCreate() {
        super.onCreate()
        
        // Initialize Firebase App Check with debug provider for development
        try {
            Firebase.initialize(this)
            Firebase.appCheck.installAppCheckProviderFactory(
                DebugAppCheckProviderFactory.getInstance()
            )
            Log.d("DriverAAApplication", "Firebase App Check initialized with debug provider")
        } catch (e: Exception) {
            Log.e("DriverAAApplication", "Failed to initialize App Check", e)
        }
    }
}
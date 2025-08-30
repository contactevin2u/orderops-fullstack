package com.yourco.driverAA.location

import android.app.Notification
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.os.IBinder
import androidx.core.content.ContextCompat
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import com.yourco.driverAA.data.db.LocationPing
import com.yourco.driverAA.data.db.LocationPingDao
import com.yourco.driverAA.notifications.Notifications
import com.yourco.driverAA.R
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.*

@AndroidEntryPoint
class LocationForegroundService : Service() {
    @Inject lateinit var dao: LocationPingDao
    private lateinit var client: FusedLocationProviderClient
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        client = LocationServices.getFusedLocationProviderClient(this)
        startForeground(1, notification())

        val hasFine = ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val hasCoarse = ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val hasBackground = if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) {
            ContextCompat.checkSelfPermission(this, android.Manifest.permission.ACCESS_BACKGROUND_LOCATION) == PackageManager.PERMISSION_GRANTED
        } else true

        if ((!hasFine && !hasCoarse) || !hasBackground) {
            stopSelf()
            return
        }

        val request = LocationRequest.Builder(
            LocationRequest.PRIORITY_BALANCED_POWER_ACCURACY, 60000  // 1 minute instead of 15 seconds
        ).setMinUpdateIntervalMillis(30000)  // Minimum 30 seconds
            .setMaxUpdateDelayMillis(120000)  // Maximum 2 minutes
            .build()
        client.requestLocationUpdates(request, callback, mainLooper)
    }

    private val callback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val loc = result.lastLocation ?: return
            scope.launch {
                dao.insert(
                    LocationPing(
                        lat = loc.latitude,
                        lng = loc.longitude,
                        accuracy = loc.accuracy,
                        speed = loc.speed,
                        ts = System.currentTimeMillis()
                    )
                )
            }
        }
    }

    private fun notification(): Notification {
        Notifications.createJobsChannel(this)
        return NotificationCompat.Builder(this, Notifications.JOBS_CHANNEL)
            .setContentTitle("Tracking")
            .setSmallIcon(R.drawable.ic_notification_foreground)
            .build()
    }

    override fun onDestroy() {
        client.removeLocationUpdates(callback)
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}

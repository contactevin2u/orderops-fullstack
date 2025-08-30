package com.yourco.driverAA.fcm

import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.yourco.driverAA.notifications.Notifications
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.data.auth.AuthService
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import javax.inject.Inject

@AndroidEntryPoint
class DriverFirebaseMessagingService : FirebaseMessagingService() {
    
    @Inject
    lateinit var authService: AuthService
    override fun onMessageReceived(message: RemoteMessage) {
        val type = message.data["type"]
        if (type == "job_assigned") {
            val jobId = message.data["jobId"] ?: return
            val notification = Notifications.jobAssignedNotification(this, jobId).build()
            NotificationManagerCompat.from(this).notify(jobId.hashCode(), notification)
        }
    }

    override fun onNewToken(token: String) {
        val client = OkHttpClient()
        val body = """{"token":"$token"}""".toRequestBody("application/json".toMediaType())
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val idToken = authService.getIdToken()
                val requestBuilder = Request.Builder()
                    .url("${BuildConfig.API_BASE.trimEnd('/')}/driver/push-tokens")
                    .post(body)
                
                // Add authorization header if token is available
                if (idToken != null) {
                    requestBuilder.header("Authorization", "Bearer $idToken")
                }
                
                val req = requestBuilder.build()
                client.newCall(req).execute().use { response ->
                    if (!response.isSuccessful) {
                        // Log error but don't crash
                        android.util.Log.w("FCM", "Failed to upload token: ${'$'}{response.code}")
                    }
                }
            } catch (e: Exception) {
                android.util.Log.w("FCM", "Error uploading token", e)
            }
        }
    }
}


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
        android.util.Log.i("FCM", "New FCM token received: ${token.take(20)}...")
        val client = OkHttpClient()
        val body = """{"token":"$token"}""".toRequestBody("application/json".toMediaType())
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val idToken = authService.getIdToken()
                
                if (idToken == null) {
                    android.util.Log.w("FCM", "No ID token available - driver not logged in yet. Skipping token upload.")
                    return@launch
                }
                
                android.util.Log.i("FCM", "Uploading FCM token with authentication...")
                
                val requestBuilder = Request.Builder()
                    .url("${BuildConfig.API_BASE.trimEnd('/')}/driver/push-tokens")
                    .post(body)
                    .header("Authorization", "Bearer $idToken")
                
                val req = requestBuilder.build()
                client.newCall(req).execute().use { response ->
                    when (response.code) {
                        200 -> android.util.Log.i("FCM", "Token uploaded successfully")
                        403 -> android.util.Log.w("FCM", "Authentication failed (403) - driver may need to re-login")
                        401 -> android.util.Log.w("FCM", "Unauthorized (401) - invalid or expired token")
                        else -> android.util.Log.w("FCM", "Failed to upload token: ${response.code} - ${response.message}")
                    }
                }
            } catch (e: Exception) {
                android.util.Log.w("FCM", "Error uploading token: ${e.message}", e)
            }
        }
    }
}


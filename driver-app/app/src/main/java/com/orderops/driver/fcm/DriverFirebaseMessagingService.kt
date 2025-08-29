package com.orderops.driver.fcm

import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.orderops.driver.notifications.Notifications
import com.orderops.driver.BuildConfig
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody

class DriverFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val type = message.data["type"]
        if (type == "job_assigned") {
            val jobId = message.data["jobId"] ?: return
            val notification = Notifications.jobAssignedNotification(this, jobId).build()
            NotificationManagerCompat.from(this).notify(jobId.hashCode(), notification)
        }
    }

    override fun onNewToken(token: String) {
        // Optional: POST token to backend
        val client = OkHttpClient()
        val body = """{"token":"$token"}""".toRequestBody("application/json".toMediaType())
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val req = Request.Builder()
                    .url("${BuildConfig.API_BASE.trimEnd('/')}/driver/push-tokens")
                    .post(body)
                    .build()
                client.newCall(req).execute().use { /* ignore body */ }
            } catch (_: Exception) { }
        }
    }
}


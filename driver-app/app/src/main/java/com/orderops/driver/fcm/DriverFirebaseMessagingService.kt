package com.orderops.driver.fcm

import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.orderops.driver.notifications.Notifications

class DriverFirebaseMessagingService : FirebaseMessagingService() {
    override fun onMessageReceived(message: RemoteMessage) {
        val type = message.data["type"]
        if (type == "job_assigned") {
            val jobId = message.data["jobId"] ?: return
            val notification = Notifications.jobAssignedNotification(this, jobId).build()
            NotificationManagerCompat.from(this).notify(jobId.hashCode(), notification)
        }
    }
}

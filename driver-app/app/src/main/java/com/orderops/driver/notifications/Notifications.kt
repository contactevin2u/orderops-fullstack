package com.orderops.driver.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.navigation.NavDeepLinkBuilder
import com.orderops.driver.R
import com.orderops.driver.util.DeepLinks

object Notifications {
    const val JOBS_CHANNEL = "jobs"

    fun createJobsChannel(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                JOBS_CHANNEL,
                context.getString(R.string.jobs_channel_name),
                NotificationManager.IMPORTANCE_HIGH
            )
            val manager = context.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    fun jobAssignedNotification(context: Context, jobId: String): androidx.core.app.NotificationCompat.Builder {
        createJobsChannel(context)
        val pendingIntent = NavDeepLinkBuilder(context)
            .setComponentName(com.orderops.driver.MainActivity::class.java)
            .setGraph(R.navigation.nav_graph)
            .setDestination(R.id.jobDetail)
            .setArguments(android.os.Bundle().apply { putString("jobId", jobId) })
            .createPendingIntent()
        return NotificationCompat.Builder(context, JOBS_CHANNEL)
            .setSmallIcon(R.drawable.ic_notification_foreground)
            .setContentTitle("New job assigned")
            .setContentText("Job $jobId")
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
    }
}

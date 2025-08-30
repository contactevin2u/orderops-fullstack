package com.yourco.driverAA.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.core.app.NotificationCompat
import com.yourco.driverAA.R

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

    fun jobAssignedNotification(context: Context, jobId: String): NotificationCompat.Builder {
        createJobsChannel(context)
        val intent = Intent(
            Intent.ACTION_VIEW,
            Uri.parse("driver://job/$jobId")
        ).setPackage(context.packageName)
            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)

        val pi = PendingIntent.getActivity(
            context, jobId.hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(context, JOBS_CHANNEL)
            .setSmallIcon(R.drawable.ic_notification_foreground)
            .setContentTitle("New job assigned")
            .setContentText("Job $jobId")
            .setAutoCancel(true)
            .setContentIntent(pi)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
    }
}

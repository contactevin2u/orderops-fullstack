package com.yourco.driverAA.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessaging
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import java.net.HttpURLConnection
import java.net.URL
import org.json.JSONObject
import android.Manifest
import android.content.pm.PackageManager
import androidx.core.content.ContextCompat
import androidx.appcompat.app.AppCompatActivity

class MyFcmService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        registerToken(applicationContext, token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val type = data["type"] ?: return
        if (type != "ORDER_ASSIGNED") return

        createChannel()
        val orderId = data["order_id"]
        val code = data["code"]
        val pickup = data["pickup_address"]
        val dropoff = data["dropoff_address"]
        val window = data["delivery_window"]
        val text = "Order #$code · $pickup → $dropoff ($window)"

        val intent = Intent(this, OrderDetailActivity::class.java).apply {
            orderId?.let { putExtra("order_id", it) }
        }
        val pending = PendingIntent.getActivity(
            this, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_order)
            .setContentTitle("New Order Assigned")
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(pending)
            .build()
        NotificationManagerCompat.from(this).notify(1001, notification)
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Orders",
                NotificationManager.IMPORTANCE_HIGH
            )
            manager.createNotificationChannel(channel)
        }
    }

    companion object {
        private const val CHANNEL_ID = "orders_high"

        fun registerToken(context: Context, token: String) {
            try {
                val url = URL("https://your-backend.example.com/api/driver/devices")
                val conn = url.openConnection() as HttpURLConnection
                conn.requestMethod = "POST"
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json")
                val payload = JSONObject().apply {
                    put("token", token)
                    put("platform", "android")
                    put("app_version", BuildConfig.VERSION_NAME)
                    put("model", android.os.Build.MODEL)
                }
                conn.outputStream.use { it.write(payload.toString().toByteArray()) }
                conn.responseCode
            } catch (e: Exception) {
                Log.w("MyFcmService", "registerToken failed", e)
            }
        }

        fun refreshToken(context: Context) {
            FirebaseMessaging.getInstance().token.addOnSuccessListener {
                registerToken(context, it)
            }
        }

        fun requestPermission(activity: AppCompatActivity, requestCode: Int = 1001) {
            if (Build.VERSION.SDK_INT >= 33 &&
                ContextCompat.checkSelfPermission(activity, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
            ) {
                activity.requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), requestCode)
            }
        }
    }
}

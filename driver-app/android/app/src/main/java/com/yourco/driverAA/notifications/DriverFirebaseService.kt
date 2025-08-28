package com.yourco.driverAA.notifications

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.yourco.driverAA.core.network.ApiClient
import com.yourco.driverAA.core.network.DeviceRegisterRequest
import com.yourco.driverAA.core.network.DevicesApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import retrofit2.create

class DriverFirebaseService : FirebaseMessagingService() {
  override fun onNewToken(token: String) {
    super.onNewToken(token)
    CoroutineScope(Dispatchers.IO).launch {
      runCatching {
        val api = ApiClient.retrofit.create<DevicesApi>()
        api.registerDevice(DeviceRegisterRequest(token = token))
      }
    }
  }

  override fun onMessageReceived(message: RemoteMessage) {
    // TODO: build actionable notification as per your spec
  }
}

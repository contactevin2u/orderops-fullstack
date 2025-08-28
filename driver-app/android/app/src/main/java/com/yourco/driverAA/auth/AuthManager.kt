package com.yourco.driverAA.auth

import android.content.Context
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.messaging.FirebaseMessaging
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.core.network.ApiClient
import com.yourco.driverAA.core.network.DeviceRegisterRequest
import com.yourco.driverAA.core.network.DevicesApi
import com.yourco.driverAA.core.network.IdTokenProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import retrofit2.create

class AuthManager(private val context: Context) {

  private val auth = FirebaseAuth.getInstance()
  private val devicesApi = ApiClient.retrofit.create<DevicesApi>()

  init {
    IdTokenProvider.set {
      auth.currentUser?.getIdToken(false)?.await()?.token
    }
    auth.addIdTokenListener { _ ->
      tryRegisterDevice()
    }
  }

  suspend fun signIn(email: String, password: String) = withContext(Dispatchers.IO) {
    auth.signInWithEmailAndPassword(email, password).await()
    tryRegisterDevice()
  }

  suspend fun signOut() = withContext(Dispatchers.IO) {
    auth.signOut()
  }

  private suspend fun tryRegisterDevice() = withContext(Dispatchers.IO) {
    val user = auth.currentUser ?: return@withContext
    val idToken = user.getIdToken(false).await()?.token ?: return@withContext
    val fcm = runCatching { FirebaseMessaging.getInstance().token.await() }.getOrNull() ?: "unknown"
    runCatching {
      devicesApi.registerDevice(
        DeviceRegisterRequest(
          token = fcm,
          app_version = BuildConfig.VERSION_NAME,
          model = android.os.Build.MODEL
        )
      )
    }
  }
}

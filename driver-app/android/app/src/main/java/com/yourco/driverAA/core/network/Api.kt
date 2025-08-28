package com.yourco.driverAA.core.network

import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.Headers
import retrofit2.http.POST
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.core.util.ensureTrailingSlash

object ApiClient {
  private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

  private val authHeaderInterceptor = Interceptor { chain ->
    val req = chain.request()
    val token = IdTokenProvider.currentIdToken()
    val newReq = if (token != null) {
      req.newBuilder().addHeader("Authorization", "Bearer $token").build()
    } else req
    chain.proceed(newReq)
  }

  private val logging = HttpLoggingInterceptor().apply {
    level = HttpLoggingInterceptor.Level.BASIC
  }

  private val ok = OkHttpClient.Builder()
    .addInterceptor(authHeaderInterceptor)
    .addInterceptor(logging)
    .build()

  val retrofit: Retrofit = Retrofit.Builder()
    .baseUrl(BuildConfig.API_BASE.ensureTrailingSlash())
    .client(ok)
    .addConverterFactory(MoshiConverterFactory.create(moshi))
    .build()
}

object IdTokenProvider {
  @Volatile private var tokenGetter: (suspend () -> String?)? = null
  fun set(getter: suspend () -> String?) { tokenGetter = getter }
  fun currentIdToken(): String? = runBlocking { tokenGetter?.invoke() }
}

interface DevicesApi {
  @Headers("Content-Type: application/json")
  @POST("drivers/devices")
  suspend fun registerDevice(@Body body: DeviceRegisterRequest): StatusOk
}

data class DeviceRegisterRequest(
  val token: String,
  val platform: String = "android",
  val app_version: String? = null,
  val model: String? = null
)

data class StatusOk(val status: String = "ok")

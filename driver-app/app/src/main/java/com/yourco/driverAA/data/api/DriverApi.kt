package com.yourco.driverAA.data.api

import kotlinx.serialization.Serializable
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface DriverApi {
    @GET("drivers/jobs")
    suspend fun getJobs(@Query("status_filter") statusFilter: String = "active"): List<JobDto>

    @GET("drivers/jobs/{id}")
    suspend fun getJob(@Path("id") id: String): JobDto

    @POST("drivers/locations")
    suspend fun postLocations(@Body locations: List<LocationPingDto>)
    
    @PATCH("drivers/orders/{id}")
    suspend fun updateOrderStatus(@Path("id") orderId: String, @Body update: OrderStatusUpdateDto): JobDto
    
    @Multipart
    @POST("drivers/orders/{id}/pod-photo")
    suspend fun uploadPodPhoto(
        @Path("id") orderId: String, 
        @Part file: MultipartBody.Part,
        @Query("photo_number") photoNumber: Int = 1
    ): PodUploadResponse
}

@Serializable
data class JobDto(
    val id: String,
    val code: String? = null,
    val status: String? = null,
    val customer_name: String? = null,
    val customer_phone: String? = null,
    val address: String? = null,
    val delivery_date: String? = null,
    val notes: String? = null,
    val total: String? = null,
    val paid_amount: String? = null,
    val balance: String? = null,
    val type: String? = null, // OUTRIGHT | INSTALLMENT | RENTAL | MIXED
    val items: List<JobItemDto>? = null
)

@Serializable
data class JobItemDto(
    val id: String? = null,
    val name: String? = null,
    val qty: Int? = null,
    val unit_price: String? = null
)

@Serializable
data class LocationPingDto(val lat: Double, val lng: Double, val accuracy: Float, val speed: Float, val ts: Long)

@Serializable
data class OrderStatusUpdateDto(val status: String)

@Serializable
data class PodUploadResponse(val url: String, val photo_number: Int)

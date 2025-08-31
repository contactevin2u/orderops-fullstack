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
    
    @GET("drivers/commissions")
    suspend fun getCommissions(): List<CommissionMonthDto>
    
    @POST("drivers/shifts/clock-in")
    suspend fun clockIn(@Body request: ClockInRequest): ShiftResponse
    
    @POST("drivers/shifts/clock-out")
    suspend fun clockOut(@Body request: ClockOutRequest): ShiftResponse
    
    @GET("drivers/shifts/status")
    suspend fun getShiftStatus(): ShiftStatusResponse
    
    @GET("drivers/shifts/active")
    suspend fun getActiveShift(): ShiftResponse?
    
    @GET("drivers/shifts/history")
    suspend fun getShiftHistory(@Query("limit") limit: Int = 10): List<ShiftResponse>
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
    val items: List<JobItemDto>? = null,
    val commission: CommissionDto? = null
)

@Serializable
data class JobItemDto(
    val id: String? = null,
    val name: String? = null,
    val qty: Int? = null,
    val unit_price: String? = null
)

@Serializable
data class CommissionDto(
    val amount: String,
    val status: String, // "pending" or "actualized"
    val scheme: String,
    val rate: String,
    val role: String? = null // "primary" or "secondary"
)

@Serializable
data class LocationPingDto(val lat: Double, val lng: Double, val accuracy: Float, val speed: Float, val ts: Long)

@Serializable
data class OrderStatusUpdateDto(val status: String)

@Serializable
data class PodUploadResponse(val url: String, val photo_number: Int)

@Serializable
data class CommissionMonthDto(
    val month: String,
    val total: Double
)

@Serializable
data class ClockInRequest(
    val lat: Double,
    val lng: Double,
    val location_name: String? = null
)

@Serializable
data class ClockOutRequest(
    val lat: Double,
    val lng: Double,
    val location_name: String? = null,
    val notes: String? = null
)

@Serializable
data class ShiftResponse(
    val id: Int,
    val driver_id: Int,
    val clock_in_at: Long,
    val clock_in_lat: Double,
    val clock_in_lng: Double,
    val clock_in_location_name: String? = null,
    val clock_out_at: Long? = null,
    val clock_out_lat: Double? = null,
    val clock_out_lng: Double? = null,
    val clock_out_location_name: String? = null,
    val is_outstation: Boolean,
    val outstation_distance_km: Double? = null,
    val outstation_allowance_amount: Double,
    val total_working_hours: Double? = null,
    val status: String,
    val notes: String? = null,
    val created_at: Long
)

@Serializable
data class ShiftStatusResponse(
    val is_clocked_in: Boolean,
    val shift_id: Int? = null,
    val clock_in_at: Long? = null,
    val hours_worked: Float? = null,
    val is_outstation: Boolean? = null,
    val location: String? = null,
    val message: String
)

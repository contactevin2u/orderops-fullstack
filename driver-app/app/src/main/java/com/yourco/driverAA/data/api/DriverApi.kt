package com.yourco.driverAA.data.api

import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface DriverApi {
    @GET("drivers/jobs")
    suspend fun getJobs(): List<JobDto>

    @GET("drivers/jobs/{id}")
    suspend fun getJob(@Path("id") id: String): JobDto

    @POST("drivers/locations")
    suspend fun postLocations(@Body locations: List<LocationPingDto>)
}

@Serializable
data class JobDto(
    val id: String,
    val status: String? = null,
    val customer_name: String? = null,
    val customer_phone: String? = null,
    val address: String? = null,
    val delivery_date: String? = null,
    val notes: String? = null,
    val total: String? = null,
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

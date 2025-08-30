package com.yourco.driverAA.data.api

import kotlinx.serialization.Serializable
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface DriverApi {
    @GET("driver/jobs")
    suspend fun getJobs(): List<JobDto>

    @GET("driver/jobs/{id}")
    suspend fun getJob(@Path("id") id: String): JobDto

    @POST("driver/locations")
    suspend fun postLocations(@Body locations: List<LocationPingDto>)
}

@Serializable
data class JobDto(val id: String)

@Serializable
data class LocationPingDto(val lat: Double, val lng: Double, val accuracy: Float, val speed: Float, val ts: Long)

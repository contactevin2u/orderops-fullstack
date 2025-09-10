package com.yourco.driverAA.data.repository

import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.auth.AuthService
import kotlinx.coroutines.flow.first
import javax.inject.Inject
import javax.inject.Singleton

data class UserInfo(
    val id: Int,
    val username: String,
    val role: String
)

@Singleton
class UserRepository @Inject constructor(
    private val authService: AuthService,
    private val api: DriverApi
) {
    
    suspend fun getCurrentUserInfo(): Result<UserInfo> {
        return try {
            val user = authService.currentUser.first()
            if (user == null) {
                Result.failure(Exception("Not authenticated"))
            } else {
                val response = api.getCurrentUser()
                Result.success(
                    UserInfo(
                        id = response.id,
                        username = response.username,
                        role = response.role
                    )
                )
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Admin functionality removed - driver app is for drivers only
}
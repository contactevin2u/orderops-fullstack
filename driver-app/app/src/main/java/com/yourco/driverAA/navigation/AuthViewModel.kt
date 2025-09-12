package com.yourco.driverAA.navigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.auth.AuthService
import com.yourco.driverAA.data.repository.UserRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    val authService: AuthService,
    val userRepository: UserRepository
) : ViewModel() {
    
    /**
     * Sign out current driver and clear all local data
     * This ensures proper data isolation between drivers
     */
    fun signOut() {
        viewModelScope.launch {
            try {
                authService.signOut()
            } catch (e: Exception) {
                // Log error but don't prevent sign out
                println("⚠️ Error during sign out: ${e.message}")
            }
        }
    }
}
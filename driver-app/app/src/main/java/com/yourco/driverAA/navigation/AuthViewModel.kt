package com.yourco.driverAA.navigation

import androidx.lifecycle.ViewModel
import com.yourco.driverAA.data.auth.AuthService
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject

@HiltViewModel
class AuthViewModel @Inject constructor(
    val authService: AuthService
) : ViewModel()
package com.yourco.driverAA

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.google.firebase.auth.FirebaseAuth
import com.yourco.driverAA.auth.AuthManager
import com.yourco.driverAA.auth.LoginScreen

class MainActivity : ComponentActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    val authManager = AuthManager(this)

    setContent {
      MaterialTheme {
        val userState = remember { mutableStateOf(FirebaseAuth.getInstance().currentUser) }
        LaunchedEffect(Unit) {
          FirebaseAuth.getInstance().addAuthStateListener { userState.value = it.currentUser }
        }
        if (userState.value == null) {
          LoginScreen(auth = authManager) {
            userState.value = FirebaseAuth.getInstance().currentUser
          }
        } else {
          HomeScreen()
        }
      }
    }
  }
}

@Composable fun HomeScreen() { /* TODO: orders list etc. */ }

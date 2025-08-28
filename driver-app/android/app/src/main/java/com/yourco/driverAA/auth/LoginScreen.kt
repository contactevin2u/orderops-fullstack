package com.yourco.driverAA.auth

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(auth: AuthManager, onSuccess: () -> Unit) {
  var email by remember { mutableStateOf("") }
  var password by remember { mutableStateOf("") }
  var error by remember { mutableStateOf<String?>(null) }
  val scope = rememberCoroutineScope()

  Column(Modifier.fillMaxSize().padding(24.dp)) {
    Text("Driver Login", style = MaterialTheme.typography.titleLarge)
    Spacer(Modifier.height(16.dp))
    OutlinedTextField(value = email, onValueChange = { email = it }, label = { Text("Email") }, singleLine = true)
    Spacer(Modifier.height(8.dp))
    OutlinedTextField(value = password, onValueChange = { password = it }, label = { Text("Password") },
      singleLine = true, visualTransformation = PasswordVisualTransformation())
    Spacer(Modifier.height(16.dp))
    Button(onClick = {
      error = null
      scope.launch {
        runCatching { auth.signIn(email.trim(), password) }
          .onSuccess { onSuccess() }
          .onFailure { error = it.message ?: "Sign-in failed" }
      }
    }) { Text("Sign in") }
    if (error != null) {
      Spacer(Modifier.height(12.dp)); Text(error!!, color = MaterialTheme.colorScheme.error)
    }
  }
}

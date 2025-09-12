package com.yourco.driverAA.data.auth

import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.yourco.driverAA.data.repository.DataClearingService
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthService @Inject constructor(
    private val firebaseAuth: FirebaseAuth,
    private val dataClearingService: DataClearingService
) {
    
    val currentUser: Flow<FirebaseUser?> = callbackFlow {
        val listener = FirebaseAuth.AuthStateListener { auth ->
            trySend(auth.currentUser)
        }
        firebaseAuth.addAuthStateListener(listener)
        awaitClose { firebaseAuth.removeAuthStateListener(listener) }
    }
    
    suspend fun signInWithEmailAndPassword(email: String, password: String): Result<FirebaseUser> {
        return try {
            // Clear any existing local data before signing in new driver
            // This prevents data leakage between different drivers
            dataClearingService.clearAllLocalData()
            
            val result = firebaseAuth.signInWithEmailAndPassword(email, password).await()
            result.user?.let { user ->
                Result.success(user)
            } ?: Result.failure(Exception("Sign in failed"))
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getIdToken(): String? {
        return try {
            firebaseAuth.currentUser?.getIdToken(false)?.await()?.token
        } catch (e: Exception) {
            null
        }
    }
    
    suspend fun signOut() {
        try {
            // Clear all local data before signing out
            // This ensures no data persists for the next driver
            dataClearingService.clearAllLocalData()
            firebaseAuth.signOut()
        } catch (e: Exception) {
            // Even if data clearing fails, sign out the user
            firebaseAuth.signOut()
            throw e
        }
    }
    
    fun getCurrentUser(): FirebaseUser? = firebaseAuth.currentUser
}
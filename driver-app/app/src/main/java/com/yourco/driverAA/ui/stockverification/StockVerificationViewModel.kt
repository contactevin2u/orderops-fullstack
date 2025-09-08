package com.yourco.driverAA.ui.stockverification

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.*
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class StockVerificationViewModel @Inject constructor(
    private val jobsRepository: JobsRepository
) : ViewModel() {
    
    private val TAG = "StockVerificationVM"
    
    private val _uiState = MutableStateFlow(StockVerificationUiState())
    val uiState: StateFlow<StockVerificationUiState> = _uiState.asStateFlow()
    
    private val _scannedUIDs = MutableStateFlow<List<String>>(emptyList())
    val scannedUIDs: StateFlow<List<String>> = _scannedUIDs.asStateFlow()
    
    init {
        loadAssignment()
    }
    
    private fun loadAssignment() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            try {
                when (val result = jobsRepository.getMyLorryAssignment()) {
                    is Result.Success -> {
                        val assignment = result.data
                        if (assignment != null) {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                lorryAssignment = assignment,
                                hasAssignment = true,
                                canClockIn = !assignment.stock_verified
                            )
                            Log.d(TAG, "Loaded assignment: ${assignment.lorry_id}")
                        } else {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                hasAssignment = false,
                                error = "No lorry assignment found for today"
                            )
                        }
                    }
                    is Result.Error -> {
                        _uiState.value = _uiState.value.copy(
                            isLoading = false,
                            error = result.throwable.message ?: "Failed to load assignment"
                        )
                        Log.e(TAG, "Failed to load assignment", result.throwable)
                    }
                    is Result.Loading -> {
                        // Keep loading state
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "Unknown error"
                )
                Log.e(TAG, "Exception loading assignment", e)
            }
        }
    }
    
    fun addScannedUID(uid: String) {
        val current = _scannedUIDs.value.toMutableList()
        if (!current.contains(uid)) {
            current.add(uid)
            _scannedUIDs.value = current
            Log.d(TAG, "Added UID: $uid, total: ${current.size}")
        } else {
            Log.w(TAG, "UID already scanned: $uid")
        }
    }
    
    fun removeScannedUID(uid: String) {
        val current = _scannedUIDs.value.toMutableList()
        if (current.remove(uid)) {
            _scannedUIDs.value = current
            Log.d(TAG, "Removed UID: $uid, total: ${current.size}")
        }
    }
    
    fun clearAllScannedUIDs() {
        _scannedUIDs.value = emptyList()
        Log.d(TAG, "Cleared all scanned UIDs")
    }
    
    fun clockInWithStockVerification(lat: Double, lng: Double, locationName: String?) {
        viewModelScope.launch {
            val currentState = _uiState.value
            val assignment = currentState.lorryAssignment
            
            if (assignment == null) {
                _uiState.value = currentState.copy(
                    error = "No assignment available"
                )
                return@launch
            }
            
            // Allow empty scanned UIDs for empty lorries - backend will handle validation
            
            _uiState.value = currentState.copy(
                isProcessing = true,
                error = null
            )
            
            Log.d(TAG, "Starting clock-in with ${_scannedUIDs.value.size} scanned UIDs")
            
            try {
                val request = ClockInRequest(
                    lat = lat,
                    lng = lng,
                    location_name = locationName,
                    scanned_uids = _scannedUIDs.value
                )
                
                when (val result = jobsRepository.clockIn(request)) {
                    is Result.Success -> {
                        val response = result.data
                        _uiState.value = currentState.copy(
                            isProcessing = false,
                            clockInComplete = true,
                            clockInResponse = response,
                            canAccessOrders = true
                        )
                        
                        Log.d(TAG, "Clock-in successful: ${response.message}")
                        
                        // Clear scanned UIDs after successful clock-in
                        _scannedUIDs.value = emptyList()
                    }
                    is Result.Error -> {
                        _uiState.value = currentState.copy(
                            isProcessing = false,
                            error = result.throwable.message ?: "Clock-in failed"
                        )
                        Log.e(TAG, "Clock-in failed", result.throwable)
                    }
                    is Result.Loading -> {
                        // Keep processing state
                    }
                }
            } catch (e: Exception) {
                _uiState.value = currentState.copy(
                    isProcessing = false,
                    error = e.message ?: "Clock-in error"
                )
                Log.e(TAG, "Exception during clock-in", e)
            }
        }
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
    
    fun retry() {
        loadAssignment()
    }
}

data class StockVerificationUiState(
    val isLoading: Boolean = false,
    val isProcessing: Boolean = false,
    val hasAssignment: Boolean = false,
    val lorryAssignment: LorryAssignmentResponse? = null,
    val canClockIn: Boolean = false,
    val clockInComplete: Boolean = false,
    val clockInResponse: ClockInResponse? = null,
    val canAccessOrders: Boolean = false,
    val error: String? = null
)
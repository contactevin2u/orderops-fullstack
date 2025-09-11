package com.yourco.driverAA.ui.jobs

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.DriverStatusResponse
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class JobsListViewModel @Inject constructor(
    private val repo: JobsRepository
) : ViewModel() {
    
    private val _jobs = MutableStateFlow<List<JobDto>>(emptyList())
    val jobs: StateFlow<List<JobDto>> = _jobs.asStateFlow()
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    
    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()
    
    private val _showRetryButton = MutableStateFlow(false)
    val showRetryButton: StateFlow<Boolean> = _showRetryButton.asStateFlow()
    
    private val _driverStatus = MutableStateFlow<DriverStatusResponse?>(null)
    val driverStatus: StateFlow<DriverStatusResponse?> = _driverStatus.asStateFlow()
    
    private val _canAccessOrders = MutableStateFlow(true)
    val canAccessOrders: StateFlow<Boolean> = _canAccessOrders.asStateFlow()

    init {
        checkDriverStatusAndLoadJobs()
    }

    fun loadJobs(statusFilter: String = "active") {
        viewModelScope.launch {
            repo.getJobs(statusFilter).collect { result ->
                when (result) {
                    is Result.Loading -> {
                        _loading.value = true
                        _errorMessage.value = null
                        _showRetryButton.value = false
                    }
                    is Result.Success -> {
                        _loading.value = false
                        _jobs.value = result.data
                        _errorMessage.value = null
                        _showRetryButton.value = false
                    }
                    is Result.Error -> {
                        _loading.value = false
                        _errorMessage.value = result.userMessage
                        _showRetryButton.value = result.isRecoverable
                        
                        // Handle authentication errors
                        if (result.requiresReauth) {
                            // TODO: Navigate to login screen or show re-login dialog
                        }
                    }
                }
            }
        }
    }
    
    fun clearError() {
        _errorMessage.value = null
        _showRetryButton.value = false
    }
    
    fun retryLoadJobs(statusFilter: String = "active") {
        clearError()
        loadJobs(statusFilter)
    }
    
    private fun checkDriverStatusAndLoadJobs(statusFilter: String = "active") {
        viewModelScope.launch {
            _loading.value = true
            
            try {
                when (val statusResult = repo.getDriverStatus()) {
                    is Result.Success -> {
                        val status = statusResult.data
                        _driverStatus.value = status
                        _canAccessOrders.value = status.can_access_orders
                        
                        if (status.can_access_orders) {
                            // Driver can access orders, proceed with loading jobs
                            loadJobs(statusFilter)
                        } else {
                            // Driver cannot access orders
                            _loading.value = false
                            _errorMessage.value = status.message
                            _showRetryButton.value = false
                            _jobs.value = emptyList()
                        }
                    }
                    is Result.Error -> {
                        _loading.value = false
                        _errorMessage.value = statusResult.userMessage
                        _showRetryButton.value = statusResult.isRecoverable
                        _canAccessOrders.value = false
                        _jobs.value = emptyList()
                    }
                    is Result.Loading -> {
                        // Keep loading state
                    }
                }
            } catch (e: Exception) {
                _loading.value = false
                _errorMessage.value = "Failed to check driver status: ${e.message}"
                _showRetryButton.value = true
                _canAccessOrders.value = false
            }
        }
    }
    
    fun refreshDriverStatus(statusFilter: String = "active") {
        checkDriverStatusAndLoadJobs(statusFilter)
    }
}

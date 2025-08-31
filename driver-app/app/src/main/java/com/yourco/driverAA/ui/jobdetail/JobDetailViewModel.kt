package com.yourco.driverAA.ui.jobdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File
import javax.inject.Inject

@HiltViewModel
class JobDetailViewModel @Inject constructor(
    private val repository: JobsRepository
) : ViewModel() {
    
    private val _job = MutableStateFlow<JobDto?>(null)
    val job: StateFlow<JobDto?> = _job.asStateFlow()
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    private val _showOnHoldDialog = MutableStateFlow(false)
    val showOnHoldDialog: StateFlow<Boolean> = _showOnHoldDialog.asStateFlow()
    
    fun loadJob(jobId: String) {
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            when (val result = repository.getJob(jobId)) {
                is Result.Success -> {
                    _job.value = result.data
                    _loading.value = false
                }
                is Result.Error -> {
                    _error.value = result.throwable.message ?: "Failed to load job"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
    
    fun updateStatus(newStatus: String) {
        if (newStatus == "ON_HOLD") {
            // Show dialog to ask about customer availability
            _showOnHoldDialog.value = true
            return
        }
        
        val currentJob = _job.value ?: return
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            when (val result = repository.updateOrderStatus(currentJob.id, newStatus)) {
                is Result.Success -> {
                    _job.value = result.data
                    _loading.value = false
                }
                is Result.Error -> {
                    _error.value = result.throwable.message ?: "Failed to update status"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
    
    fun uploadPodPhoto(photoFile: File, photoNumber: Int = 1) {
        val currentJob = _job.value ?: return
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            when (val result = repository.uploadPodPhoto(currentJob.id, photoFile, photoNumber)) {
                is Result.Success -> {
                    _loading.value = false
                    // Reload job to get updated status with PoD photo
                    loadJob(currentJob.id)
                }
                is Result.Error -> {
                    _error.value = result.throwable.message ?: "Failed to upload photo $photoNumber"
                    _loading.value = false
                }
                is Result.Loading -> {
                    // Loading state is already handled above with _loading.value = true
                    // This branch should not be reached in practice
                }
            }
        }
    }
    
    fun dismissOnHoldDialog() {
        _showOnHoldDialog.value = false
    }
    
    fun handleOnHoldResponse(customerAvailable: Boolean, deliveryDate: String? = null) {
        val currentJob = _job.value ?: return
        _showOnHoldDialog.value = false
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            when (val result = repository.handleOnHoldResponse(
                orderId = currentJob.id.toInt(),
                customerAvailable = customerAvailable,
                deliveryDate = deliveryDate
            )) {
                is Result.Success -> {
                    // Reload job to get updated status
                    loadJob(currentJob.id)
                }
                is Result.Error -> {
                    _error.value = result.throwable.message ?: "Failed to handle on-hold response"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
}
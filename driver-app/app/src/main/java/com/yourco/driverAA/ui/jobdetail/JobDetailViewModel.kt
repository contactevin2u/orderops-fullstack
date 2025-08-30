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
                    _error.value = result.exception.message ?: "Failed to load job"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
    
    fun updateStatus(newStatus: String) {
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
                    _error.value = result.exception.message ?: "Failed to update status"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
}
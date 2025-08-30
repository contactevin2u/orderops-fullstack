package com.yourco.driverAA.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.CommissionMonthDto
import com.yourco.driverAA.domain.JobsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class CommissionsViewModel @Inject constructor(
    private val repository: JobsRepository
) : ViewModel() {
    
    private val _commissions = MutableStateFlow<List<CommissionMonthDto>>(emptyList())
    val commissions: StateFlow<List<CommissionMonthDto>> = _commissions.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    fun loadCommissions() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            
            try {
                val result = repository.getCommissions()
                _commissions.value = result
            } catch (e: Exception) {
                _error.value = e.message ?: "Failed to load commissions"
            } finally {
                _isLoading.value = false
            }
        }
    }
}
package com.yourco.driverAA.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.UpsellIncentivesDto
import com.yourco.driverAA.domain.JobsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class UpsellIncentivesViewModel @Inject constructor(
    private val repository: JobsRepository
) : ViewModel() {
    
    private val _upsellIncentives = MutableStateFlow<UpsellIncentivesDto?>(null)
    val upsellIncentives: StateFlow<UpsellIncentivesDto?> = _upsellIncentives.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    private val _selectedMonth = MutableStateFlow<String?>(null)
    val selectedMonth: StateFlow<String?> = _selectedMonth.asStateFlow()
    
    private val _statusFilter = MutableStateFlow<String?>(null) // null = all, PENDING, RELEASED
    val statusFilter: StateFlow<String?> = _statusFilter.asStateFlow()
    
    init {
        loadUpsellIncentives()
    }
    
    fun loadUpsellIncentives() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            
            try {
                val result = repository.getUpsellIncentives(_selectedMonth.value, _statusFilter.value)
                _upsellIncentives.value = result
            } catch (e: Exception) {
                _error.value = e.message ?: "Failed to load upsell incentives"
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun selectMonth(month: String?) {
        if (_selectedMonth.value != month) {
            _selectedMonth.value = month
            loadUpsellIncentives()
        }
    }
    
    fun setStatusFilter(status: String?) {
        if (_statusFilter.value != status) {
            _statusFilter.value = status
            loadUpsellIncentives()
        }
    }
}
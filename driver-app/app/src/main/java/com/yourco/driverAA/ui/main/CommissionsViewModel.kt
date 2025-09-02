package com.yourco.driverAA.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.CommissionMonthDto
import com.yourco.driverAA.data.api.UpsellIncentivesDto
import com.yourco.driverAA.data.api.JobDto
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
    
    private val _selectedMonth = MutableStateFlow<String?>(null)
    val selectedMonth: StateFlow<String?> = _selectedMonth.asStateFlow()
    
    private val _showMonthPicker = MutableStateFlow(false)
    val showMonthPicker: StateFlow<Boolean> = _showMonthPicker.asStateFlow()
    
    private val _upsellIncentives = MutableStateFlow<UpsellIncentivesDto?>(null)
    val upsellIncentives: StateFlow<UpsellIncentivesDto?> = _upsellIncentives.asStateFlow()
    
    private val _activeTab = MutableStateFlow("commissions") // "commissions" or "upsells"
    val activeTab: StateFlow<String> = _activeTab.asStateFlow()
    
    private val _detailedOrders = MutableStateFlow<List<JobDto>>(emptyList())
    val detailedOrders: StateFlow<List<JobDto>> = _detailedOrders.asStateFlow()
    
    private val _showDetailedOrders = MutableStateFlow(false)
    val showDetailedOrders: StateFlow<Boolean> = _showDetailedOrders.asStateFlow()
    
    fun loadCommissions() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            
            try {
                val commissionsResult = repository.getCommissions()
                _commissions.value = commissionsResult.sortedByDescending { it.month }
                
                // Also load upsell incentives
                val upsellsResult = repository.getUpsellIncentives()
                _upsellIncentives.value = upsellsResult
                
                // Set current month if not already selected
                if (_selectedMonth.value == null && commissionsResult.isNotEmpty()) {
                    val currentMonth = getCurrentMonth()
                    _selectedMonth.value = commissionsResult.find { it.month == currentMonth }?.month
                }
            } catch (e: Exception) {
                _error.value = e.message ?: "Failed to load commissions"
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun selectMonth(month: String) {
        _selectedMonth.value = month
        _showMonthPicker.value = false
    }
    
    fun toggleMonthPicker() {
        _showMonthPicker.value = !_showMonthPicker.value
    }
    
    fun setActiveTab(tab: String) {
        _activeTab.value = tab
    }
    
    fun loadDetailedOrders(month: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            
            try {
                val orders = repository.getDriverOrders(month)
                _detailedOrders.value = orders
                _showDetailedOrders.value = true
            } catch (e: Exception) {
                _error.value = e.message ?: "Failed to load detailed orders"
            } finally {
                _isLoading.value = false
            }
        }
    }
    
    fun hideDetailedOrders() {
        _showDetailedOrders.value = false
        _detailedOrders.value = emptyList()
    }
    
    private fun getCurrentMonth(): String {
        val currentDate = java.time.LocalDate.now()
        return "${currentDate.year}-${currentDate.monthValue.toString().padStart(2, '0')}"
    }
}
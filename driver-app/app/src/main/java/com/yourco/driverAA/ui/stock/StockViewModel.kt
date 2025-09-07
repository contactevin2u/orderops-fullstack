package com.yourco.driverAA.ui.stock

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.InventoryConfigResponse
import com.yourco.driverAA.data.api.LorryStockResponse
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import com.yourco.driverAA.util.MalayErrorMessages
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import javax.inject.Inject

@HiltViewModel
class StockViewModel @Inject constructor(
    private val repository: JobsRepository
) : ViewModel() {
    
    private val _lorryStock = MutableStateFlow<LorryStockResponse?>(null)
    val lorryStock: StateFlow<LorryStockResponse?> = _lorryStock.asStateFlow()
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    private val _selectedDate = MutableStateFlow(LocalDate.now().format(DateTimeFormatter.ISO_LOCAL_DATE))
    val selectedDate: StateFlow<String> = _selectedDate.asStateFlow()
    
    private val _inventoryConfig = MutableStateFlow<InventoryConfigResponse?>(null)
    val inventoryConfig: StateFlow<InventoryConfigResponse?> = _inventoryConfig.asStateFlow()
    
    init {
        loadInventoryConfig()
    }
    
    private fun loadInventoryConfig() {
        viewModelScope.launch {
            when (val result = repository.getInventoryConfig()) {
                is Result.Success -> {
                    _inventoryConfig.value = result.data
                }
                is Result.Error -> {
                    android.util.Log.w("StockViewModel", "Failed to load inventory config: ${result.throwable.message}")
                    // Fallback to enabled defaults for production
                    _inventoryConfig.value = InventoryConfigResponse(
                        uid_inventory_enabled = true,
                        uid_scan_required_after_pod = true,
                        inventory_mode = "required"
                    )
                }
                is Result.Loading -> {
                    // Loading handled by main stock loading
                }
            }
        }
    }
    
    fun loadTodaysStock() {
        loadStockForDate(LocalDate.now())
    }
    
    fun loadStockForDate(date: LocalDate) {
        val dateString = date.format(DateTimeFormatter.ISO_LOCAL_DATE)
        _selectedDate.value = dateString
        
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            when (val result = repository.getLorryStock(dateString)) {
                is Result.Success -> {
                    _lorryStock.value = result.data
                    _loading.value = false
                }
                is Result.Error -> {
                    _error.value = MalayErrorMessages.getErrorMessage(result.throwable)
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
    
    fun refreshStock() {
        val currentDate = LocalDate.parse(_selectedDate.value, DateTimeFormatter.ISO_LOCAL_DATE)
        loadStockForDate(currentDate)
    }
    
    fun clearError() {
        _error.value = null
    }
    
    fun checkStockVerificationStatus(callback: (Boolean) -> Unit) {
        viewModelScope.launch {
            try {
                when (val result = repository.getDriverStatus()) {
                    is Result.Success -> {
                        val status = result.data
                        // If driver cannot access orders due to stock verification, show verification screen
                        val needsVerification = !status.can_access_orders && 
                                              status.assignment_status.has_assignment && 
                                              !status.assignment_status.stock_verified
                        callback(needsVerification)
                    }
                    is Result.Error -> {
                        callback(false) // On error, show normal stock screen
                    }
                    is Result.Loading -> {
                        // Keep checking
                    }
                }
            } catch (e: Exception) {
                callback(false) // On exception, show normal stock screen
            }
        }
    }
    
    // Helper functions for UI
    fun isInventoryEnabled(): Boolean {
        return true
    }
    
    fun getStockSummary(): String {
        val stock = _lorryStock.value ?: return "No data"
        val scanned = stock.totalScanned ?: 0
        val expected = stock.totalExpected
        val variance = stock.totalVariance ?: 0
        
        return when {
            variance == 0 -> "Stock matched: $scanned/$expected items"
            variance > 0 -> "Excess stock: +$variance items ($scanned/$expected)"
            else -> "Short stock: $variance items ($scanned/$expected)"
        }
    }
    
    fun hasStockData(): Boolean {
        return _lorryStock.value != null && _lorryStock.value!!.items.isNotEmpty()
    }
    
    fun getStockStatus(): StockStatus {
        val stock = _lorryStock.value
        return when {
            false -> StockStatus.DISABLED
            _loading.value -> StockStatus.LOADING
            _error.value != null -> StockStatus.ERROR
            stock == null -> StockStatus.NO_DATA
            stock.totalVariance == null -> StockStatus.PARTIAL_DATA
            stock.totalVariance == 0 -> StockStatus.BALANCED
            stock.totalVariance!! > 0 -> StockStatus.EXCESS
            else -> StockStatus.SHORT
        }
    }
}

enum class StockStatus {
    DISABLED,
    LOADING,
    ERROR,
    NO_DATA,
    PARTIAL_DATA,
    BALANCED,
    EXCESS,
    SHORT
}
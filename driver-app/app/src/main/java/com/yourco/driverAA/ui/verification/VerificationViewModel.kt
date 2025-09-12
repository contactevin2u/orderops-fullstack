// ui/verification/VerificationViewModel.kt
package com.yourco.driverAA.ui.verification

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.ui.model.LorryStockUi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class VerificationUiState(
    val loading: Boolean = true,
    val stock: LorryStockUi? = null,
    val uploading: Boolean = false,
    val uploadComplete: Boolean = false,
    val error: String? = null
)

class VerificationViewModel(
    private val repo: JobsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(VerificationUiState())
    val state: StateFlow<VerificationUiState> = _state

    fun loadTodayStock() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            try {
                val stockRes = repo.getTodayLorryStock()
                val stock = stockRes.getOrNull()
                _state.value = _state.value.copy(
                    loading = false,
                    stock = stock,
                    error = if (stock == null) "Failed to load stock data" else null
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Unknown error occurred"
                )
            }
        }
    }

    fun updateSkuCount(skuId: Int, newCount: Int) {
        val currentStock = _state.value.stock ?: return
        val updatedSkus = currentStock.skus.map { sku ->
            if (sku.skuId == skuId) sku.copy(counted = newCount) else sku
        }
        _state.value = _state.value.copy(
            stock = currentStock.copy(skus = updatedSkus)
        )
    }

    fun submitStockCount() {
        val stock = _state.value.stock ?: return
        
        viewModelScope.launch {
            _state.value = _state.value.copy(uploading = true, error = null)
            try {
                val uploadRes = repo.uploadStockCount(
                    asOfDate = stock.dateIso,
                    skuCounts = stock.skus.associate { it.skuId to it.counted }
                )
                
                if (uploadRes.isSuccess) {
                    _state.value = _state.value.copy(
                        uploading = false,
                        uploadComplete = true
                    )
                } else {
                    _state.value = _state.value.copy(
                        uploading = false,
                        error = "Upload failed: ${uploadRes.exceptionOrNull()?.message}"
                    )
                }
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    uploading = false,
                    error = e.message ?: "Upload failed"
                )
            }
        }
    }

    fun getTotalCounted(): Int {
        return _state.value.stock?.skus?.sumOf { it.counted } ?: 0
    }

    fun getVariance(): Int {
        val stock = _state.value.stock ?: return 0
        return getTotalCounted() - stock.totalExpected
    }

    fun isReadyToSubmit(): Boolean {
        val stock = _state.value.stock ?: return false
        return stock.skus.isNotEmpty() && !_state.value.uploading && !_state.value.uploadComplete
    }
}
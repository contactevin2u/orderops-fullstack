package com.yourco.driverAA.ui.jobdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import com.yourco.driverAA.data.api.UpsellRequest
import com.yourco.driverAA.data.api.UpsellItemRequest
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
    
    private val _showUpsellDialog = MutableStateFlow(false)
    val showUpsellDialog: StateFlow<Boolean> = _showUpsellDialog.asStateFlow()
    
    private val _selectedUpsellItem = MutableStateFlow<JobItemDto?>(null)
    val selectedUpsellItem: StateFlow<JobItemDto?> = _selectedUpsellItem.asStateFlow()
    
    private val _uploadingPhotos = MutableStateFlow<Set<Int>>(emptySet())
    val uploadingPhotos: StateFlow<Set<Int>> = _uploadingPhotos.asStateFlow()
    
    private val _uploadedPhotos = MutableStateFlow<Set<Int>>(emptySet())
    val uploadedPhotos: StateFlow<Set<Int>> = _uploadedPhotos.asStateFlow()
    
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
            // Mark photo as uploading
            _uploadingPhotos.value = _uploadingPhotos.value + photoNumber
            _error.value = null
            
            when (val result = repository.uploadPodPhoto(currentJob.id, photoFile, photoNumber)) {
                is Result.Success -> {
                    // Mark photo as uploaded and remove from uploading
                    _uploadingPhotos.value = _uploadingPhotos.value - photoNumber
                    _uploadedPhotos.value = _uploadedPhotos.value + photoNumber
                    
                    // Reload job to get updated status with PoD photo
                    loadJob(currentJob.id)
                }
                is Result.Error -> {
                    // Remove from uploading on error
                    _uploadingPhotos.value = _uploadingPhotos.value - photoNumber
                    _error.value = result.throwable.message ?: "Failed to upload photo $photoNumber"
                }
                is Result.Loading -> {
                    // Loading state is handled by _uploadingPhotos
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
            
            // Calculate delivery date: if customer not available, use tomorrow; otherwise use provided date
            val finalDeliveryDate = if (!customerAvailable) {
                val tomorrow = java.time.LocalDate.now().plusDays(1)
                tomorrow.toString()
            } else {
                deliveryDate
            }
            
            when (val result = repository.handleOnHoldResponse(
                orderId = currentJob.id,
                deliveryDate = finalDeliveryDate
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
    
    fun showUpsellDialog(item: JobItemDto) {
        _selectedUpsellItem.value = item
        _showUpsellDialog.value = true
    }
    
    fun dismissUpsellDialog() {
        _showUpsellDialog.value = false
        _selectedUpsellItem.value = null
    }
    
    fun upsellItem(
        item: JobItemDto,
        upsellType: String, // "BELI_TERUS" or "ANSURAN"
        newName: String?,
        newPrice: Double,
        installmentMonths: Int?
    ) {
        val currentJob = _job.value ?: return
        _showUpsellDialog.value = false
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            
            val upsellRequest = UpsellRequest(
                items = listOf(
                    UpsellItemRequest(
                        item_id = item.id?.toInt() ?: return@launch,
                        upsell_type = upsellType,
                        new_name = newName,
                        new_price = newPrice,
                        installment_months = installmentMonths
                    )
                ),
                notes = "Upsell: ${item.name} -> $upsellType RM$newPrice${if (installmentMonths != null) " ($installmentMonths bulan)" else ""}"
            )
            
            when (val result = repository.upsellOrder(currentJob.id, upsellRequest)) {
                is Result.Success -> {
                    // Reload job to show updated items and totals
                    loadJob(currentJob.id)
                }
                is Result.Error -> {
                    _error.value = result.throwable.message ?: "Failed to upsell item"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
}
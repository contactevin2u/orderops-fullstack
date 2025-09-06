package com.yourco.driverAA.ui.jobdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import com.yourco.driverAA.data.api.UpsellRequest
import com.yourco.driverAA.data.api.UpsellItemRequest
import com.yourco.driverAA.data.api.InventoryConfigResponse
import com.yourco.driverAA.data.api.UIDScanRequest
import com.yourco.driverAA.data.api.UIDScanResponse
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import com.yourco.driverAA.util.OrderStateValidator
import com.yourco.driverAA.util.ValidationResult
import com.yourco.driverAA.util.MalayErrorMessages
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
    
    // Store photo files to persist thumbnails after job reload
    private val _uploadedPhotoFiles = MutableStateFlow<Map<Int, File>>(emptyMap())
    val uploadedPhotoFiles: StateFlow<Map<Int, File>> = _uploadedPhotoFiles.asStateFlow()
    
    // Store all driver jobs for validation
    private val _allJobs = MutableStateFlow<List<JobDto>>(emptyList())
    val allJobs: StateFlow<List<JobDto>> = _allJobs.asStateFlow()
    
    // Success message for positive feedback
    private val _successMessage = MutableStateFlow<String?>(null)
    val successMessage: StateFlow<String?> = _successMessage.asStateFlow()
    
    // UID Inventory state
    private val _inventoryConfig = MutableStateFlow<InventoryConfigResponse?>(null)
    val inventoryConfig: StateFlow<InventoryConfigResponse?> = _inventoryConfig.asStateFlow()
    
    private val _showUIDScanDialog = MutableStateFlow(false)
    val showUIDScanDialog: StateFlow<Boolean> = _showUIDScanDialog.asStateFlow()
    
    private val _scannedUIDs = MutableStateFlow<List<UIDScanResponse>>(emptyList())
    val scannedUIDs: StateFlow<List<UIDScanResponse>> = _scannedUIDs.asStateFlow()
    
    private val _uidScanLoading = MutableStateFlow(false)
    val uidScanLoading: StateFlow<Boolean> = _uidScanLoading.asStateFlow()
    
    fun loadJob(jobId: String) {
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            _successMessage.value = null
            
            // Load all driver jobs for validation
            loadAllJobs()
            
            // Load inventory configuration
            loadInventoryConfig()
            
            when (val result = repository.getJob(jobId)) {
                is Result.Success -> {
                    _job.value = result.data
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
    
    private fun loadAllJobs() {
        viewModelScope.launch {
            repository.getJobs("active").collect { result ->
                when (result) {
                    is Result.Success -> {
                        _allJobs.value = result.data
                    }
                    is Result.Error -> {
                        // Don't show error for background job loading
                    }
                    is Result.Loading -> {
                        // Loading handled by main job loading
                    }
                }
            }
        }
    }
    
    private fun loadInventoryConfig() {
        viewModelScope.launch {
            when (val result = repository.getInventoryConfig()) {
                is Result.Success -> {
                    _inventoryConfig.value = result.data
                }
                is Result.Error -> {
                    // Don't show error for background config loading
                    android.util.Log.w("JobDetailViewModel", "Failed to load inventory config: ${result.throwable.message}")
                }
                is Result.Loading -> {
                    // Loading handled by main job loading
                }
            }
        }
    }
    
    fun updateStatus(newStatus: String) {
        val currentJob = _job.value ?: return
        val allJobsList = _allJobs.value
        
        // Only validate critical blocking issues (like multiple in-transit orders)
        if (newStatus == "IN_TRANSIT") {
            val inTransitJobs = allJobsList.filter { it.status == "IN_TRANSIT" && it.id != currentJob.id }
            if (inTransitJobs.isNotEmpty()) {
                val inTransitJob = inTransitJobs.first()
                _error.value = "Anda mempunyai pesanan dalam perjalanan (#${inTransitJob.code}). " +
                    "Sila selesaikan pesanan tersebut dahulu sebelum memulakan pesanan baru."
                return
            }
        }
        
        if (newStatus == "ON_HOLD") {
            // Show dialog to ask about customer availability
            _showOnHoldDialog.value = true
            return
        }
        
        // Remove client-side PoD validation - let backend handle it with proper server-side checks
        
        viewModelScope.launch {
            _loading.value = true
            _error.value = null
            _successMessage.value = null
            
            when (val result = repository.updateOrderStatus(currentJob.id, newStatus)) {
                is Result.Success -> {
                    _job.value = result.data
                    _successMessage.value = getSuccessMessage(newStatus)
                    _loading.value = false
                    
                    // Reload all jobs to update validation state
                    loadAllJobs()
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
                    
                    // Store the photo file for persistent thumbnail display
                    _uploadedPhotoFiles.value = _uploadedPhotoFiles.value + (photoNumber to photoFile)
                    
                    // Reload job to get updated status with PoD photo
                    loadJob(currentJob.id)
                }
                is Result.Error -> {
                    // Remove from uploading on error
                    _uploadingPhotos.value = _uploadingPhotos.value - photoNumber
                    _error.value = "Muat naik gambar $photoNumber gagal. ${MalayErrorMessages.getErrorMessage(result.throwable)}"
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
                "${tomorrow}T00:00:00+00:00"  // Convert to ISO datetime format with timezone
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
                    _error.value = "Gagal mengemaskini status tangguh. ${MalayErrorMessages.getErrorMessage(result.throwable)}"
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
            
            // Safely convert item.id to integer
            val itemId = try {
                item.id?.toInt() ?: run {
                    _error.value = "ID item tidak sah"
                    _loading.value = false
                    return@launch
                }
            } catch (e: NumberFormatException) {
                _error.value = "Format ID item tidak sah"
                _loading.value = false
                return@launch
            }
            
            val upsellRequest = UpsellRequest(
                items = listOf(
                    UpsellItemRequest(
                        item_id = itemId,
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
                    _error.value = "Gagal menambah item. ${MalayErrorMessages.getErrorMessage(result.throwable)}"
                    _loading.value = false
                }
                is Result.Loading -> {
                    _loading.value = true
                }
            }
        }
    }
    
    // Helper functions for UI
    fun getStatusDisplayText(status: String?): String {
        return OrderStateValidator.getStatusDisplayText(status)
    }
    
    fun getActionButtonText(targetStatus: String): String {
        val currentStatus = _job.value?.status
        return OrderStateValidator.getActionButtonText(currentStatus, targetStatus)
    }
    
    fun getOrderStateMessage(): String {
        val currentJob = _job.value ?: return ""
        return OrderStateValidator.getOrderStateMessage(currentJob)
    }
    
    fun canPerformAction(targetStatus: String): Boolean {
        val currentJob = _job.value ?: return false
        val currentStatus = currentJob.status
        
        // Basic validation - most transitions are allowed, backend will handle detailed validation
        return when (targetStatus) {
            "IN_TRANSIT" -> {
                // Only block if there's another in-transit order
                val allJobsList = _allJobs.value
                val inTransitJobs = allJobsList.filter { it.status == "IN_TRANSIT" && it.id != currentJob.id }
                inTransitJobs.isEmpty() && currentStatus in listOf("ASSIGNED", "ON_HOLD")
            }
            "DELIVERED" -> currentStatus == "IN_TRANSIT"
            "ON_HOLD" -> currentStatus in listOf("ASSIGNED", "IN_TRANSIT")
            "CANCELLED" -> currentStatus in listOf("ASSIGNED", "ON_HOLD")
            else -> true
        }
    }
    
    fun getValidationMessage(targetStatus: String): String {
        // Return simple status-based messages, let backend handle complex validation
        return when (targetStatus) {
            "IN_TRANSIT" -> "Mula pesanan"
            "DELIVERED" -> "Tandakan sebagai dihantar"
            "ON_HOLD" -> "Tangguhkan pesanan"
            "CANCELLED" -> "Batalkan pesanan"
            else -> "Kemaskini status"
        }
    }
    
    fun clearMessages() {
        _error.value = null
        _successMessage.value = null
    }
    
    fun isOrderInTransit(): Boolean {
        return _job.value?.status == "IN_TRANSIT"
    }
    
    fun isOrderCompleted(): Boolean {
        val status = _job.value?.status
        return status == "DELIVERED" || status == "CANCELLED"
    }
    
    fun hasInTransitOrders(): Boolean {
        return _allJobs.value.any { it.status == "IN_TRANSIT" }
    }
    
    fun getInTransitOrderCode(): String? {
        return _allJobs.value.find { it.status == "IN_TRANSIT" }?.code
    }
    
    private fun getSuccessMessage(status: String): String {
        return when (status) {
            "IN_TRANSIT" -> "Pesanan berjaya dimulakan"
            "DELIVERED" -> "Pesanan berjaya dihantar"
            "CANCELLED" -> "Pesanan dibatalkan"
            else -> "Status berjaya dikemaskini"
        }
    }
    
    // UID Inventory functions
    fun isInventoryEnabled(): Boolean {
        return _inventoryConfig.value?.uid_inventory_enabled == true
    }
    
    fun isUIDScanRequired(): Boolean {
        return _inventoryConfig.value?.uid_scan_required_after_pod == true
    }
    
    fun shouldShowUIDScanAfterPOD(): Boolean {
        val config = _inventoryConfig.value
        val job = _job.value
        
        // Show UID scanning if inventory is enabled and job is in DELIVERED status
        return config?.uid_inventory_enabled == true && 
               job?.status?.uppercase() == "DELIVERED" && 
               _uploadedPhotos.value.isNotEmpty()
    }
    
    fun showUIDScanDialog() {
        _showUIDScanDialog.value = true
    }
    
    fun dismissUIDScanDialog() {
        _showUIDScanDialog.value = false
    }
    
    fun scanUID(uid: String, skuId: Int? = null, action: String = "ISSUE") {
        val currentJob = _job.value ?: return
        
        viewModelScope.launch {
            _uidScanLoading.value = true
            _error.value = null
            
            val jobId = try {
                currentJob.id.toInt()
            } catch (e: NumberFormatException) {
                _error.value = "ID pesanan tidak sah"
                _uidScanLoading.value = false
                return@launch
            }
            
            val request = UIDScanRequest(
                order_id = jobId,
                action = action,
                uid = uid.trim().uppercase(),
                sku_id = skuId
            )
            
            when (val result = repository.scanUID(request)) {
                is Result.Success -> {
                    // Add to scanned UIDs list
                    _scannedUIDs.value = _scannedUIDs.value + result.data
                    _successMessage.value = "UID ${result.data.uid} berjaya direkod"
                    _uidScanLoading.value = false
                }
                is Result.Error -> {
                    _error.value = "Gagal merekod UID: ${MalayErrorMessages.getErrorMessage(result.throwable)}"
                    _uidScanLoading.value = false
                }
                is Result.Loading -> {
                    _uidScanLoading.value = true
                }
            }
        }
    }
    
    fun canCompleteDeliveryWithoutUID(): Boolean {
        val config = _inventoryConfig.value
        
        // Can complete if UID scanning is not required, or if not enabled at all
        return config?.uid_scan_required_after_pod != true
    }
    
    fun getUIDScanStatusMessage(): String {
        val config = _inventoryConfig.value ?: return ""
        val scannedCount = _scannedUIDs.value.size
        
        return when {
            !config.uid_inventory_enabled -> ""
            config.uid_scan_required_after_pod -> {
                if (scannedCount == 0) {
                    "UID diperlukan sebelum selesai"
                } else {
                    "$scannedCount UID direkod"
                }
            }
            else -> {
                if (scannedCount == 0) {
                    "UID pilihan (boleh skip)"
                } else {
                    "$scannedCount UID direkod"
                }
            }
        }
    }
}
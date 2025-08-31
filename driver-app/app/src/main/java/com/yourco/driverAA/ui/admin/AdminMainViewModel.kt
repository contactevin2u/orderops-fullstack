package com.yourco.driverAA.ui.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.AssignmentSuggestionsResponse
import com.yourco.driverAA.data.api.AvailableDriver
import com.yourco.driverAA.data.api.PendingOrder
import com.yourco.driverAA.data.auth.AuthService
import com.yourco.driverAA.data.repository.AdminRepository
import com.yourco.driverAA.data.repository.ParsedOrderInfo
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AdminUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val successMessage: String? = null,
    
    // Message parsing
    val parsedOrder: ParsedOrderInfo? = null,
    
    // AI Assignments
    val aiSuggestions: AssignmentSuggestionsResponse? = null,
    val applyingAssignments: Set<Int> = emptySet(),
    val acceptingAllAssignments: Boolean = false,
    
    // Orders and Drivers
    val pendingOrders: List<PendingOrder> = emptyList(),
    val availableDrivers: List<AvailableDriver> = emptyList(),
    
    // Created orders
    val createdOrders: List<String> = emptyList()
)

@HiltViewModel
class AdminMainViewModel @Inject constructor(
    val authService: AuthService,
    private val adminRepository: AdminRepository
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(AdminUiState())
    val uiState: StateFlow<AdminUiState> = _uiState.asStateFlow()
    
    fun parseMessage(messageText: String): ParsedOrderInfo? {
        return adminRepository.parseOrderMessage(messageText)
    }
    
    fun showPreview(parsed: ParsedOrderInfo?) {
        _uiState.value = _uiState.value.copy(
            parsedOrder = parsed,
            error = if (parsed == null) "Could not parse message. Please check the format." else null
        )
    }
    
    fun clearPreview() {
        _uiState.value = _uiState.value.copy(parsedOrder = null, error = null)
    }
    
    fun createOrderFromParsed(parsed: ParsedOrderInfo, onComplete: (Boolean) -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            adminRepository.createOrder(
                customerName = parsed.customerName,
                customerPhone = parsed.customerPhone,
                deliveryAddress = parsed.deliveryAddress,
                notes = parsed.notes,
                totalAmount = parsed.totalAmount
            ).fold(
                onSuccess = { order ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        successMessage = "Order #${order.id} created successfully!",
                        parsedOrder = null,
                        createdOrders = _uiState.value.createdOrders + order.code.orEmpty()
                    )
                    onComplete(true)
                    // Clear success message after a delay
                    viewModelScope.launch {
                        kotlinx.coroutines.delay(3000)
                        _uiState.value = _uiState.value.copy(successMessage = null)
                    }
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "Failed to create order: ${error.message}"
                    )
                    onComplete(false)
                }
            )
        }
    }
    
    fun loadAIAssignmentSuggestions() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            
            adminRepository.getAIAssignmentSuggestions().fold(
                onSuccess = { suggestions ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        aiSuggestions = suggestions
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        isLoading = false,
                        error = "Failed to load AI suggestions: ${error.message}"
                    )
                }
            )
        }
    }
    
    fun applyAssignment(orderId: Int, driverId: Int) {
        viewModelScope.launch {
            val currentApplying = _uiState.value.applyingAssignments
            _uiState.value = _uiState.value.copy(
                applyingAssignments = currentApplying + orderId
            )
            
            adminRepository.applyAssignment(orderId, driverId).fold(
                onSuccess = { response ->
                    _uiState.value = _uiState.value.copy(
                        applyingAssignments = _uiState.value.applyingAssignments - orderId,
                        successMessage = response.message
                    )
                    // Refresh suggestions and orders
                    loadAIAssignmentSuggestions()
                    loadPendingOrders()
                    // Clear success message
                    viewModelScope.launch {
                        kotlinx.coroutines.delay(3000)
                        _uiState.value = _uiState.value.copy(successMessage = null)
                    }
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        applyingAssignments = _uiState.value.applyingAssignments - orderId,
                        error = "Failed to apply assignment: ${error.message}"
                    )
                }
            )
        }
    }
    
    fun acceptAllAssignments() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(
                acceptingAllAssignments = true,
                error = null
            )
            
            adminRepository.acceptAllAssignments().fold(
                onSuccess = { response ->
                    _uiState.value = _uiState.value.copy(
                        acceptingAllAssignments = false,
                        successMessage = response.message
                    )
                    // Refresh suggestions and orders
                    loadAIAssignmentSuggestions()
                    loadPendingOrders()
                    // Clear success message
                    viewModelScope.launch {
                        kotlinx.coroutines.delay(5000)
                        _uiState.value = _uiState.value.copy(successMessage = null)
                    }
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        acceptingAllAssignments = false,
                        error = "Failed to accept all assignments: ${error.message}"
                    )
                }
            )
        }
    }
    
    fun loadPendingOrders() {
        viewModelScope.launch {
            adminRepository.getPendingOrders().fold(
                onSuccess = { response ->
                    _uiState.value = _uiState.value.copy(
                        pendingOrders = response.pending_orders
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        error = "Failed to load pending orders: ${error.message}"
                    )
                }
            )
        }
    }
    
    fun loadAvailableDrivers() {
        viewModelScope.launch {
            adminRepository.getAvailableDrivers().fold(
                onSuccess = { response ->
                    _uiState.value = _uiState.value.copy(
                        availableDrivers = response.available_drivers
                    )
                },
                onFailure = { error ->
                    _uiState.value = _uiState.value.copy(
                        error = "Failed to load available drivers: ${error.message}"
                    )
                }
            )
        }
    }
    
    fun loadCurrentAssignments() {
        // Placeholder for future implementation
        // This would load current trip assignments for editing
    }
    
    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}
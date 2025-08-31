package com.yourco.driverAA.data.repository

import com.yourco.driverAA.data.api.AcceptAllResponse
import com.yourco.driverAA.data.api.ApplyAssignmentRequest
import com.yourco.driverAA.data.api.AssignmentApplyResponse
import com.yourco.driverAA.data.api.AssignmentSuggestionsResponse
import com.yourco.driverAA.data.api.AvailableDriversResponse
import com.yourco.driverAA.data.api.CreateOrderRequest
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.OrderDto
import com.yourco.driverAA.data.api.PendingOrdersResponse
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AdminRepository @Inject constructor(
    private val api: DriverApi
) {
    
    suspend fun getAIAssignmentSuggestions(): Result<AssignmentSuggestionsResponse> {
        return try {
            val response = api.getAIAssignmentSuggestions()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun applyAssignment(orderId: Int, driverId: Int): Result<AssignmentApplyResponse> {
        return try {
            val request = ApplyAssignmentRequest(orderId, driverId)
            val response = api.applyAssignment(request)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun acceptAllAssignments(): Result<AcceptAllResponse> {
        return try {
            val response = api.acceptAllAssignments()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getAvailableDrivers(): Result<AvailableDriversResponse> {
        return try {
            val response = api.getAvailableDrivers()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun getPendingOrders(): Result<PendingOrdersResponse> {
        return try {
            val response = api.getPendingOrders()
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun createOrder(
        customerName: String,
        customerPhone: String?,
        deliveryAddress: String,
        notes: String?,
        totalAmount: Double,
        deliveryDate: String? = null
    ): Result<OrderDto> {
        return try {
            val request = CreateOrderRequest(
                customer_name = customerName,
                customer_phone = customerPhone,
                delivery_address = deliveryAddress,
                notes = notes,
                total_amount = totalAmount,
                delivery_date = deliveryDate
            )
            val response = api.createOrder(request)
            Result.success(response)
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    // Parse message text to extract order information
    fun parseOrderMessage(message: String): ParsedOrderInfo? {
        return try {
            val lines = message.trim().split("\n").map { it.trim() }
            var customerName = ""
            var customerPhone: String? = null
            var deliveryAddress = ""
            var notes = ""
            var totalAmount = 0.0
            
            for (line in lines) {
                when {
                    line.startsWith("Name:", ignoreCase = true) || 
                    line.startsWith("Customer:", ignoreCase = true) -> {
                        customerName = line.substringAfter(":").trim()
                    }
                    line.startsWith("Phone:", ignoreCase = true) || 
                    line.startsWith("Tel:", ignoreCase = true) ||
                    line.startsWith("Contact:", ignoreCase = true) -> {
                        customerPhone = line.substringAfter(":").trim()
                            .replace("+6", "").replace("-", "").replace(" ", "")
                        // Normalize Malaysian phone number
                        if (customerPhone?.startsWith("01") == true && customerPhone.length >= 10) {
                            customerPhone = "6$customerPhone"
                        }
                    }
                    line.startsWith("Address:", ignoreCase = true) || 
                    line.startsWith("Location:", ignoreCase = true) -> {
                        deliveryAddress = line.substringAfter(":").trim()
                    }
                    line.startsWith("Amount:", ignoreCase = true) || 
                    line.startsWith("Total:", ignoreCase = true) ||
                    line.startsWith("Price:", ignoreCase = true) -> {
                        val amountStr = line.substringAfter(":").trim()
                            .replace("RM", "").replace("rm", "").replace(",", "").trim()
                        totalAmount = amountStr.toDoubleOrNull() ?: 0.0
                    }
                    line.startsWith("Notes:", ignoreCase = true) || 
                    line.startsWith("Remarks:", ignoreCase = true) -> {
                        notes = line.substringAfter(":").trim()
                    }
                    // If line doesn't start with a known prefix, treat as notes continuation
                    line.isNotEmpty() && !line.contains(":") && 
                    customerName.isNotEmpty() && deliveryAddress.isNotEmpty() -> {
                        notes = if (notes.isEmpty()) line else "$notes\n$line"
                    }
                }
            }
            
            if (customerName.isNotEmpty() && deliveryAddress.isNotEmpty()) {
                ParsedOrderInfo(
                    customerName = customerName,
                    customerPhone = customerPhone,
                    deliveryAddress = deliveryAddress,
                    notes = notes.ifEmpty { null },
                    totalAmount = totalAmount
                )
            } else null
            
        } catch (e: Exception) {
            null
        }
    }
}

data class ParsedOrderInfo(
    val customerName: String,
    val customerPhone: String?,
    val deliveryAddress: String,
    val notes: String?,
    val totalAmount: Double
)
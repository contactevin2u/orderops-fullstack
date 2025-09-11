package com.yourco.driverAA.data.api

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import okhttp3.MultipartBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface DriverApi {
    @GET("driver/me")
    suspend fun getCurrentUser(): ApiResponse<UserDto>
    
    @GET("driver/jobs")
    suspend fun getJobs(@Query("status_filter") statusFilter: String = "active"): List<JobDto>

    @GET("driver/jobs/{id}")
    suspend fun getJob(@Path("id") id: String): JobDto

    @POST("driver/locations")
    suspend fun postLocations(@Body locations: List<LocationPingDto>)
    
    @PATCH("driver/orders/{id}")
    suspend fun updateOrderStatus(@Path("id") orderId: String, @Body update: OrderStatusUpdateDto): JobDto
    
    @PATCH("orders/{id}/driver-update")
    suspend fun patchOrder(@Path("id") orderId: String, @Body update: OrderPatchDto): ApiResponse<OrderDto>
    
    @POST("orders/{id}/upsell")
    suspend fun upsellOrder(@Path("id") orderId: String, @Body request: UpsellRequest): ApiResponse<UpsellResponse>
    
    @Multipart
    @POST("driver/orders/{id}/pod-photo")
    suspend fun uploadPodPhoto(
        @Path("id") orderId: String, 
        @Part file: MultipartBody.Part,
        @Query("photo_number") photoNumber: Int = 1
    ): PodUploadResponse
    
    @GET("driver/orders")
    suspend fun getDriverOrders(@Query("month") month: String? = null): List<JobDto>
    
    @GET("driver/commissions")
    suspend fun getCommissions(): List<CommissionMonthDto>
    
    @GET("driver/upsell-incentives")
    suspend fun getUpsellIncentives(
        @Query("month") month: String? = null,
        @Query("status") status: String? = null
    ): UpsellIncentivesDto
    
    @POST("driver/shifts/clock-in")
    suspend fun clockIn(@Body request: ClockInRequest): ShiftResponse
    
    @POST("driver/shifts/clock-out")
    suspend fun clockOut(@Body request: ClockOutRequest): ShiftResponse
    
    @GET("driver/shifts/status")
    suspend fun getShiftStatus(): ShiftStatusResponse
    
    @GET("driver/shifts/active")
    suspend fun getActiveShift(): ShiftResponse?
    
    @GET("driver/shifts/history")
    suspend fun getShiftHistory(@Query("limit") limit: Int = 10): List<ShiftResponse>
    
    // UID Inventory endpoints
    @GET("driver/inventory/config")
    suspend fun getInventoryConfig(): InventoryConfigResponse
    
    @POST("driver/inventory/uid/scan")
    suspend fun scanUID(@Body request: UIDScanRequest): UIDScanResponse
    
    @GET("driver/inventory/lorry/{driver_id}/stock")
    suspend fun getLorryStock(@Path("driver_id") driverId: Int, @Query("date") date: String): ApiResponse<LorryStockResponse>
    
    @POST("driver/inventory/lorry/{driver_id}/stock/upload")
    suspend fun uploadLorryStock(@Path("driver_id") driverId: Int, @Body body: LorryStockUploadRequest): ApiResponse<Unit>
    
    @POST("driver/inventory/sku/resolve")
    suspend fun resolveSKU(@Body request: SKUResolveRequest): SKUResolveResponse
    
    // Orders are automatically assigned by backend AI - no manual assignment needed
    @POST("driver/orders/simple")
    suspend fun createOrder(@Body request: CreateOrderRequest): OrderDto
    
    // Lorry Management endpoints
    @GET("driver/lorry-management/my-assignment")
    suspend fun getMyLorryAssignment(@Query("date") date: String? = null): ApiResponse<MyAssignmentResponse>
    
    @POST("driver/lorry-management/clock-in-with-stock")
    suspend fun clockInWithStock(@Body request: ClockInWithStockRequest): ApiResponse<ShiftResponse>
    
    @GET("driver/lorry-management/driver-status")
    suspend fun getDriverStatus(): ApiResponse<DriverStatusResponse>
}

@Serializable
data class UserDto(
    val id: Int,
    val username: String,
    val role: String
)

@Serializable
data class UIDProcessingResult(
    val success_count: Int,
    val total_requested: Int,
    val errors: List<String> = emptyList()
)

@Serializable
data class JobDto(
    val id: String,
    val code: String? = null,
    val status: String? = null,
    val customer_name: String? = null,
    val customer_phone: String? = null,
    val address: String? = null,
    val delivery_date: String? = null,
    val notes: String? = null,
    val total: String? = null,
    val paid_amount: String? = null,
    val balance: String? = null,
    val type: String? = null, // OUTRIGHT | INSTALLMENT | RENTAL | MIXED
    val items: List<JobItemDto>? = null,
    val commission: CommissionDto? = null,
    val uid_processing: UIDProcessingResult? = null // New field for UID processing results
)

@Serializable
data class JobItemDto(
    val id: String? = null,
    val name: String? = null,
    val qty: Int? = null,
    val unit_price: String? = null,
    val uid: String? = null // Add uid property for UID tracking
)

@Serializable
data class CommissionDto(
    val amount: String,
    val status: String, // "EARNED" or "PAID" (new AI system) / "pending" or "actualized" (legacy)
    val scheme: String,
    val rate: String,
    val role: String? = null, // "primary" or "secondary"
    val payment_method: String? = null, // "cash" or "bank_transfer" (detected by AI)
    val ai_verified: Boolean? = null, // Whether AI verified the payment method
    val cash_collection_required: Boolean? = null, // Whether cash needs to be collected
    val released_at: String? = null, // When commission was released
    val notes: String? = null // Release notes or AI analysis details
)

@Serializable
data class LocationPingDto(val lat: Double, val lng: Double, val accuracy: Float, val speed: Float, val ts: Long)

@Serializable
data class UIDActionDto(
    val action: String, // DELIVER, COLLECT, REPAIR, SWAP
    val uid: String,
    val sku_id: Int? = null,
    val notes: String? = null
)

@Serializable
data class OrderStatusUpdateDto(
    val status: String,
    val uid_actions: List<UIDActionDto>? = null // New optional field for integrated UID workflow
)

@Serializable
data class PodUploadResponse(val url: String, val photo_number: Int)

@Serializable
data class CommissionMonthDto(
    val month: String,
    val total: Double
)

@Serializable
data class UpsellItemDto(
    val item_id: Int,
    val original_name: String,
    val new_name: String,
    val original_price: Double,
    val new_price: Double,
    val upsell_type: String,
    val installment_months: Int? = null
)

@Serializable
data class UpsellIncentiveDto(
    val id: Int,
    val order_id: Int,
    val order_code: String,
    val upsell_amount: Double,
    val driver_incentive: Double,
    val status: String, // PENDING, RELEASED
    val items_upsold: List<UpsellItemDto>,
    val notes: String? = null,
    val created_at: String,
    val released_at: String? = null
)

@Serializable
data class UpsellSummaryDto(
    val total_pending: Double,
    val total_released: Double,
    val total_records: Int
)

@Serializable
data class UpsellIncentivesDto(
    val incentives: List<UpsellIncentiveDto>,
    val summary: UpsellSummaryDto
)

@Serializable
data class ClockInRequest(
    val lat: Double,
    val lng: Double,
    val location_name: String? = null,
    val scanned_uids: List<String>? = null
)

@Serializable
data class ClockOutRequest(
    val lat: Double,
    val lng: Double,
    val location_name: String? = null,
    val notes: String? = null
)

@Serializable
data class ShiftResponse(
    val id: Int,
    val driver_id: Int,
    val clock_in_at: Long,
    val clock_in_lat: Double,
    val clock_in_lng: Double,
    val clock_in_location_name: String? = null,
    val clock_out_at: Long? = null,
    val clock_out_lat: Double? = null,
    val clock_out_lng: Double? = null,
    val clock_out_location_name: String? = null,
    val is_outstation: Boolean,
    val outstation_distance_km: Double? = null,
    val outstation_allowance_amount: Double,
    val total_working_hours: Double? = null,
    val status: String,
    val notes: String? = null,
    val created_at: Long
)

@Serializable
data class ShiftStatusResponse(
    val is_clocked_in: Boolean,
    val shift_id: Int? = null,
    val clock_in_at: Long? = null,
    val hours_worked: Float? = null,
    val is_outstation: Boolean? = null,
    val location: String? = null,
    val message: String
)

// Admin functionality removed - handled by frontend web admin

@Serializable
data class CreateOrderRequest(
    val customer_name: String,
    val customer_phone: String?,
    val delivery_address: String,
    val notes: String?,
    val total_amount: Double,
    val delivery_date: String? = null
)

@Serializable
data class OrderDto(
    val id: Int,
    val code: String,
    val type: String,
    val status: String,
    val delivery_date: String? = null,
    val notes: String? = null,
    val subtotal: String, // Decimal as String
    val discount: String? = "0",
    val delivery_fee: String? = "0", 
    val return_delivery_fee: String? = "0",
    val penalty_fee: String? = "0",
    val total: String, // Decimal as String
    val paid_amount: String,
    val balance: String,
    val customer: CustomerDto? = null,
    val items: List<OrderItemDto> = emptyList(),
    val payments: List<PaymentDto> = emptyList(),
    val plan: PlanDto? = null,
    val trip: TripDto? = null
)

@Serializable
data class OrderPatchDto(
    val status: String? = null,
    val delivery_date: String? = null
)

@Serializable 
data class UpsellItemRequest(
    val item_id: Int,
    val upsell_type: String, // "BELI_TERUS" | "ANSURAN"
    val new_name: String? = null,
    val new_price: Double, // New total price for the item
    val installment_months: Int? = null // Only for ANSURAN
)

@Serializable
data class UpsellRequest(
    val items: List<UpsellItemRequest>,
    val notes: String? = null
)

@Serializable
data class ApiResponse<T>(
    val ok: Boolean = true,
    val data: T,
    val error: String? = null
)

@Serializable
data class CustomerDto(
    val id: Int,
    val name: String?,
    val phone: String?,
    val address: String?
)

@Serializable
data class OrderItemDto(
    val id: Int,
    val name: String,
    val qty: Int,
    val unit_price: String,
    val line_total: String,
    val item_type: String? = null
)

@Serializable
data class PaymentDto(
    val id: Int,
    val amount: String,
    val date: String,
    val method: String?,
    val reference: String?
)

@Serializable
data class PlanDto(
    val id: Int,
    val plan_type: String,
    val months: Int,
    val monthly_amount: String,
    val start_date: String,
    val status: String
)

@Serializable
data class TripDto(
    val id: Int,
    val driver_id: Int,
    val status: String,
    val route_id: Int? = null
)

@Serializable
data class UpsellResponse(
    val success: Boolean,
    val order_id: Int,
    val message: String,
    val new_total: String,
    val order: OrderDto? = null
)

// UID Inventory DTOs
@Serializable
data class InventoryConfigResponse(
    val uid_inventory_enabled: Boolean,
    val uid_scan_required_after_pod: Boolean,
    val inventory_mode: String // "off" | "optional" | "required"
)

@Serializable
data class UIDScanRequest(
    val order_id: Int,
    val action: String, // "LOAD_OUT" | "DELIVER" | "RETURN" | "REPAIR" | "SWAP" | "LOAD_IN" | "ISSUE"
    val uid: String,
    val sku_id: Int? = null, // Optional if UID already exists
    val notes: String? = null
)

@Serializable
data class UIDScanResponse(
    val success: Boolean,
    val message: String,
    val uid: String,
    val action: String,
    val sku_name: String? = null,
    val order_item_id: Int? = null
)

@Serializable
data class LorryStockItem(
    @SerialName("sku_id") val skuId: Int,
    @SerialName("sku_name") val skuName: String,
    @SerialName("expected_count") val expectedCount: Int,
    @SerialName("scanned_count") val scannedCount: Int? = null,
    val variance: Int? = null
)

@Serializable
data class LorryStockResponse(
    val date: String,
    @SerialName("driver_id") val driverId: Int,
    val items: List<LorryStockItem> = emptyList(),
    @SerialName("total_expected") val totalExpected: Int = 0,
    @SerialName("total_scanned") val totalScanned: Int = 0,
    @SerialName("total_variance") val totalVariance: Int = 0
)

@Serializable
data class SKUResolveRequest(
    val name: String,
    val threshold: Double = 0.8
)

@Serializable
data class SKUMatch(
    val sku_id: Int,
    val sku_name: String,
    val confidence: Double,
    val match_type: String // "exact" | "alias" | "fuzzy"
)

@Serializable
data class SKUResolveResponse(
    val matches: List<SKUMatch>,
    val suggestions: List<String> = emptyList()
)

@Serializable
data class LorryStockUploadItem(
    val sku_id: Int,
    val scanned_count: Int
)

@Serializable
data class LorryStockUploadRequest(
    val date: String,
    val items: List<LorryStockUploadItem>,
    val notes: String? = null
)

// Lorry Management DTOs
@Serializable
data class LorryAssignmentResponse(
    val id: Int,
    val lorry_id: String,
    val assignment_date: String,
    val status: String,
    val stock_verified: Boolean,
    val stock_verified_at: String? = null,
    val shift_id: Int? = null,
    val notes: String? = null
)

@Serializable
data class MyAssignmentResponse(
    val message: String? = null,
    val assignment: LorryAssignmentResponse? = null
)

@Serializable
data class ClockInWithStockRequest(
    val lat: Double,
    val lng: Double,
    val location_name: String? = null,
    val scanned_uids: List<String>
)

@Serializable
data class ClockInResponse(
    val shift_id: Int,
    val clock_in_at: String,
    val assignment_id: Int,
    val lorry_id: String,
    val stock_verification_required: Boolean,
    val stock_verification_completed: Boolean,
    val variance_detected: Boolean,
    val message: String
)

@Serializable
data class AssignmentStatus(
    val has_assignment: Boolean,
    val stock_verified: Boolean,
    val lorry_id: String? = null
)

@Serializable
data class DriverStatusResponse(
    val can_access_orders: Boolean,
    val has_active_holds: Boolean,
    val hold_reasons: List<String>,
    val assignment_status: AssignmentStatus,
    val message: String
)

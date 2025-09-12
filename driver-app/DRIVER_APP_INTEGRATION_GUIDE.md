# Driver App Integration Guide - Unified Inventory System

This guide details the integration points needed to align the Android driver app with the unified event-sourced inventory system.

## 📋 Overview

The backend has been unified so both inventory endpoints now use the same event-sourced truth. The Android app needs minimal changes to leverage this and implement proper hold gating.

## 🔧 Applied Patches

### ✅ Patch 1: DriverApi.kt Updates
**File**: `driver-app/app/src/main/java/com/yourco/driverAA/data/api/DriverApi.kt`

**Changes Made**:
- Added missing `@GET("inventory/drivers/{driver_id}/stock-status")` endpoint
- Added DTOs: `StockStatusResponse`, `StockItemEntry`, `StockStatusSku`, `DriverHold`
- Added `MyAssignmentEnvelope` for proper response unwrapping

**Key New DTOs**:
```kotlin
@Serializable
data class StockStatusResponse(
    val driver_id: Int,
    val lorry_id: String? = null,
    val stock_items: List<StockStatusSku> = emptyList(),
    val total_items: Int = 0,
    val total_expected: Int = 0,
    val total_scanned: Int = 0,
    val total_variance: Int = 0,
    val holds: List<DriverHold> = emptyList(),
    val message: String? = null
)
```

### ✅ Patch 2: JobsRepository.kt Updates  
**File**: `driver-app/app/src/main/java/com/yourco/driverAA/domain/JobsRepository.kt`

**Changes Made**:
- Added `getTodayLorryStock()` - automatically uses today's date in ISO format
- Added `getDriverHolds()` - alias for `getDriverStatus()` for semantic clarity
- Added `getStockStatusFor(date: String)` - fetches stock status with variance/holds info

**New Helper Functions**:
```kotlin
suspend fun getTodayLorryStock(): Result<LorryStockResponse>
suspend fun getDriverHolds(): Result<DriverStatusResponse> 
suspend fun getStockStatusFor(date: String): Result<StockStatusResponse>
```

## 🎯 UI Integration Points

### A) Home/Main Screen - Hold Gating
**Location**: Main activity or home fragment

**Implementation**:
```kotlin
// In your home screen's ViewModel or activity
lifecycleScope.launch {
    val holdsResult = jobsRepository.getDriverHolds()
    if (holdsResult is Result.Success) {
        val status = holdsResult.data
        if (status.has_active_holds) {
            // Show blocking banner
            showHoldBanner(status.hold_reasons.joinToString(", "))
            // Disable navigation to job actions
            disableJobActions()
        } else {
            // Enable normal operations
            enableJobActions()
        }
    }
}

private fun showHoldBanner(reasons: String) {
    // Show warning banner: 
    // "⚠️ Morning stock verification pending: $reasons"
    // "Please complete verification; ops must release hold."
}
```

### B) Morning Stock Verification Screen
**Location**: Stock verification activity/fragment

**Implementation**:
```kotlin
class MorningVerificationViewModel @Inject constructor(
    private val jobsRepository: JobsRepository
) : ViewModel() {
    
    fun loadTodayData() {
        viewModelScope.launch {
            // Fetch assignment and stock in parallel
            val assignmentDeferred = async { jobsRepository.getMyLorryAssignment() }
            val stockDeferred = async { jobsRepository.getTodayLorryStock() }
            
            val assignment = assignmentDeferred.await()
            val stock = stockDeferred.await()
            
            // Update UI with lorry assignment and expected stock
            _uiState.value = VerificationUiState(
                assignment = assignment.getOrNull(),
                expectedStock = stock.getOrNull(),
                isLoading = false
            )
        }
    }
    
    fun checkHoldStatus() {
        viewModelScope.launch {
            val holdsResult = jobsRepository.getDriverHolds()
            if (holdsResult is Result.Success) {
                val hasHolds = holdsResult.data.has_active_holds
                _holdReleased.value = !hasHolds
                
                if (!hasHolds) {
                    // Navigate back to main screen - holds cleared
                    navigationManager.navigateToHome()
                }
            }
        }
    }
}
```

## 📅 Date-Scoped Operations

### Automatic Date Handling
The system now requires explicit dates for stock operations to prevent timezone drift:

```kotlin
// ✅ Good - uses today automatically  
val stock = jobsRepository.getTodayLorryStock()

// ✅ Good - explicit date for historical data
val stockStatus = jobsRepository.getStockStatusFor("2025-01-15") 

// ❌ Bad - old approach without date (would fail)
// val stock = jobsRepository.getLorryStock() // No date parameter
```

### Backend Alignment
- `/driver/inventory/lorry/{driver_id}/stock?date=YYYY-MM-DD` (required date)
- `/inventory/drivers/{driver_id}/stock-status?date=YYYY-MM-DD` (required date)
- Both endpoints now use the same event-sourced truth → **no more disagreements**

## 🚫 Hold Gating Flow

### 1. Check Driver Status
```kotlin
val status = jobsRepository.getDriverHolds().getOrThrow()
```

### 2. Gate Based on Holds
```kotlin
if (status.has_active_holds) {
    // Block job actions, show:
    status.hold_reasons.forEach { reason ->
        when (reason) {
            "STOCK_VARIANCE" -> "Morning stock verification pending"
            "INVESTIGATION" -> "Under investigation - contact operations"
            else -> reason
        }
    }
} else {
    // Enable normal operations
}
```

### 3. Server-Side Release
Hold release is handled server-side by operations. The app just polls `getDriverHolds()` to detect when holds are cleared.

## 🔄 No Changes Needed

### OfflineJobsRepository / SyncManager
**Why No Changes**: Your existing offline queue already posts UID scans via `inventory/uid/scan` and syncs when online. This flows directly into the backend's unified `LorryInventoryService.process_delivery_actions()` pipeline - no additional client logic needed.

### Existing Workflows
- UID scanning: Already queued and synced ✅
- Order status updates: Already handled ✅  
- Photo uploads: Already working ✅
- Offline support: Already robust ✅

## 🧪 Testing Checklist

### Backend Validation
1. **Both endpoints agree**: 
   - GET `/driver/inventory/lorry/2/stock?date=2025-01-15` 
   - GET `/inventory/drivers/2/stock-status?date=2025-01-15`
   - Should return same `total_expected` counts

2. **Date requirement enforced**:
   - Try calling endpoints without `?date=` → should get 400 error

3. **Hold gating works**:
   - Create morning stock variance → driver gets hold
   - Admin releases hold → driver can work again

### Mobile App Testing  
1. **Hold banner appears** when `has_active_holds = true`
2. **Job actions disabled** during holds
3. **Morning verification** shows expected vs scanned counts
4. **Date handling** works automatically with `getTodayLorryStock()`

## 🚀 Migration Benefits

### Consistency
- **Before**: Lorry endpoint showed 4 UIDs, stock-status showed 0
- **After**: Both endpoints show same counts (event-sourced truth)

### Safety
- Driver scans now require valid lorry assignment (no pseudo-lorries)
- DELIVER actions validate UID is actually in the lorry first
- SWAP operations create both DELIVERY + COLLECTION events

### Performance  
- KL timezone boundaries prevent day-drift issues
- Window functions replace Python loops for UID state calculation
- Proper database indexes can be used (no more `func.date()` casts)

## 📱 Example UI Flow

```
1. App Launch
   ↓
2. Check Driver Status
   ├─ has_active_holds = true → Show Hold Banner + Block Actions
   ├─ has_active_holds = false → Enable Normal Operations
   ↓
3. Morning Verification (if needed)
   ├─ Fetch Today's Assignment + Expected Stock  
   ├─ Driver Scans Items
   ├─ Upload Verification
   ├─ Poll Hold Status Until Released
   ↓
4. Normal Operations Enabled
```

This integration maintains your existing offline-first architecture while adding the necessary hold gating and date-scoped operations for the unified inventory system.
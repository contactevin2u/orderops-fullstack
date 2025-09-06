# Offline-First Driver App Architecture Plan

## Database Schema Enhancement

### Core Tables (Room Database)

```kotlin
// Jobs table - stores all assigned jobs locally
@Entity(tableName = "jobs")
data class JobEntity(
    @PrimaryKey val id: String,
    val code: String?,
    val status: String,
    val customerName: String?,
    val customerPhone: String?,
    val address: String?,
    val deliveryDate: String?,
    val notes: String?,
    val total: String?,
    val paidAmount: String?,
    val balance: String?,
    val type: String?,
    val items: String, // JSON serialized items
    val commission: String?, // JSON serialized commission
    val syncStatus: String = "SYNCED", // SYNCED, PENDING, FAILED
    val lastModified: Long = System.currentTimeMillis()
)

// Outbox table - stores all offline operations
@Entity(tableName = "outbox")
data class OutboxEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val operation: String, // UPDATE_STATUS, UPLOAD_POD, SCAN_UID, etc.
    val entityId: String, // Job ID, Order ID, etc.
    val payload: String, // JSON payload for the operation
    val endpoint: String, // API endpoint to call
    val httpMethod: String, // POST, PATCH, etc.
    val retryCount: Int = 0,
    val maxRetries: Int = 5,
    val nextRetryAt: Long = System.currentTimeMillis(),
    val status: String = "PENDING", // PENDING, PROCESSING, COMPLETED, FAILED
    val createdAt: Long = System.currentTimeMillis(),
    val lastAttemptAt: Long? = null,
    val errorMessage: String? = null
)

// Photos table - stores POD photos for offline upload
@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val orderId: String,
    val localPath: String,
    val photoNumber: Int,
    val uploadStatus: String = "PENDING", // PENDING, UPLOADING, UPLOADED, FAILED
    val remoteUrl: String? = null,
    val createdAt: Long = System.currentTimeMillis()
)

// UID Scans table - stores inventory scans for offline sync
@Entity(tableName = "uid_scans")
data class UIDScanEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val orderId: Int,
    val action: String,
    val uid: String,
    val skuId: Int?,
    val notes: String?,
    val syncStatus: String = "PENDING",
    val createdAt: Long = System.currentTimeMillis()
)

// Sync log table - tracks sync operations
@Entity(tableName = "sync_log")
data class SyncLogEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val operation: String,
    val entityType: String,
    val entityId: String,
    val success: Boolean,
    val errorMessage: String?,
    val timestamp: Long = System.currentTimeMillis()
)
```

## Repository Pattern with Offline Support

```kotlin
@Singleton
class OfflineJobsRepository @Inject constructor(
    private val api: DriverApi,
    private val jobsDao: JobsDao,
    private val outboxDao: OutboxDao,
    private val photosDao: PhotosDao,
    private val syncManager: SyncManager,
    private val connectivityManager: ConnectivityManager
) {
    
    // Always return local data first, sync in background
    fun getJobs(statusFilter: String = "active"): Flow<List<JobDto>> = 
        jobsDao.getJobsByStatus(statusFilter)
            .map { entities -> entities.map { it.toDto() } }
            .onStart { 
                // Trigger background sync if online
                if (connectivityManager.isOnline()) {
                    syncManager.syncJobs()
                }
            }
    
    // Update job status offline-first
    suspend fun updateOrderStatus(orderId: String, status: String): Result<JobDto> {
        return try {
            // Update local database immediately
            jobsDao.updateJobStatus(orderId, status, "PENDING")
            
            // Queue for background sync
            val operation = OutboxEntity(
                operation = "UPDATE_STATUS",
                entityId = orderId,
                payload = Json.encodeToString(OrderStatusUpdateDto(status)),
                endpoint = "drivers/orders/$orderId",
                httpMethod = "PATCH"
            )
            outboxDao.insert(operation)
            
            // Return updated local data
            val updatedJob = jobsDao.getJobById(orderId)?.toDto()
            Result.Success(updatedJob ?: throw Exception("Job not found"))
        } catch (e: Exception) {
            Result.error(e, "update_status")
        }
    }
    
    // Upload POD photo with offline support
    suspend fun uploadPodPhoto(orderId: String, photoFile: File, photoNumber: Int): Result<String> {
        return try {
            // Store photo locally immediately
            val photoEntity = PhotoEntity(
                orderId = orderId,
                localPath = photoFile.absolutePath,
                photoNumber = photoNumber
            )
            photosDao.insert(photoEntity)
            
            // Queue for upload when online
            val operation = OutboxEntity(
                operation = "UPLOAD_POD",
                entityId = orderId,
                payload = Json.encodeToString(mapOf(
                    "photoId" to photoEntity.id,
                    "photoNumber" to photoNumber
                )),
                endpoint = "drivers/orders/$orderId/pod-photo",
                httpMethod = "POST"
            )
            outboxDao.insert(operation)
            
            Result.Success("Photo queued for upload")
        } catch (e: Exception) {
            Result.error(e, "upload_photo")
        }
    }
}
```

## Sync Manager with Conflict Resolution

```kotlin
@Singleton
class SyncManager @Inject constructor(
    private val api: DriverApi,
    private val outboxDao: OutboxDao,
    private val jobsDao: JobsDao,
    private val photosDao: PhotosDao,
    private val connectivityManager: ConnectivityManager
) {
    
    suspend fun syncAll() {
        if (!connectivityManager.isOnline()) return
        
        try {
            // 1. Download latest jobs from server
            syncJobsFromServer()
            
            // 2. Process outbox operations
            processOutboxOperations()
            
            // 3. Upload pending photos
            uploadPendingPhotos()
            
        } catch (e: Exception) {
            Log.e("SyncManager", "Sync failed", e)
        }
    }
    
    private suspend fun processOutboxOperations() {
        val pendingOperations = outboxDao.getPendingOperations()
        
        pendingOperations.forEach { operation ->
            if (operation.nextRetryAt <= System.currentTimeMillis()) {
                try {
                    when (operation.operation) {
                        "UPDATE_STATUS" -> executeStatusUpdate(operation)
                        "UPLOAD_POD" -> executePhotoUpload(operation)
                        "SCAN_UID" -> executeUIDScan(operation)
                        // Add more operations as needed
                    }
                } catch (e: Exception) {
                    handleOperationFailure(operation, e)
                }
            }
        }
    }
    
    private suspend fun executeStatusUpdate(operation: OutboxEntity) {
        val update = Json.decodeFromString<OrderStatusUpdateDto>(operation.payload)
        val response = api.updateOrderStatus(operation.entityId, update)
        
        // Update local job with server response
        val jobEntity = response.toEntity().copy(syncStatus = "SYNCED")
        jobsDao.update(jobEntity)
        
        // Mark operation as completed
        outboxDao.markCompleted(operation.id)
    }
    
    private suspend fun handleOperationFailure(operation: OutboxEntity, error: Exception) {
        val updatedOperation = operation.copy(
            retryCount = operation.retryCount + 1,
            lastAttemptAt = System.currentTimeMillis(),
            errorMessage = error.message,
            nextRetryAt = calculateNextRetry(operation.retryCount),
            status = if (operation.retryCount >= operation.maxRetries) "FAILED" else "PENDING"
        )
        outboxDao.update(updatedOperation)
    }
    
    private fun calculateNextRetry(retryCount: Int): Long {
        // Exponential backoff: 1min, 2min, 4min, 8min, 16min
        val delayMinutes = (2.0.pow(retryCount.toDouble())).toLong()
        return System.currentTimeMillis() + (delayMinutes * 60 * 1000)
    }
}
```

## Background Sync Worker

```kotlin
@HiltWorker
class SyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted workerParams: WorkerParameters,
    private val syncManager: SyncManager,
    private val connectivityManager: ConnectivityManager
) : CoroutineWorker(context, workerParams) {

    override suspend fun doWork(): Result {
        return try {
            if (connectivityManager.isOnline()) {
                syncManager.syncAll()
                Result.success()
            } else {
                Result.retry() // Retry when connectivity is restored
            }
        } catch (e: Exception) {
            Log.e("SyncWorker", "Background sync failed", e)
            Result.retry()
        }
    }

    @AssistedFactory
    interface Factory {
        fun create(context: Context, workerParams: WorkerParameters): SyncWorker
    }
}
```

## UI State Management for Offline

```kotlin
data class OfflineUiState(
    val isOnline: Boolean = true,
    val pendingSyncCount: Int = 0,
    val lastSyncTime: Long? = null,
    val syncInProgress: Boolean = false,
    val syncErrors: List<String> = emptyList()
)

@HiltViewModel
class OfflineJobsViewModel @Inject constructor(
    private val repository: OfflineJobsRepository,
    private val connectivityManager: ConnectivityManager,
    private val outboxDao: OutboxDao
) : ViewModel() {
    
    val uiState = combine(
        connectivityManager.isOnlineFlow(),
        outboxDao.getPendingCount(),
        outboxDao.getLastSyncTime()
    ) { isOnline, pendingCount, lastSync ->
        OfflineUiState(
            isOnline = isOnline,
            pendingSyncCount = pendingCount,
            lastSyncTime = lastSync
        )
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = OfflineUiState()
    )
}
```

## Implementation Strategy

### Phase 1: Database Enhancement (Week 1)
- ✅ Extend Room database with offline tables
- ✅ Create DAOs for all entities
- ✅ Add migration scripts for existing database

### Phase 2: Repository Pattern (Week 2)
- ✅ Implement offline-first repositories
- ✅ Add local data caching for all operations
- ✅ Create outbox pattern for operations

### Phase 3: Sync Manager (Week 3)
- ✅ Build comprehensive sync engine
- ✅ Add conflict resolution logic
- ✅ Implement exponential backoff retry

### Phase 4: Background Workers (Week 4)
- ✅ Create WorkManager sync jobs
- ✅ Add connectivity change listeners
- ✅ Implement periodic sync scheduling

### Phase 5: UI Integration (Week 5)
- ✅ Add offline indicators to UI
- ✅ Show pending operations count
- ✅ Display sync status and errors

### Phase 6: Testing & Optimization (Week 6)
- ✅ Test offline scenarios extensively
- ✅ Optimize database performance
- ✅ Add comprehensive error handling

## Key Benefits

1. **True Offline Operation**: All critical functions work without internet
2. **Immediate UI Feedback**: Users see changes instantly
3. **Automatic Sync**: Background synchronization when online
4. **Conflict Resolution**: Handle data conflicts intelligently
5. **Reliable**: Exponential backoff and retry mechanisms
6. **User-Friendly**: Clear offline status indicators

## Technical Considerations

- **Storage**: SQLite can handle large datasets efficiently
- **Battery**: Use WorkManager for battery-optimized sync
- **Data Usage**: Sync only necessary data to minimize bandwidth
- **Security**: Encrypt sensitive data in local database
- **Performance**: Use database indexes and efficient queries
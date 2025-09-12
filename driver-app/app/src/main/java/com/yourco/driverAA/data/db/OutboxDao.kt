package com.yourco.driverAA.data.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface OutboxDao {
    @Query("SELECT * FROM outbox WHERE status = 'PENDING' AND nextRetryAt <= :currentTime ORDER BY priority ASC, createdAt ASC")
    suspend fun getPendingOperations(currentTime: Long = System.currentTimeMillis()): List<OutboxEntity>
    
    @Query("SELECT * FROM outbox WHERE status = :status ORDER BY createdAt DESC")
    suspend fun getOperationsByStatus(status: String): List<OutboxEntity>
    
    @Query("SELECT * FROM outbox ORDER BY createdAt DESC LIMIT 100")
    suspend fun getRecentOperations(): List<OutboxEntity>
    
    @Query("SELECT COUNT(*) FROM outbox WHERE status = 'PENDING'")
    fun getPendingCount(): Flow<Int>
    
    @Query("SELECT COUNT(*) FROM outbox WHERE status = 'FAILED'")
    fun getFailedCount(): Flow<Int>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(operation: OutboxEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(operations: List<OutboxEntity>)
    
    @Update
    suspend fun update(operation: OutboxEntity)
    
    @Query("UPDATE outbox SET status = 'COMPLETED' WHERE id = :id")
    suspend fun markCompleted(id: String)
    
    @Query("UPDATE outbox SET status = 'FAILED', errorMessage = :error WHERE id = :id")
    suspend fun markFailed(id: String, error: String)
    
    @Query("UPDATE outbox SET retryCount = retryCount + 1, lastAttemptAt = :timestamp, nextRetryAt = :nextRetry, errorMessage = :error WHERE id = :id")
    suspend fun incrementRetry(id: String, timestamp: Long, nextRetry: Long, error: String?)
    
    @Delete
    suspend fun delete(operation: OutboxEntity)
    
    @Query("DELETE FROM outbox WHERE id = :id")
    suspend fun deleteById(id: String)
    
    @Query("DELETE FROM outbox WHERE status = 'COMPLETED' AND createdAt < :olderThan")
    suspend fun deleteCompletedOlderThan(olderThan: Long)
    
    @Query("DELETE FROM outbox WHERE status = 'FAILED' AND retryCount >= maxRetries AND createdAt < :olderThan")
    suspend fun deleteFailedOlderThan(olderThan: Long)
    
    @Query("SELECT MAX(createdAt) FROM outbox WHERE status = 'COMPLETED'")
    fun getLastSyncTime(): Flow<Long?>
    
    @Query("DELETE FROM outbox")
    suspend fun deleteAll()
}
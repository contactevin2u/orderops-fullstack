package com.yourco.driverAA.data.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface UIDScansDao {
    @Query("SELECT * FROM uid_scans WHERE orderId = :orderId ORDER BY createdAt DESC")
    fun getScansForOrder(orderId: Int): Flow<List<UIDScanEntity>>
    
    @Query("SELECT * FROM uid_scans WHERE syncStatus = :status ORDER BY createdAt ASC")
    suspend fun getScansBySyncStatus(status: String): List<UIDScanEntity>
    
    @Query("SELECT * FROM uid_scans WHERE syncStatus = 'PENDING' ORDER BY createdAt ASC")
    suspend fun getPendingScans(): List<UIDScanEntity>
    
    @Query("SELECT COUNT(*) FROM uid_scans WHERE syncStatus = 'PENDING'")
    fun getPendingScansCount(): Flow<Int>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(scan: UIDScanEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(scans: List<UIDScanEntity>)
    
    @Update
    suspend fun update(scan: UIDScanEntity)
    
    @Query("UPDATE uid_scans SET syncStatus = :status, syncedAt = :syncedAt WHERE id = :id")
    suspend fun updateSyncStatus(id: String, status: String, syncedAt: Long?)
    
    @Query("UPDATE uid_scans SET syncStatus = 'FAILED', errorMessage = :error WHERE id = :id")
    suspend fun markSyncFailed(id: String, error: String)
    
    @Delete
    suspend fun delete(scan: UIDScanEntity)
    
    @Query("DELETE FROM uid_scans WHERE id = :id")
    suspend fun deleteById(id: String)
    
    @Query("DELETE FROM uid_scans WHERE syncStatus = 'SYNCED' AND createdAt < :olderThan")
    suspend fun deleteSyncedOlderThan(olderThan: Long)
}
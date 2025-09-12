package com.yourco.driverAA.data.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface PhotosDao {
    @Query("SELECT * FROM photos WHERE orderId = :orderId ORDER BY photoNumber ASC")
    fun getPhotosForOrder(orderId: String): Flow<List<PhotoEntity>>
    
    @Query("SELECT * FROM photos WHERE uploadStatus = :status ORDER BY createdAt ASC")
    suspend fun getPhotosByUploadStatus(status: String): List<PhotoEntity>
    
    @Query("SELECT * FROM photos WHERE uploadStatus = 'PENDING' ORDER BY createdAt ASC")
    suspend fun getPendingPhotos(): List<PhotoEntity>
    
    @Query("SELECT COUNT(*) FROM photos WHERE uploadStatus = 'PENDING'")
    fun getPendingPhotosCount(): Flow<Int>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(photo: PhotoEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(photos: List<PhotoEntity>)
    
    @Update
    suspend fun update(photo: PhotoEntity)
    
    @Query("UPDATE photos SET uploadStatus = :status, uploadedAt = :uploadedAt, remoteUrl = :remoteUrl WHERE id = :id")
    suspend fun updateUploadStatus(id: String, status: String, uploadedAt: Long?, remoteUrl: String?)
    
    @Query("UPDATE photos SET uploadStatus = 'FAILED', errorMessage = :error WHERE id = :id")
    suspend fun markUploadFailed(id: String, error: String)
    
    @Delete
    suspend fun delete(photo: PhotoEntity)
    
    @Query("DELETE FROM photos WHERE id = :id")
    suspend fun deleteById(id: String)
    
    @Query("DELETE FROM photos WHERE uploadStatus = 'UPLOADED' AND createdAt < :olderThan")
    suspend fun deleteUploadedOlderThan(olderThan: Long)
    
    @Query("DELETE FROM photos")
    suspend fun deleteAll()
}
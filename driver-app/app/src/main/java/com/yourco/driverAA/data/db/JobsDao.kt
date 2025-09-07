package com.yourco.driverAA.data.db

import androidx.room.*
import kotlinx.coroutines.flow.Flow

@Dao
interface JobsDao {
    @Query("SELECT * FROM jobs WHERE status IN ('assigned', 'in_transit', 'on_hold') ORDER BY lastModified DESC")
    fun getActiveJobs(): Flow<List<JobEntity>>
    
    @Query("SELECT * FROM jobs WHERE status = :status ORDER BY lastModified DESC")
    fun getJobsByStatus(status: String): Flow<List<JobEntity>>
    
    @Query("SELECT * FROM jobs ORDER BY lastModified DESC")
    fun getAllJobs(): Flow<List<JobEntity>>
    
    @Query("SELECT * FROM jobs WHERE id = :id")
    suspend fun getJobById(id: String): JobEntity?
    
    @Query("SELECT * FROM jobs WHERE syncStatus = :syncStatus")
    suspend fun getJobsBySyncStatus(syncStatus: String): List<JobEntity>
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(job: JobEntity)
    
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(jobs: List<JobEntity>)
    
    @Update
    suspend fun update(job: JobEntity)
    
    @Query("UPDATE jobs SET status = :status, syncStatus = :syncStatus, lastModified = :timestamp WHERE id = :id")
    suspend fun updateJobStatus(id: String, status: String, syncStatus: String, timestamp: Long = System.currentTimeMillis())
    
    @Query("UPDATE jobs SET syncStatus = :syncStatus WHERE id = :id")
    suspend fun updateSyncStatus(id: String, syncStatus: String)
    
    @Delete
    suspend fun delete(job: JobEntity)
    
    @Query("DELETE FROM jobs WHERE id = :id")
    suspend fun deleteById(id: String)
    
    @Query("DELETE FROM jobs")
    suspend fun deleteAll()
    
    @Query("SELECT COUNT(*) FROM jobs WHERE syncStatus = 'PENDING'")
    fun getPendingSyncCount(): Flow<Int>
}
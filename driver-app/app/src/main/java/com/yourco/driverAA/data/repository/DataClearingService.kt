package com.yourco.driverAA.data.repository

import com.yourco.driverAA.data.db.AppDatabase
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DataClearingService @Inject constructor(
    private val database: AppDatabase
) {
    
    /**
     * Clear all local data when switching drivers to prevent data leakage
     * This ensures each driver only sees their own orders and data
     */
    suspend fun clearAllLocalData() {
        try {
            // Clear all job data
            database.jobsDao().deleteAll()
            
            // Clear all outbox pending requests 
            database.outboxDao().deleteAll()
            
            // Clear all stored photos
            database.photosDao().deleteAll()
            
            // Clear all UID scans
            database.uidScansDao().deleteAll()
            
            // Clear all location pings
            database.locationDao().deleteAll()
            
            println("✅ Successfully cleared all local data for driver switch")
            
        } catch (e: Exception) {
            println("⚠️ Error clearing local data: ${e.message}")
            throw e
        }
    }
    
    /**
     * Clear data for a specific driver (if we tracked driver IDs in entities)
     * Currently not implemented as entities don't track driver ownership
     */
    suspend fun clearDataForDriver(driverId: Int) {
        // TODO: Implement when we add driver_id to entities
        // For now, we clear all data since we can't differentiate
        clearAllLocalData()
    }
}
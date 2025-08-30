package com.yourco.driverAA.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [LocationPing::class], 
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun locationDao(): LocationPingDao
}


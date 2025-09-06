package com.yourco.driverAA.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        LocationPing::class,
        JobEntity::class,
        OutboxEntity::class,
        PhotoEntity::class,
        UIDScanEntity::class
    ], 
    version = 2,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun locationDao(): LocationPingDao
    abstract fun jobsDao(): JobsDao
    abstract fun outboxDao(): OutboxDao
    abstract fun photosDao(): PhotosDao
    abstract fun uidScansDao(): UIDScansDao
}


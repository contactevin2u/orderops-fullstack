package com.orderops.driver.data.db

import androidx.room.Dao
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.PrimaryKey
import androidx.room.Query

@Entity
data class LocationPing(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val lat: Double,
    val lng: Double,
    val accuracy: Float,
    val speed: Float,
    val ts: Long,
    val uploaded: Boolean = false
)

@Dao
interface LocationPingDao {
    @Insert
    suspend fun insert(ping: LocationPing)

    @Query("SELECT * FROM LocationPing WHERE uploaded = 0")
    suspend fun pending(): List<LocationPing>

    @Query("UPDATE LocationPing SET uploaded = 1 WHERE id IN (:ids)")
    suspend fun markUploaded(ids: List<Long>)
}

package com.yourco.driverAA.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(tableName = "uid_scans")
data class UIDScanEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val orderId: Int,
    val action: String, // LOAD_OUT, DELIVER, RETURN, REPAIR, SWAP, LOAD_IN, ISSUE
    val uid: String,
    val skuId: Int?,
    val notes: String?,
    val syncStatus: String = "PENDING", // PENDING, SYNCED, FAILED
    val createdAt: Long = System.currentTimeMillis(),
    val syncedAt: Long? = null,
    val errorMessage: String? = null
)
package com.yourco.driverAA.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(tableName = "outbox")
data class OutboxEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val operation: String, // UPDATE_STATUS, UPLOAD_POD, SCAN_UID, CLOCK_IN, CLOCK_OUT, etc.
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
    val errorMessage: String? = null,
    val priority: Int = 1 // 1 = high (status updates), 2 = medium (photos), 3 = low (analytics)
)
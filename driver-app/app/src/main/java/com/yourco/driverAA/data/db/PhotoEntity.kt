package com.yourco.driverAA.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import java.util.UUID

@Entity(tableName = "photos")
data class PhotoEntity(
    @PrimaryKey val id: String = UUID.randomUUID().toString(),
    val orderId: String,
    val localPath: String,
    val photoNumber: Int,
    val uploadStatus: String = "PENDING", // PENDING, UPLOADING, UPLOADED, FAILED
    val remoteUrl: String? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val uploadedAt: Long? = null,
    val errorMessage: String? = null,
    val fileSize: Long = 0L,
    val mimeType: String = "image/jpeg"
)
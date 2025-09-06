package com.yourco.driverAA.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.data.api.JobItemDto
import com.yourco.driverAA.data.api.CommissionDto
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json

@Entity(tableName = "jobs")
data class JobEntity(
    @PrimaryKey val id: String,
    val code: String?,
    val status: String?,
    val customerName: String?,
    val customerPhone: String?,
    val address: String?,
    val deliveryDate: String?,
    val notes: String?,
    val total: String?,
    val paidAmount: String?,
    val balance: String?,
    val type: String?, // OUTRIGHT | INSTALLMENT | RENTAL | MIXED
    val items: String?, // JSON serialized items
    val commission: String?, // JSON serialized commission
    val syncStatus: String = "SYNCED", // SYNCED, PENDING, FAILED
    val lastModified: Long = System.currentTimeMillis()
) {
    fun toDto(): JobDto {
        val itemsList = items?.let { 
            try {
                Json.decodeFromString<List<JobItemDto>>(it)
            } catch (e: Exception) {
                emptyList()
            }
        } ?: emptyList()
        
        val commissionData = commission?.let {
            try {
                Json.decodeFromString<CommissionDto>(it)
            } catch (e: Exception) {
                null
            }
        }
        
        return JobDto(
            id = id,
            code = code,
            status = status,
            customer_name = customerName,
            customer_phone = customerPhone,
            address = address,
            delivery_date = deliveryDate,
            notes = notes,
            total = total,
            paid_amount = paidAmount,
            balance = balance,
            type = type,
            items = itemsList,
            commission = commissionData
        )
    }
    
    companion object {
        fun fromDto(dto: JobDto): JobEntity {
            val itemsJson = dto.items?.let { Json.encodeToString(it) }
            val commissionJson = dto.commission?.let { Json.encodeToString(it) }
            
            return JobEntity(
                id = dto.id,
                code = dto.code,
                status = dto.status,
                customerName = dto.customer_name,
                customerPhone = dto.customer_phone,
                address = dto.address,
                deliveryDate = dto.delivery_date,
                notes = dto.notes,
                total = dto.total,
                paidAmount = dto.paid_amount,
                balance = dto.balance,
                type = dto.type,
                items = itemsJson,
                commission = commissionJson
            )
        }
    }
}
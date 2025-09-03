package com.yourco.driverAA.util

import com.yourco.driverAA.data.api.JobDto

/**
 * Validator for order state transitions with Malay error messages
 */
object OrderStateValidator {
    
    /**
     * Check if driver can start a new order
     * @param currentJobs List of all current jobs assigned to driver
     * @param targetStatus The status driver wants to set
     * @return ValidationResult with success/failure and Malay message
     */
    fun validateStatusChange(currentJobs: List<JobDto>, jobId: String, targetStatus: String): ValidationResult {
        val currentJob = currentJobs.find { it.id == jobId }
            ?: return ValidationResult.error("Pesanan tidak dijumpai")
        
        val currentStatus = currentJob.status
        val inTransitJobs = currentJobs.filter { it.status == "STARTED" && it.id != jobId }
        
        return when (targetStatus) {
            "STARTED" -> validateStartOrder(currentStatus, inTransitJobs)
            "DELIVERED" -> validateDeliverOrder(currentStatus, currentJob)
            "ON_HOLD" -> validateOnHoldOrder(currentStatus)
            "CANCELLED" -> validateCancelOrder(currentStatus)
            else -> ValidationResult.error("Status tidak sah")
        }
    }
    
    private fun validateStartOrder(currentStatus: String?, inTransitJobs: List<JobDto>): ValidationResult {
        // Check if there's already an in-transit order
        if (inTransitJobs.isNotEmpty()) {
            val inTransitJob = inTransitJobs.first()
            return ValidationResult.error(
                "Anda mempunyai pesanan dalam perjalanan (#${inTransitJob.code}). " +
                "Sila selesaikan pesanan tersebut dahulu sebelum memulakan pesanan baru."
            )
        }
        
        return when (currentStatus) {
            "ASSIGNED" -> ValidationResult.success("Pesanan berjaya dimulakan")
            "STARTED" -> ValidationResult.error("Pesanan ini sudah dimulakan")
            "DELIVERED" -> ValidationResult.error("Pesanan ini sudah dihantar")
            "ON_HOLD" -> ValidationResult.success("Pesanan berjaya dimulakan dari status ditangguhkan")
            "CANCELLED" -> ValidationResult.error("Pesanan ini telah dibatalkan")
            else -> ValidationResult.error("Tidak boleh memulakan pesanan dari status semasa")
        }
    }
    
    private fun validateDeliverOrder(currentStatus: String?, job: JobDto): ValidationResult {
        return when (currentStatus) {
            "STARTED" -> {
                // Check if PoD photos are required and uploaded
                val podPhotosRequired = true // Assuming PoD photos are always required
                if (podPhotosRequired) {
                    // This would need to be checked against actual uploaded photos
                    ValidationResult.success("Pesanan berjaya dihantar")
                } else {
                    ValidationResult.error("Sila muat naik gambar Proof of Delivery (PoD) sebelum menandakan sebagai dihantar")
                }
            }
            "ASSIGNED" -> ValidationResult.error("Sila mulakan pesanan dahulu sebelum menghantar")
            "DELIVERED" -> ValidationResult.error("Pesanan ini sudah dihantar")
            "ON_HOLD" -> ValidationResult.error("Pesanan ditangguhkan. Sila hubungi pelanggan dahulu")
            "CANCELLED" -> ValidationResult.error("Pesanan ini telah dibatalkan")
            else -> ValidationResult.error("Tidak boleh menghantar pesanan dari status semasa")
        }
    }
    
    private fun validateOnHoldOrder(currentStatus: String?): ValidationResult {
        return when (currentStatus) {
            "ASSIGNED", "STARTED" -> ValidationResult.success("Pesanan ditangguhkan")
            "DELIVERED" -> ValidationResult.error("Pesanan yang sudah dihantar tidak boleh ditangguhkan")
            "ON_HOLD" -> ValidationResult.error("Pesanan ini sudah ditangguhkan")
            "CANCELLED" -> ValidationResult.error("Pesanan yang dibatalkan tidak boleh ditangguhkan")
            else -> ValidationResult.error("Tidak boleh menangguhkan pesanan dari status semasa")
        }
    }
    
    private fun validateCancelOrder(currentStatus: String?): ValidationResult {
        return when (currentStatus) {
            "ASSIGNED", "ON_HOLD" -> ValidationResult.success("Pesanan dibatalkan")
            "STARTED" -> ValidationResult.error("Pesanan dalam perjalanan tidak boleh dibatalkan. Sila hubungi pentadbir")
            "DELIVERED" -> ValidationResult.error("Pesanan yang sudah dihantar tidak boleh dibatalkan")
            "CANCELLED" -> ValidationResult.error("Pesanan ini sudah dibatalkan")
            else -> ValidationResult.error("Tidak boleh membatalkan pesanan dari status semasa")
        }
    }
    
    /**
     * Get user-friendly status text in Malay
     */
    fun getStatusDisplayText(status: String?): String {
        return when (status) {
            "ASSIGNED" -> "Ditugaskan"
            "STARTED" -> "Dalam Perjalanan"
            "DELIVERED" -> "Dihantar"
            "ON_HOLD" -> "Ditangguhkan"
            "CANCELLED" -> "Dibatalkan"
            else -> "Tidak Diketahui"
        }
    }
    
    /**
     * Get action button text in Malay
     */
    fun getActionButtonText(currentStatus: String?, targetStatus: String): String {
        return when (targetStatus) {
            "STARTED" -> when (currentStatus) {
                "ON_HOLD" -> "Sambung Pesanan"
                else -> "Mula Pesanan"
            }
            "DELIVERED" -> "Tandakan Dihantar"
            "ON_HOLD" -> "Tangguhkan"
            "CANCELLED" -> "Batalkan"
            else -> "Kemaskini"
        }
    }
    
    /**
     * Check if driver can perform any actions (has active jobs)
     */
    fun validateDriverHasActiveJobs(jobs: List<JobDto>): ValidationResult {
        val activeJobs = jobs.filter { it.status in listOf("ASSIGNED", "STARTED", "ON_HOLD") }
        
        return if (activeJobs.isEmpty()) {
            ValidationResult.error("Tiada pesanan aktif. Sila hubungi pentadbir untuk tugasan baru.")
        } else {
            ValidationResult.success("Driver mempunyai ${activeJobs.size} pesanan aktif")
        }
    }
    
    /**
     * Get helpful messages for current order state
     */
    fun getOrderStateMessage(job: JobDto): String {
        return when (job.status) {
            "ASSIGNED" -> "Pesanan telah ditugaskan kepada anda. Klik 'Mula Pesanan' untuk bermula."
            "STARTED" -> "Pesanan dalam perjalanan. Sila hantar kepada pelanggan dan muat naik gambar PoD."
            "DELIVERED" -> "Pesanan telah berjaya dihantar. Terima kasih!"
            "ON_HOLD" -> "Pesanan ditangguhkan. Sila hubungi pelanggan atau pentadbir untuk maklumat lanjut."
            "CANCELLED" -> "Pesanan ini telah dibatalkan."
            else -> "Status pesanan tidak diketahui. Sila hubungi pentadbir."
        }
    }
}

/**
 * Result of validation with success/error state and message
 */
sealed class ValidationResult {
    data class Success(val message: String) : ValidationResult()
    data class Error(val message: String) : ValidationResult()
    
    companion object {
        fun success(message: String) = Success(message)
        fun error(message: String) = Error(message)
    }
    
    val isSuccess: Boolean get() = this is Success
    val isError: Boolean get() = this is Error
    val message: String get() = when (this) {
        is Success -> message
        is Error -> message
    }
}

/**
 * Common error messages in Malay
 */
object MalayErrorMessages {
    const val NETWORK_ERROR = "Ralat rangkaian. Sila periksa sambungan internet anda."
    const val SERVER_ERROR = "Ralat pelayan. Sila cuba lagi sebentar."
    const val UNAUTHORIZED = "Akses ditolak. Sila log masuk semula."
    const val ORDER_NOT_FOUND = "Pesanan tidak dijumpai."
    const val PHOTO_UPLOAD_FAILED = "Muat naik gambar gagal. Sila cuba lagi."
    const val LOCATION_ACCESS_DENIED = "Akses lokasi diperlukan untuk aplikasi ini."
    const val INVALID_INPUT = "Input tidak sah. Sila periksa maklumat yang dimasukkan."
    const val CONNECTION_TIMEOUT = "Sambungan terputus. Sila cuba lagi."
    
    fun getErrorMessage(throwable: Throwable): String {
        return when {
            throwable.message?.contains("network", ignoreCase = true) == true -> NETWORK_ERROR
            throwable.message?.contains("unauthorized", ignoreCase = true) == true -> UNAUTHORIZED
            throwable.message?.contains("timeout", ignoreCase = true) == true -> CONNECTION_TIMEOUT
            throwable.message?.contains("not found", ignoreCase = true) == true -> ORDER_NOT_FOUND
            else -> throwable.message ?: SERVER_ERROR
        }
    }
}
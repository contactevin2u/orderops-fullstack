package com.yourco.driverAA.util

import retrofit2.HttpException
import java.io.IOException
import java.net.SocketTimeoutException
import java.net.UnknownHostException

/**
 * Utility class for converting technical errors into user-friendly messages
 */
object ErrorHandler {
    
    /**
     * Convert a throwable into a user-friendly error message
     */
    fun getUserFriendlyMessage(throwable: Throwable): String {
        return when (throwable) {
            is HttpException -> getHttpErrorMessage(throwable)
            is IOException -> getNetworkErrorMessage(throwable)
            is UnknownHostException -> "No internet connection. Please check your network and try again."
            is SocketTimeoutException -> "Request timed out. Please check your connection and try again."
            else -> "Something went wrong. Please try again in a moment."
        }
    }
    
    /**
     * Handle HTTP errors with specific status codes
     */
    private fun getHttpErrorMessage(httpException: HttpException): String {
        return when (httpException.code()) {
            400 -> "Invalid request. Please check your input and try again."
            401 -> "Your session has expired. Please sign in again."
            403 -> "You don't have permission for this action. Contact your manager."
            404 -> "Information not found. It may have been removed or updated."
            409 -> "This action conflicts with existing data. Please refresh and try again."
            422 -> "Please check your input - some information appears to be incorrect."
            429 -> "Too many requests. Please wait a moment and try again."
            500, 502, 503, 504 -> "Server error. Please try again in a few moments."
            else -> "Unable to complete request. Please try again."
        }
    }
    
    /**
     * Handle network and connectivity errors
     */
    private fun getNetworkErrorMessage(ioException: IOException): String {
        return when {
            ioException.message?.contains("timeout", ignoreCase = true) == true -> 
                "Request timed out. Please check your connection and try again."
            ioException.message?.contains("network", ignoreCase = true) == true -> 
                "Network error. Please check your internet connection."
            else -> "Connection problem. Please check your internet and try again."
        }
    }
    
    /**
     * Get user-friendly error for specific operations
     */
    fun getOperationError(operation: String, throwable: Throwable): String {
        val baseMessage = when (operation) {
            "login" -> "Unable to sign in"
            "load_jobs" -> "Unable to load your jobs"
            "update_status" -> "Unable to update job status"
            "upload_photo" -> "Unable to upload photo"
            "submit_report" -> "Unable to submit your report"
            "load_earnings" -> "Unable to load your earnings"
            "accept_job" -> "Unable to accept this job"
            "complete_job" -> "Unable to mark job as complete"
            else -> "Unable to complete action"
        }
        
        val reason = when (throwable) {
            is HttpException -> when (throwable.code()) {
                401 -> "Your session has expired. Please sign in again."
                403 -> "You don't have permission for this action."
                404 -> "This job may have been removed or updated."
                409 -> "This job has been updated. Please refresh and try again."
                else -> "Please try again in a moment."
            }
            is IOException -> "Please check your internet connection."
            else -> "Please try again in a moment."
        }
        
        return "$baseMessage. $reason"
    }
    
    /**
     * Check if error requires immediate action (like re-login)
     */
    fun requiresReauth(throwable: Throwable): Boolean {
        return throwable is HttpException && throwable.code() == 401
    }
    
    /**
     * Check if error is recoverable (user can retry)
     */
    fun isRecoverable(throwable: Throwable): Boolean {
        return when (throwable) {
            is HttpException -> when (throwable.code()) {
                401, 403 -> false // Auth issues require intervention
                400, 422 -> false // Client errors need input changes
                else -> true // Server errors, network issues are recoverable
            }
            is IOException -> true // Network issues are recoverable
            else -> true // Unknown errors assumed recoverable
        }
    }
}
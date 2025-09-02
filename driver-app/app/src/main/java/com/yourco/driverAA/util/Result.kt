package com.yourco.driverAA.util

sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(
        val throwable: Throwable,
        val userMessage: String = ErrorHandler.getUserFriendlyMessage(throwable),
        val isRecoverable: Boolean = ErrorHandler.isRecoverable(throwable),
        val requiresReauth: Boolean = ErrorHandler.requiresReauth(throwable)
    ) : Result<Nothing>()
    object Loading : Result<Nothing>()
    
    companion object {
        fun <T> error(
            throwable: Throwable,
            operation: String? = null
        ): Result<T> {
            val message = operation?.let { 
                ErrorHandler.getOperationError(it, throwable) 
            } ?: ErrorHandler.getUserFriendlyMessage(throwable)
            
            return Error(
                throwable = throwable,
                userMessage = message,
                isRecoverable = ErrorHandler.isRecoverable(throwable),
                requiresReauth = ErrorHandler.requiresReauth(throwable)
            )
        }
    }
}

package com.yourco.driverAA.data.network

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ConnectivityManager @Inject constructor(
    private val context: Context
) {
    private val connectivityManager = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
    
    private val _isOnline = MutableStateFlow(checkInitialConnectivity())
    val isOnline: StateFlow<Boolean> = _isOnline.asStateFlow()
    
    private val networkCallback = object : ConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            _isOnline.value = true
        }
        
        override fun onLost(network: Network) {
            _isOnline.value = checkConnectivity()
        }
        
        override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
            val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
                             (networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                              networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                              networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
            _isOnline.value = hasInternet
        }
    }
    
    init {
        registerNetworkCallback()
    }
    
    private fun registerNetworkCallback() {
        try {
            val networkRequest = NetworkRequest.Builder()
                .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                // Remove NET_CAPABILITY_VALIDATED requirement - too strict
                .build()
            
            connectivityManager.registerNetworkCallback(networkRequest, networkCallback)
        } catch (e: Exception) {
            android.util.Log.e("ConnectivityManager", "Failed to register network callback", e)
        }
    }
    
    private fun checkInitialConnectivity(): Boolean = checkConnectivity()
    
    private fun checkConnectivity(): Boolean {
        return try {
            val activeNetwork = connectivityManager.activeNetwork ?: return false
            val networkCapabilities = connectivityManager.getNetworkCapabilities(activeNetwork) ?: return false
            
            // Less strict check - only require internet capability, not validation
            // This prevents false negatives when Android hasn't validated the connection yet
            networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) &&
            (networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
             networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
             networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET))
        } catch (e: Exception) {
            false
        }
    }
    
    fun isOnline(): Boolean = _isOnline.value
    
    fun isOnlineFlow(): StateFlow<Boolean> = isOnline
    
    fun unregisterCallback() {
        try {
            connectivityManager.unregisterNetworkCallback(networkCallback)
        } catch (e: Exception) {
            android.util.Log.e("ConnectivityManager", "Failed to unregister network callback", e)
        }
    }
}
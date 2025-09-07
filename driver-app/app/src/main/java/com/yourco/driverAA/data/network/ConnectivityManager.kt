package com.yourco.driverAA.data.network

import android.content.Context
import android.net.ConnectivityManager as SysConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ConnectivityManager @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val connectivityManager =
        context.getSystemService(Context.CONNECTIVITY_SERVICE) as SysConnectivityManager
    
    private val _isOnline = MutableStateFlow(checkInitialConnectivity())
    val isOnline: StateFlow<Boolean> = _isOnline.asStateFlow()
    
    private val networkCallback = object : SysConnectivityManager.NetworkCallback() {
        override fun onAvailable(network: Network) {
            android.util.Log.i("ConnectivityManager", "Network available: $network")
            _isOnline.value = true
            android.util.Log.i("ConnectivityManager", "Set isOnline = true")
        }
        
        override fun onLost(network: Network) {
            android.util.Log.i("ConnectivityManager", "Network lost: $network")
            val connected = checkConnectivity()
            _isOnline.value = connected
            android.util.Log.i("ConnectivityManager", "Set isOnline = $connected after network loss")
        }
        
        override fun onCapabilitiesChanged(network: Network, networkCapabilities: NetworkCapabilities) {
            val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            val hasTransport = networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                              networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                              networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
            val isConnected = hasInternet && hasTransport
            
            android.util.Log.i("ConnectivityManager", "Network capabilities changed - Internet: $hasInternet, Transport: $hasTransport, Result: $isConnected")
            _isOnline.value = isConnected
        }
    }
    
    init {
        android.util.Log.i("ConnectivityManager", "Initializing ConnectivityManager")
        android.util.Log.i("ConnectivityManager", "Initial connectivity check: ${checkInitialConnectivity()}")
        registerNetworkCallback()
    }
    
    private fun registerNetworkCallback() {
        try {
            android.util.Log.i("ConnectivityManager", "Attempting to register default network callback")
            // Use default network callback for better reliability on Android 10+
            connectivityManager.registerDefaultNetworkCallback(networkCallback)
            android.util.Log.i("ConnectivityManager", "Successfully registered default network callback")
        } catch (e: Exception) {
            android.util.Log.e("ConnectivityManager", "Failed to register default network callback", e)
            // Fallback for older Android versions
            try {
                android.util.Log.i("ConnectivityManager", "Attempting fallback network callback registration")
                val networkRequest = NetworkRequest.Builder()
                    .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
                    .build()
                connectivityManager.registerNetworkCallback(networkRequest, networkCallback)
                android.util.Log.i("ConnectivityManager", "Successfully registered fallback network callback")
            } catch (fallbackException: Exception) {
                android.util.Log.e("ConnectivityManager", "Fallback network callback also failed", fallbackException)
            }
        }
    }
    
    private fun checkInitialConnectivity(): Boolean = checkConnectivity()
    
    private fun checkConnectivity(): Boolean {
        return try {
            val activeNetwork = connectivityManager.activeNetwork
            android.util.Log.i("ConnectivityManager", "Active network: $activeNetwork")
            
            if (activeNetwork == null) {
                android.util.Log.w("ConnectivityManager", "No active network found")
                return false
            }
            
            val networkCapabilities = connectivityManager.getNetworkCapabilities(activeNetwork)
            android.util.Log.i("ConnectivityManager", "Network capabilities: $networkCapabilities")
            
            if (networkCapabilities == null) {
                android.util.Log.w("ConnectivityManager", "No network capabilities found")
                return false
            }
            
            val hasInternet = networkCapabilities.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            val hasWifi = networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)
            val hasCellular = networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) 
            val hasEthernet = networkCapabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
            val hasTransport = hasWifi || hasCellular || hasEthernet
            
            android.util.Log.i("ConnectivityManager", "Connectivity check - Internet: $hasInternet, WiFi: $hasWifi, Cellular: $hasCellular, Ethernet: $hasEthernet")
            
            // Less strict check - only require internet capability, not validation
            // This prevents false negatives when Android hasn't validated the connection yet
            val result = hasInternet && hasTransport
            android.util.Log.i("ConnectivityManager", "Connectivity result: $result")
            result
        } catch (e: Exception) {
            android.util.Log.e("ConnectivityManager", "Exception in checkConnectivity", e)
            false
        }
    }
    
    fun isOnline(): Boolean {
        val online = _isOnline.value
        android.util.Log.i("ConnectivityManager", "isOnline() called, returning: $online")
        return online
    }
    
    fun getIsOnlineFlow(): StateFlow<Boolean> = isOnline
    
    fun unregisterCallback() {
        try {
            connectivityManager.unregisterNetworkCallback(networkCallback)
        } catch (e: Exception) {
            android.util.Log.e("ConnectivityManager", "Failed to unregister network callback", e)
        }
    }
}
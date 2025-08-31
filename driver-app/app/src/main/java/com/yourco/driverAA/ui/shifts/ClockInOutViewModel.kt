package com.yourco.driverAA.ui.shifts

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import android.location.Location
import androidx.core.content.ContextCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.ClockInRequest
import com.yourco.driverAA.data.api.ClockOutRequest
import com.yourco.driverAA.data.api.ShiftResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import retrofit2.HttpException
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

data class ClockInOutUiState(
    val isClocked: Boolean = false,
    val isLoading: Boolean = false,
    val error: String? = null,
    val currentLocation: String? = null,
    val clockInTime: String? = null,
    val hoursWorked: Float? = null,
    val isOutstation: Boolean = false,
    val shiftId: Int? = null
)

@HiltViewModel
class ClockInOutViewModel @Inject constructor(
    private val api: DriverApi,
    @ApplicationContext private val context: Context
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(ClockInOutUiState())
    val uiState: StateFlow<ClockInOutUiState> = _uiState.asStateFlow()
    
    private val fusedLocationClient: FusedLocationProviderClient by lazy {
        LocationServices.getFusedLocationProviderClient(context)
    }
    
    private val geocoder: Geocoder by lazy {
        Geocoder(context, Locale.getDefault())
    }

    fun loadShiftStatus() {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
                
                val response = api.getShiftStatus()
                val timeFormatter = SimpleDateFormat("HH:mm", Locale.getDefault())
                
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    isClocked = response.is_clocked_in,
                    clockInTime = response.clock_in_at?.let { timeFormatter.format(Date(it * 1000)) },
                    hoursWorked = response.hours_worked?.toFloat(),
                    isOutstation = response.is_outstation ?: false,
                    currentLocation = response.location,
                    shiftId = response.shift_id
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Failed to load shift status: ${e.message}"
                )
            }
        }
    }

    fun clockIn() {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
                
                getCurrentLocation { location ->
                    viewModelScope.launch {
                        try {
                            val locationName = getLocationName(location.latitude, location.longitude)
                            
                            val request = ClockInRequest(
                                lat = location.latitude,
                                lng = location.longitude,
                                location_name = locationName
                            )
                            
                            val shift = api.clockIn(request)
                            val timeFormatter = SimpleDateFormat("HH:mm", Locale.getDefault())
                            
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                isClocked = true,
                                clockInTime = timeFormatter.format(Date(shift.clock_in_at * 1000)),
                                currentLocation = shift.clock_in_location_name,
                                isOutstation = shift.is_outstation,
                                shiftId = shift.id,
                                hoursWorked = 0f
                            )
                        } catch (e: HttpException) {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                error = "Clock-in failed: ${e.message()}"
                            )
                        } catch (e: Exception) {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                error = "Clock-in failed: ${e.message}"
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Failed to get location: ${e.message}"
                )
            }
        }
    }

    fun clockOut(notes: String? = null) {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
                
                getCurrentLocation { location ->
                    viewModelScope.launch {
                        try {
                            val locationName = getLocationName(location.latitude, location.longitude)
                            
                            val request = ClockOutRequest(
                                lat = location.latitude,
                                lng = location.longitude,
                                location_name = locationName,
                                notes = notes
                            )
                            
                            val shift = api.clockOut(request)
                            
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                isClocked = false,
                                clockInTime = null,
                                currentLocation = null,
                                hoursWorked = shift.total_working_hours?.toFloat(),
                                shiftId = null
                            )
                        } catch (e: HttpException) {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                error = "Clock-out failed: ${e.message()}"
                            )
                        } catch (e: Exception) {
                            _uiState.value = _uiState.value.copy(
                                isLoading = false,
                                error = "Clock-out failed: ${e.message}"
                            )
                        }
                    }
                }
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Failed to get location: ${e.message}"
                )
            }
        }
    }

    private fun getCurrentLocation(onLocationReceived: (Location) -> Unit) {
        if (ContextCompat.checkSelfPermission(
                context,
                Manifest.permission.ACCESS_FINE_LOCATION
            ) != PackageManager.PERMISSION_GRANTED
        ) {
            throw SecurityException("Location permission not granted")
        }

        val locationRequest = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 10000)
            .setWaitForAccurateLocation(false)
            .setMinUpdateIntervalMillis(5000)
            .setMaxUpdateDelayMillis(30000)
            .build()

        fusedLocationClient.getCurrentLocation(Priority.PRIORITY_HIGH_ACCURACY, null)
            .addOnSuccessListener { location: Location? ->
                location?.let { onLocationReceived(it) }
                    ?: throw RuntimeException("Unable to get current location")
            }
            .addOnFailureListener { exception ->
                throw exception
            }
    }

    private suspend fun getLocationName(lat: Double, lng: Double): String {
        return try {
            val addresses = geocoder.getFromLocation(lat, lng, 1)
            if (addresses?.isNotEmpty() == true) {
                val address = addresses[0]
                val locationParts = mutableListOf<String>()
                
                address.subLocality?.let { locationParts.add(it) }
                address.locality?.let { locationParts.add(it) }
                address.adminArea?.let { locationParts.add(it) }
                
                locationParts.joinToString(", ").takeIf { it.isNotEmpty() }
                    ?: "Unknown Location"
            } else {
                "Location (${"%.4f".format(lat)}, ${"%.4f".format(lng)})"
            }
        } catch (e: Exception) {
            "Location (${"%.4f".format(lat)}, ${"%.4f".format(lng)})"
        }
    }
}
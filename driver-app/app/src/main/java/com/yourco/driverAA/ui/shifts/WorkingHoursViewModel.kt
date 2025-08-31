package com.yourco.driverAA.ui.shifts

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.api.ShiftResponse
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

data class ShiftHistoryItem(
    val id: Int,
    val date: String,
    val clockIn: String,
    val clockOut: String,
    val hoursWorked: String,
    val earnings: String,
    val isOutstation: Boolean
)

data class WorkingHoursUiState(
    val isLoading: Boolean = false,
    val error: String? = null,
    val todayHours: Float? = null,
    val weekHours: Float? = null,
    val monthHours: Float? = null,
    val monthEarnings: Float? = null,
    val recentShifts: List<ShiftHistoryItem> = emptyList()
)

@HiltViewModel
class WorkingHoursViewModel @Inject constructor(
    private val api: DriverApi
) : ViewModel() {
    
    private val _uiState = MutableStateFlow(WorkingHoursUiState())
    val uiState: StateFlow<WorkingHoursUiState> = _uiState.asStateFlow()

    fun loadWorkingHours() {
        viewModelScope.launch {
            try {
                _uiState.value = _uiState.value.copy(isLoading = true, error = null)
                
                // Load recent shifts
                val shifts = api.getShiftHistory(limit = 20)
                val shiftItems = shifts.map { shift ->
                    formatShiftToHistoryItem(shift)
                }
                
                // Calculate summary statistics
                val now = Calendar.getInstance()
                val todayStart = Calendar.getInstance().apply {
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                    set(Calendar.MILLISECOND, 0)
                }
                
                val weekStart = Calendar.getInstance().apply {
                    set(Calendar.DAY_OF_WEEK, Calendar.MONDAY)
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                    set(Calendar.MILLISECOND, 0)
                }
                
                val monthStart = Calendar.getInstance().apply {
                    set(Calendar.DAY_OF_MONTH, 1)
                    set(Calendar.HOUR_OF_DAY, 0)
                    set(Calendar.MINUTE, 0)
                    set(Calendar.SECOND, 0)
                    set(Calendar.MILLISECOND, 0)
                }
                
                val todayHours = shifts.filter { shift ->
                    shift.clock_in_at >= todayStart.timeInMillis / 1000
                }.sumOf { it.total_working_hours ?: 0.0 }.toFloat()
                
                val weekHours = shifts.filter { shift ->
                    shift.clock_in_at >= weekStart.timeInMillis / 1000
                }.sumOf { it.total_working_hours ?: 0.0 }.toFloat()
                
                val monthHours = shifts.filter { shift ->
                    shift.clock_in_at >= monthStart.timeInMillis / 1000
                }.sumOf { it.total_working_hours ?: 0.0 }.toFloat()
                
                val monthEarnings = shifts.filter { shift ->
                    shift.clock_in_at >= monthStart.timeInMillis / 1000
                }.sumOf { it.outstation_allowance_amount }.toFloat()
                
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    todayHours = todayHours,
                    weekHours = weekHours,
                    monthHours = monthHours,
                    monthEarnings = monthEarnings,
                    recentShifts = shiftItems
                )
                
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = "Failed to load working hours: ${e.message}"
                )
            }
        }
    }
    
    private fun formatShiftToHistoryItem(shift: ShiftResponse): ShiftHistoryItem {
        val dateFormatter = SimpleDateFormat("MMM dd", Locale.getDefault())
        val timeFormatter = SimpleDateFormat("HH:mm", Locale.getDefault())
        
        val clockInDate = Date(shift.clock_in_at * 1000)
        val clockOutDate = shift.clock_out_at?.let { Date(it * 1000) }
        
        return ShiftHistoryItem(
            id = shift.id,
            date = dateFormatter.format(clockInDate),
            clockIn = timeFormatter.format(clockInDate),
            clockOut = clockOutDate?.let { timeFormatter.format(it) } ?: "Active",
            hoursWorked = String.format("%.1f", shift.total_working_hours ?: 0.0),
            earnings = String.format("%.0f", shift.outstation_allowance_amount),
            isOutstation = shift.is_outstation
        )
    }
}
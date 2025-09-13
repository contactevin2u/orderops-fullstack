// ui/home/HomeViewModel.kt
package com.yourco.driverAA.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.ui.model.HoldsUi
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class HomeUiState(
    val loading: Boolean = true,
    val holds: HoldsUi = HoldsUi(false),
    val error: String? = null
)

class HomeViewModel(
    private val repo: JobsRepository
) : ViewModel() {

    private val _state = MutableStateFlow(HomeUiState())
    val state: StateFlow<HomeUiState> = _state

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, error = null)
            when (val holdsRes = repo.getDriverHolds()) {
                is Result.Success -> {
                    val holds = holdsRes.data
                    val ui = HoldsUi(
                        hasActiveHolds = holds.has_active_holds == true,
                        reasons = holds.hold_reasons ?: emptyList()
                    )
                    _state.value = HomeUiState(loading = false, holds = ui)
                }
                is Result.Error -> {
                    _state.value = HomeUiState(
                        loading = false, 
                        holds = HoldsUi(false),
                        error = holdsRes.throwable.message
                    )
                }
                is Result.Loading -> {
                    // Keep loading state
                }
            }
        }
    }

    /**
     * Gate any job action (delivery, pickup, etc).
     * Return true if allowed, false if blocked (and we keep state unchanged).
     */
    fun canPerformJobAction(): Boolean {
        return !_state.value.holds.hasActiveHolds
    }
}
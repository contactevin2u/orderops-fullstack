package com.yourco.driverAA.ui.main

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class OrdersListViewModel @Inject constructor(
    private val repo: JobsRepository
) : ViewModel() {
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()
    
    private val _activeJobs = MutableStateFlow<List<JobDto>>(emptyList())
    private val _completedJobs = MutableStateFlow<List<JobDto>>(emptyList())
    
    fun getJobs(statusFilter: String): StateFlow<List<JobDto>> {
        return when (statusFilter) {
            "active" -> _activeJobs.asStateFlow()
            "completed" -> _completedJobs.asStateFlow()
            else -> _activeJobs.asStateFlow()
        }
    }

    fun loadJobs(statusFilter: String) {
        viewModelScope.launch {
            repo.getJobs(statusFilter).collect { result ->
                when (result) {
                    is Result.Loading -> _loading.value = true
                    is Result.Success -> {
                        _loading.value = false
                        when (statusFilter) {
                            "active" -> _activeJobs.value = result.data
                            "completed" -> _completedJobs.value = result.data
                        }
                    }
                    is Result.Error -> {
                        _loading.value = false
                        // Handle error appropriately - could show a snackbar or error state
                    }
                }
            }
        }
    }
}
package com.yourco.driverAA.ui.jobs

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.util.Result
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

@HiltViewModel
class JobsListViewModel @Inject constructor(
    private val repo: JobsRepository
) : ViewModel() {
    
    private val _jobs = MutableStateFlow<List<JobDto>>(emptyList())
    val jobs: StateFlow<List<JobDto>> = _jobs.asStateFlow()
    
    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()

    init {
        loadJobs()
    }

    fun loadJobs() {
        viewModelScope.launch {
            repo.getJobs().collect { result ->
                when (result) {
                    is Result.Loading -> _loading.value = true
                    is Result.Success -> {
                        _loading.value = false
                        _jobs.value = result.data
                    }
                    is Result.Error -> {
                        _loading.value = false
                        // Handle error appropriately
                    }
                }
            }
        }
    }
}

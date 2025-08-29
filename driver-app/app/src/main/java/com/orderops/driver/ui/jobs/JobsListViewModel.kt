package com.orderops.driver.ui.jobs

import android.content.Context
import androidx.lifecycle.ViewModel
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import com.orderops.driver.domain.JobsRepository
import kotlinx.coroutines.flow.Flow

@HiltViewModel
class JobsListViewModel @Inject constructor(
    private val repo: JobsRepository,
    @ApplicationContext private val context: Context
) : ViewModel() {
    private val prefs = context.getSharedPreferences("driver", Context.MODE_PRIVATE)
    val jobs: Flow<List<String>> = repo.jobs
    var token: String = prefs.getString("token", "") ?: ""
        private set

    fun saveToken(value: String) {
        token = value
        prefs.edit().putString("token", value).apply()
    }
}

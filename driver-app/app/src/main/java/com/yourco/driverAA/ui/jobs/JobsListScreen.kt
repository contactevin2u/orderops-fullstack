package com.yourco.driverAA.ui.jobs

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ListItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel

@Composable
fun JobsListScreen(onJobClick: (String) -> Unit, viewModel: JobsListViewModel = hiltViewModel()) {
    val jobs by viewModel.jobs.collectAsState(initial = emptyList())
    val loading by viewModel.loading.collectAsState()

    Column {
        if (loading) {
            Text("Loading jobs...")
        } else if (jobs.isEmpty()) {
            Text("No jobs available")
        } else {
            LazyColumn {
                items(jobs) { job ->
                    ListItem(
                        headlineContent = { Text("Job ${job.id}") },
                        supportingContent = { 
                            Text("Customer: ${job.customer_name ?: "Unknown"}")
                        },
                        modifier = Modifier.clickable { onJobClick(job.id) }
                    )
                }
            }
        }
    }
}

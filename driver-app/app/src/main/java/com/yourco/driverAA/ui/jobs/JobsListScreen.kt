package com.yourco.driverAA.ui.jobs

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.ListItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.ui.Alignment
import androidx.compose.runtime.*
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.compose.ui.Modifier

@Composable

// Then in the composable:
ListItem(
    headlineText = { Text("Job $job") },
    modifier = Modifier.clickable { onJobClick(job) }
fun JobsListScreen(onJobClick: (String) -> Unit, viewModel: JobsListViewModel = hiltViewModel()) {
    val jobs by viewModel.jobs.collectAsState()
    val loading by viewModel.loading.collectAsState()
    var token by remember { mutableStateOf(viewModel.token) }

    Column {
        OutlinedTextField(
            value = token,
            onValueChange = {
                token = it
                viewModel.saveToken(it)
            },
            label = { Text("Auth Token") }
        )
        if (loading) {
            Box(
                modifier = androidx.compose.ui.Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn {
                items(jobs) { job ->
                    ListItem(
                        headlineText = { Text("Job $job") },
                        modifier = androidx.compose.ui.Modifier.clickable { onJobClick(job) }
                    )
                }
            }
        }
    }
}

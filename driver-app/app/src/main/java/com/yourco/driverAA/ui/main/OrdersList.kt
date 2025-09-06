package com.yourco.driverAA.ui.main

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.ui.components.OrderJobCard
import com.yourco.driverAA.ui.components.OrderOpsCard
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun OrdersList(
    statusFilter: String,
    onJobClick: (String) -> Unit,
    viewModel: OrdersListViewModel = hiltViewModel()
) {
    val jobs by viewModel.getJobs(statusFilter).collectAsState(initial = emptyList())
    val loading by viewModel.loading.collectAsState()
    var searchQuery by remember { mutableStateOf("") }
    var showSearch by remember { mutableStateOf(false) }

    LaunchedEffect(statusFilter) {
        viewModel.loadJobs(statusFilter)
    }

    // Filter and sort jobs
    val filteredAndSortedJobs = remember(jobs, searchQuery) {
        val filtered = if (searchQuery.isBlank()) {
            jobs
        } else {
            jobs.filter { job ->
                (job.code?.contains(searchQuery, ignoreCase = true) == true) ||
                (job.customer_name?.contains(searchQuery, ignoreCase = true) == true) ||
                (job.customer_phone?.contains(searchQuery, ignoreCase = true) == true) ||
                (job.address?.contains(searchQuery, ignoreCase = true) == true)
            }
        }
        
        // Sort by delivery date (newest first for completed orders)
        if (statusFilter == "completed") {
            filtered.sortedByDescending { job ->
                job.delivery_date?.let { dateStr ->
                    try {
                        SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).parse(dateStr)?.time ?: 0L
                    } catch (e: Exception) {
                        0L
                    }
                } ?: 0L
            }
        } else {
            filtered.sortedBy { job ->
                job.delivery_date?.let { dateStr ->
                    try {
                        SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).parse(dateStr)?.time ?: Long.MAX_VALUE
                    } catch (e: Exception) {
                        Long.MAX_VALUE
                    }
                } ?: Long.MAX_VALUE
            }
        }
    }

    Column(modifier = Modifier.fillMaxSize()) {
        // Search bar (for completed orders)
        if (statusFilter == "completed") {
            if (showSearch) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    placeholder = { Text("Search orders...") },
                    leadingIcon = {
                        Icon(Icons.Default.Search, contentDescription = "Search")
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Clear, contentDescription = "Clear")
                            }
                        } else {
                            IconButton(onClick = { showSearch = false }) {
                                Icon(Icons.Default.Clear, contentDescription = "Close search")
                            }
                        }
                    },
                    singleLine = true
                )
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.End
                ) {
                    IconButton(onClick = { showSearch = true }) {
                        Icon(Icons.Default.Search, contentDescription = "Search orders")
                    }
                }
            }
        }

        Box(modifier = Modifier.fillMaxSize()) {
            when {
                loading -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                filteredAndSortedJobs.isEmpty() -> {
                    Card(
                        modifier = Modifier
                            .align(Alignment.Center)
                            .padding(16.dp)
                    ) {
                        Text(
                            text = when {
                                searchQuery.isNotEmpty() -> "No orders found matching '$searchQuery'"
                                statusFilter == "active" -> "No active orders"
                                else -> "No completed orders"
                            },
                            modifier = Modifier.padding(16.dp),
                            style = MaterialTheme.typography.bodyLarge
                        )
                    }
                }
                else -> {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(filteredAndSortedJobs) { job ->
                            OrderJobCard(
                                orderCode = job.code ?: job.id,
                                customerName = job.customer_name ?: "Unknown Customer",
                                status = job.status ?: "UNKNOWN",
                                deliveryDate = job.delivery_date,
                                address = job.address,
                                phone = job.customer_phone,
                                onClick = { onJobClick(job.id) }
                            )
                        }
                    }
                }
            }
        }
    }
}


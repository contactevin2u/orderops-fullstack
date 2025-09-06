package com.yourco.driverAA.ui.main

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.ui.window.Dialog
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.TrendingUp
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.DateRange
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.api.CommissionMonthDto
import com.yourco.driverAA.data.api.JobDto
import com.yourco.driverAA.ui.components.OrderOpsCard
import com.yourco.driverAA.ui.components.SummaryCard
import com.yourco.driverAA.ui.components.OrderOpsPrimaryButton
import com.yourco.driverAA.ui.components.OrderOpsSecondaryButton
import com.yourco.driverAA.ui.components.StatusChip
import java.text.DecimalFormat

@Composable
fun CommissionsList(viewModel: CommissionsViewModel = hiltViewModel()) {
    val commissions by viewModel.commissions.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val selectedMonth by viewModel.selectedMonth.collectAsState()
    val showMonthPicker by viewModel.showMonthPicker.collectAsState()
    val upsellIncentives by viewModel.upsellIncentives.collectAsState()
    val activeTab by viewModel.activeTab.collectAsState()
    val detailedOrders by viewModel.detailedOrders.collectAsState()
    val showDetailedOrders by viewModel.showDetailedOrders.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.loadCommissions()
    }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        when {
            isLoading -> {
                CircularProgressIndicator(
                    modifier = Modifier.align(Alignment.Center),
                    color = MaterialTheme.colorScheme.primary
                )
            }
            error != null -> {
                OrderOpsCard(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            Icons.Default.Close,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.error,
                            modifier = Modifier.size(24.dp)
                        )
                        Spacer(modifier = Modifier.width(12.dp))
                        Text(
                            text = "Error: $error",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    }
                }
            }
            commissions.isEmpty() -> {
                Column(
                    modifier = Modifier.align(Alignment.Center),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(
                        Icons.Default.AttachMoney,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(64.dp)
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    Text(
                        text = "No commissions yet",
                        style = MaterialTheme.typography.titleLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "Complete deliveries to start earning",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center
                    )
                }
            }
            else -> {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    item {
                        // Enhanced Header with Brand Styling
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                Icons.Default.AttachMoney,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(32.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                text = "My Earnings",
                                style = MaterialTheme.typography.headlineMedium,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                    
                    item {
                        // Tab Row for switching between Commissions and Upsells
                        TabRow(
                            selectedTabIndex = if (activeTab == "commissions") 0 else 1,
                            containerColor = MaterialTheme.colorScheme.primaryContainer,
                            contentColor = MaterialTheme.colorScheme.onPrimaryContainer
                        ) {
                            Tab(
                                selected = activeTab == "commissions",
                                onClick = { viewModel.setActiveTab("commissions") },
                                text = { 
                                    Text(
                                        "Commissions",
                                        fontWeight = if (activeTab == "commissions") FontWeight.Bold else FontWeight.Medium
                                    ) 
                                },
                                icon = { Icon(Icons.Default.Receipt, contentDescription = null) }
                            )
                            Tab(
                                selected = activeTab == "upsells",
                                onClick = { viewModel.setActiveTab("upsells") },
                                text = { 
                                    Text(
                                        "Upsell Incentives",
                                        fontWeight = if (activeTab == "upsells") FontWeight.Bold else FontWeight.Medium
                                    ) 
                                },
                                icon = { Icon(Icons.Default.Star, contentDescription = null) }
                            )
                        }
                    }

                    when (activeTab) {
                        "commissions" -> {
                            // Month picker
                            item {
                                OrderOpsCard {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { viewModel.toggleMonthPicker() },
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Row(verticalAlignment = Alignment.CenterVertically) {
                                            Icon(
                                                Icons.Default.DateRange,
                                                contentDescription = null,
                                                tint = MaterialTheme.colorScheme.primary
                                            )
                                            Spacer(modifier = Modifier.width(12.dp))
                                            Text(
                                                text = selectedMonth?.let { "Month: $it" } ?: "Select Month",
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = FontWeight.Medium
                                            )
                                        }
                                        Icon(
                                            if (showMonthPicker) Icons.Default.KeyboardArrowUp 
                                            else Icons.Default.KeyboardArrowDown,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    }
                                }
                            }

                            // Month picker dropdown
                            if (showMonthPicker) {
                                item {
                                    OrderOpsCard {
                                        LazyColumn(
                                            modifier = Modifier.heightIn(max = 200.dp)
                                        ) {
                                            items(commissions) { commission ->
                                                Text(
                                                    text = commission.month,
                                                    modifier = Modifier
                                                        .fillMaxWidth()
                                                        .clickable { viewModel.selectMonth(commission.month) }
                                                        .padding(vertical = 12.dp, horizontal = 16.dp),
                                                    style = MaterialTheme.typography.bodyLarge
                                                )
                                                if (commission != commissions.last()) {
                                                    Divider()
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Commission cards for selected month
                            val selectedCommission = selectedMonth?.let { month ->
                                commissions.find { it.month == month }
                            }
                            
                            if (selectedCommission != null) {
                                item {
                                    SummaryCard(
                                        title = "Monthly Total",
                                        value = "RM ${DecimalFormat("#,##0.00").format(selectedCommission.total)}",
                                        subtitle = selectedCommission.month,
                                        backgroundColor = MaterialTheme.colorScheme.primaryContainer,
                                        onClick = { viewModel.loadDetailedOrders(selectedCommission.month) }
                                    )
                                }
                            }

                            // Show all commissions if no month selected
                            if (selectedMonth == null) {
                                items(commissions) { commission ->
                                    CommissionCard(
                                        commission = commission,
                                        onViewDetails = { viewModel.loadDetailedOrders(commission.month) }
                                    )
                                }
                            }
                        }
                        "upsells" -> {
                            // Upsell incentives content
                            upsellIncentives?.let { incentives ->
                                item {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        SummaryCard(
                                            title = "Pending",
                                            value = "RM ${DecimalFormat("#,##0.00").format(incentives.summary?.total_pending ?: 0.0)}",
                                            modifier = Modifier.weight(1f),
                                            backgroundColor = MaterialTheme.colorScheme.tertiaryContainer
                                        )
                                        SummaryCard(
                                            title = "Released",
                                            value = "RM ${DecimalFormat("#,##0.00").format(incentives.summary?.total_released ?: 0.0)}",
                                            modifier = Modifier.weight(1f),
                                            backgroundColor = MaterialTheme.colorScheme.primaryContainer
                                        )
                                    }
                                }

                                items(incentives.incentives ?: emptyList()) { incentive ->
                                    UpsellIncentiveCard(incentive = incentive)
                                }
                            } ?: item {
                                Text(
                                    text = "No upsell incentives yet",
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(32.dp),
                                    textAlign = TextAlign.Center,
                                    style = MaterialTheme.typography.bodyLarge,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }

        // Detailed Orders Dialog
        if (showDetailedOrders) {
            Dialog(onDismissRequest = { viewModel.hideDetailedOrders() }) {
                OrderOpsCard(
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Detailed Orders",
                                style = MaterialTheme.typography.headlineSmall,
                                fontWeight = FontWeight.Bold
                            )
                            IconButton(onClick = { viewModel.hideDetailedOrders() }) {
                                Icon(Icons.Default.Close, contentDescription = "Close")
                            }
                        }
                        
                        Spacer(modifier = Modifier.height(16.dp))
                        
                        LazyColumn(
                            modifier = Modifier.heightIn(max = 400.dp),
                            verticalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            items(detailedOrders) { order ->
                                DetailedOrderCard(order = order)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun CommissionCard(
    commission: CommissionMonthDto,
    onViewDetails: () -> Unit
) {
    SummaryCard(
        title = commission.month,
        value = "RM ${DecimalFormat("#,##0.00").format(commission.total)}",
        subtitle = "Monthly Commission",
        onClick = onViewDetails
    )
}

@Composable
private fun UpsellIncentiveCard(incentive: com.yourco.driverAA.data.api.UpsellIncentiveDto) {
    OrderOpsCard {
        Column {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Order #${incentive.order_code}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )
                StatusChip(status = incentive.status ?: "PENDING")
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Column {
                    Text(
                        text = "Upsell Amount",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "RM ${DecimalFormat("#,##0.00").format(incentive.upsell_amount ?: 0.0)}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Medium
                    )
                }
                Column(horizontalAlignment = Alignment.End) {
                    Text(
                        text = "Your Incentive",
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        text = "RM ${DecimalFormat("#,##0.00").format(incentive.driver_incentive ?: 0.0)}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
            
            incentive.notes?.let { notes ->
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = notes,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun DetailedOrderCard(order: JobDto) {
    OrderOpsCard {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Order #${order.code ?: order.id}",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = order.customer_name ?: "Unknown Customer",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
            order.commission?.let { commission ->
                Text(
                    text = "RM ${DecimalFormat("#,##0.00").format(commission.amount?.toDoubleOrNull() ?: 0.0)}",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}
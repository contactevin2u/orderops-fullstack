package com.yourco.driverAA.ui.main

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Inventory
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.yourco.driverAA.ui.components.OrderOpsIconButton
import com.yourco.driverAA.ui.stock.StockScreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onJobClick: (String) -> Unit,
    onClockInOutClick: () -> Unit,
    onSignOut: () -> Unit = {}
) {
    var selectedTabIndex by remember { mutableIntStateOf(0) }
    
    val tabs = listOf("Active Orders", "Completed Orders", "Commissions", "Stock", "Clock In/Out")
    val tabIcons = listOf(Icons.Default.List, Icons.Default.CheckCircle, Icons.Default.Star, Icons.Default.Inventory, Icons.Default.AccessTime)
    
    Column(modifier = Modifier.fillMaxSize()) {
        // Enhanced Top App Bar
        TopAppBar(
            title = { 
                Text(
                    text = "OrderOps Driver",
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.Bold
                )
            },
            actions = {
                OrderOpsIconButton(
                    onClick = onSignOut,
                    icon = Icons.Filled.Logout,
                    contentDescription = "Sign Out",
                    tint = MaterialTheme.colorScheme.primary
                )
            },
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = MaterialTheme.colorScheme.surface,
                titleContentColor = MaterialTheme.colorScheme.primary
            )
        )
        
        // Enhanced Tab Row
        TabRow(
            selectedTabIndex = selectedTabIndex,
            containerColor = MaterialTheme.colorScheme.primaryContainer,
            contentColor = MaterialTheme.colorScheme.onPrimaryContainer,
            indicator = { tabPositions ->
                if (selectedTabIndex < tabPositions.size) {
                    TabRowDefaults.SecondaryIndicator(
                        modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                        height = 3.dp,
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        ) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTabIndex == index,
                    onClick = { selectedTabIndex = index },
                    text = { 
                        Text(
                            text = title,
                            fontWeight = if (selectedTabIndex == index) FontWeight.Bold else FontWeight.Medium,
                            style = MaterialTheme.typography.labelMedium
                        )
                    },
                    icon = { 
                        Icon(
                            tabIcons[index], 
                            contentDescription = null,
                            tint = if (selectedTabIndex == index) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            }
                        )
                    }
                )
            }
        }
        
        when (selectedTabIndex) {
            0 -> ActiveOrdersContent(onJobClick = onJobClick)
            1 -> CompletedOrdersContent(onJobClick = onJobClick)
            2 -> CommissionsContent()
            3 -> StockContent()
            4 -> ClockInOutContent(onClockInOutClick = onClockInOutClick)
        }
    }
}

@Composable
private fun ActiveOrdersContent(onJobClick: (String) -> Unit) {
    OrdersList(statusFilter = "active", onJobClick = onJobClick)
}

@Composable
private fun CompletedOrdersContent(onJobClick: (String) -> Unit) {
    OrdersList(statusFilter = "completed", onJobClick = onJobClick)
}

@Composable
private fun CommissionsContent() {
    CommissionsList()
}

@Composable
private fun StockContent() {
    StockScreen()
}

@Composable
private fun ClockInOutContent(onClockInOutClick: () -> Unit) {
    LaunchedEffect(Unit) {
        onClockInOutClick()
    }
}
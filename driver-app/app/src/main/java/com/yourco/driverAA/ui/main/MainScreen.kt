package com.yourco.driverAA.ui.main

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(
    onJobClick: (String) -> Unit,
    onClockInOutClick: () -> Unit,
    onSignOut: () -> Unit = {}
) {
    var selectedTabIndex by remember { mutableIntStateOf(0) }
    
    val tabs = listOf("Active Orders", "Completed Orders", "Commissions", "Clock In/Out")
    val tabIcons = listOf(Icons.Default.List, Icons.Default.CheckCircle, Icons.Default.Star, Icons.Default.AccessTime)
    
    Column(modifier = Modifier.fillMaxSize()) {
        // Top App Bar with Sign Out button
        TopAppBar(
            title = { Text("Driver App") },
            actions = {
                IconButton(
                    onClick = onSignOut
                ) {
                    Icon(
                        Icons.Filled.Logout,
                        contentDescription = "Sign Out",
                        tint = MaterialTheme.colorScheme.onSurface
                    )
                }
            }
        )
        
        TabRow(selectedTabIndex = selectedTabIndex) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTabIndex == index,
                    onClick = { selectedTabIndex = index },
                    text = { Text(title) },
                    icon = { Icon(tabIcons[index], contentDescription = null) }
                )
            }
        }
        
        when (selectedTabIndex) {
            0 -> ActiveOrdersContent(onJobClick = onJobClick)
            1 -> CompletedOrdersContent(onJobClick = onJobClick)
            2 -> CommissionsContent()
            3 -> ClockInOutContent(onClockInOutClick = onClockInOutClick)
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
private fun ClockInOutContent(onClockInOutClick: () -> Unit) {
    LaunchedEffect(Unit) {
        onClockInOutClick()
    }
}
package com.yourco.driverAA.ui.main

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen(onJobClick: (String) -> Unit) {
    var selectedTabIndex by remember { mutableIntStateOf(0) }
    
    val tabs = listOf("Active Orders", "Completed Orders", "Commissions")
    val tabIcons = listOf(Icons.Default.List, Icons.Default.CheckCircle, Icons.Default.AttachMoney)
    
    Column(modifier = Modifier.fillMaxSize()) {
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
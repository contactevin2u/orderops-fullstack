package com.yourco.driverAA.ui.admin

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.auth.AuthService

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AdminMainScreen(
    onLogout: () -> Unit,
    authService: AuthService = hiltViewModel<AdminMainViewModel>().authService
) {
    var selectedTabIndex by remember { mutableIntStateOf(0) }
    
    val tabs = listOf(
        "Orders" to Icons.Filled.ShoppingCart,
        "AI Assignments" to Icons.Filled.Psychology,
        "Assignments" to Icons.Filled.Assignment
    )

    Column(
        modifier = Modifier.fillMaxSize()
    ) {
        // Top App Bar
        TopAppBar(
            title = { Text("Admin Dashboard") },
            actions = {
                TextButton(
                    onClick = {
                        authService.signOut()
                        onLogout()
                    }
                ) {
                    Icon(Icons.Filled.Logout, contentDescription = "Logout")
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Logout")
                }
            }
        )
        
        // Tab Row
        TabRow(
            selectedTabIndex = selectedTabIndex,
            modifier = Modifier.fillMaxWidth()
        ) {
            tabs.forEachIndexed { index, (title, icon) ->
                Tab(
                    selected = selectedTabIndex == index,
                    onClick = { selectedTabIndex = index },
                    text = { Text(title) },
                    icon = { Icon(icon, contentDescription = title) }
                )
            }
        }
        
        // Tab Content
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp)
        ) {
            when (selectedTabIndex) {
                0 -> OrderManagementTab()
                1 -> AIAssignmentTab()
                2 -> AssignmentManagementTab()
            }
        }
    }
}

@Composable
fun OrderManagementTab() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "Order Management",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Create Order from Message",
                    style = MaterialTheme.typography.titleMedium
                )
                Text(
                    text = "Paste WhatsApp message or order details below:",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                
                MessageParsingCard()
            }
        }
        
        PendingOrdersList()
    }
}

@Composable
fun AIAssignmentTab() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "AI Assignment Suggestions",
            style = MaterialTheme.typography.headlineSmall
        )
        
        AIAssignmentSuggestionsList()
    }
}

@Composable
fun AssignmentManagementTab() {
    Column(
        modifier = Modifier.fillMaxSize(),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "Assignment Management",
            style = MaterialTheme.typography.headlineSmall
        )
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Card(
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Available Drivers",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    AvailableDriversList()
                }
            }
            
            Card(
                modifier = Modifier.weight(1f)
            ) {
                Column(
                    modifier = Modifier.padding(16.dp)
                ) {
                    Text(
                        text = "Current Assignments",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    CurrentAssignmentsList()
                }
            }
        }
    }
}
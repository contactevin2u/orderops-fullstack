// ui/home/HomeScreen.kt
package com.yourco.driverAA.ui.home

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.yourco.driverAA.ui.components.HoldBanner
import com.yourco.driverAA.ui.navigation.NavRoute

@Composable
fun HomeScreen(
    vm: HomeViewModel,
    onNavigate: (String) -> Unit
) {
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) { vm.refresh() }

    Column(Modifier.fillMaxSize().padding(16.dp)) {
        if (state.holds.hasActiveHolds) {
            HoldBanner(
                reasons = state.holds.reasons,
                onOpenVerification = { onNavigate(NavRoute.Verification.route) }
            )
            Spacer(Modifier.height(16.dp))
        }

        // Job actions
        Text("Jobs", style = MaterialTheme.typography.titleLarge)
        Spacer(Modifier.height(8.dp))

        val disabled = state.holds.hasActiveHolds

        Button(
            onClick = { if (vm.canPerformJobAction()) onNavigate(NavRoute.Jobs.route) },
            enabled = !disabled
        ) { Text("Start Deliveries") }

        Spacer(Modifier.height(8.dp))

        Button(
            onClick = { if (vm.canPerformJobAction()) onNavigate(NavRoute.Pickups.route) },
            enabled = !disabled
        ) { Text("Start Collections") }

        if (disabled) {
            Spacer(Modifier.height(8.dp))
            Text(
                "Job actions are disabled while holds are active.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}
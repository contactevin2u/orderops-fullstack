// ui/components/HoldBanner.kt
package com.yourco.driverAA.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

@Composable
fun HoldBanner(
    reasons: List<String>,
    onOpenVerification: () -> Unit,
    modifier: Modifier = Modifier
) {
    ElevatedCard(modifier = modifier) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("⚠️ Morning stock verification pending", style = MaterialTheme.typography.titleMedium)
            if (reasons.isNotEmpty()) {
                Text(
                    "Holds: " + reasons.joinToString(separator = "; "),
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            Text(
                "Please complete the morning verification. Ops will release the hold after review.",
                style = MaterialTheme.typography.bodySmall
            )
            Spacer(Modifier.height(12.dp))
            Button(onClick = onOpenVerification) {
                Text("Open Morning Verification")
            }
        }
    }
}
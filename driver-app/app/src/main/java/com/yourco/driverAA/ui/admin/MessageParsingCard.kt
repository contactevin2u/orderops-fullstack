package com.yourco.driverAA.ui.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MessageParsingCard(
    viewModel: AdminMainViewModel = hiltViewModel()
) {
    var messageText by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }
    val uiState by viewModel.uiState.collectAsState()
    
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        OutlinedTextField(
            value = messageText,
            onValueChange = { messageText = it },
            label = { Text("Paste message here") },
            placeholder = { 
                Text("Example:\nName: John Doe\nPhone: 0123456789\nAddress: 123 Main St, KL\nAmount: RM 150.00\nNotes: Urgent delivery")
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(120.dp),
            maxLines = 6,
            enabled = !isLoading
        )
        
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Button(
                onClick = {
                    val parsed = viewModel.parseMessage(messageText)
                    if (parsed != null) {
                        isLoading = true
                        viewModel.createOrderFromParsed(parsed) { success ->
                            isLoading = false
                            if (success) {
                                messageText = ""
                            }
                        }
                    }
                },
                enabled = messageText.isNotBlank() && !isLoading,
                modifier = Modifier.weight(1f)
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(16.dp),
                        color = MaterialTheme.colorScheme.onPrimary
                    )
                } else {
                    Text("Parse & Create Order")
                }
            }
            
            OutlinedButton(
                onClick = {
                    val parsed = viewModel.parseMessage(messageText)
                    // Show preview dialog or expand form
                    viewModel.showPreview(parsed)
                },
                enabled = messageText.isNotBlank() && !isLoading
            ) {
                Text("Preview")
            }
        }
        
        // Preview parsed information
        uiState.parsedOrder?.let { parsed ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                )
            ) {
                Column(
                    modifier = Modifier
                        .padding(16.dp)
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = "Parsed Information:",
                        style = MaterialTheme.typography.titleSmall,
                        color = MaterialTheme.colorScheme.primary
                    )
                    
                    InfoRow("Customer", parsed.customerName)
                    parsed.customerPhone?.let { InfoRow("Phone", it) }
                    InfoRow("Address", parsed.deliveryAddress)
                    if (parsed.totalAmount > 0) {
                        InfoRow("Amount", "RM ${parsed.totalAmount}")
                    }
                    parsed.notes?.let { InfoRow("Notes", it) }
                    
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Button(
                            onClick = {
                                isLoading = true
                                viewModel.createOrderFromParsed(parsed) { success ->
                                    isLoading = false
                                    if (success) {
                                        messageText = ""
                                        viewModel.clearPreview()
                                    }
                                }
                            },
                            modifier = Modifier.weight(1f),
                            enabled = !isLoading
                        ) {
                            Text("Create Order")
                        }
                        
                        OutlinedButton(
                            onClick = { viewModel.clearPreview() }
                        ) {
                            Text("Cancel")
                        }
                    }
                }
            }
        }
        
        // Error message
        uiState.error?.let { error ->
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = error,
                    modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        
        // Success message
        uiState.successMessage?.let { message ->
            Card(
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Text(
                    text = message,
                    modifier = Modifier.padding(12.dp),
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth()
    ) {
        Text(
            text = "$label:",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.width(80.dp)
        )
        Text(
            text = value,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.weight(1f)
        )
    }
}
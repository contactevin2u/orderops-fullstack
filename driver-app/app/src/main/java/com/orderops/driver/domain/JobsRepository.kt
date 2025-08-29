package com.orderops.driver.domain

import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flowOf

class JobsRepository {
    val jobs: Flow<List<String>> = flowOf(listOf("1", "2", "3"))
}

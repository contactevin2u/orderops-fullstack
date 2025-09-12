// ui/model/UiModels.kt
package com.yourco.driverAA.ui.model

data class HoldsUi(
    val hasActiveHolds: Boolean,
    val reasons: List<String> = emptyList()
)

data class LorrySkuUi(
    val skuId: Int,
    val skuName: String,
    val expected: Int,
    var counted: Int = 0
)

data class LorryStockUi(
    val dateIso: String,
    val driverId: Int,
    val lorryId: String?,
    val skus: List<LorrySkuUi>,
    val totalExpected: Int
)
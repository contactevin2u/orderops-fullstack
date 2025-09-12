// ui/navigation/NavRoute.kt
package com.yourco.driverAA.ui.navigation

sealed class NavRoute(val route: String) {
    object Home : NavRoute("home")
    object Jobs : NavRoute("jobs") 
    object Pickups : NavRoute("pickups")
    object Verification : NavRoute("verification")
}
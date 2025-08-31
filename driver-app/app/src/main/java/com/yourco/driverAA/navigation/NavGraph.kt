package com.yourco.driverAA.navigation

import androidx.compose.runtime.*
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import androidx.hilt.navigation.compose.hiltViewModel
import com.yourco.driverAA.data.auth.AuthService
import com.yourco.driverAA.data.repository.UserRepository
import com.yourco.driverAA.ui.auth.LoginScreen
import com.yourco.driverAA.ui.main.MainScreen
import com.yourco.driverAA.ui.admin.AdminMainScreen
import com.yourco.driverAA.ui.jobdetail.JobDetailScreen
import com.yourco.driverAA.ui.shifts.ClockInOutScreen
import com.yourco.driverAA.util.DeepLinks

@Composable
fun NavGraph() {
    val navController = rememberNavController()
    val authService: AuthService = hiltViewModel<AuthViewModel>().authService
    val userRepository: UserRepository = hiltViewModel<AuthViewModel>().userRepository
    val currentUser by authService.currentUser.collectAsState(initial = null)
    
    var isAdmin by remember { mutableStateOf(false) }
    
    LaunchedEffect(currentUser) {
        if (currentUser != null) {
            isAdmin = userRepository.isAdmin()
        }
    }
    
    val startDestination = when {
        currentUser == null -> "login"
        isAdmin -> "admin"
        else -> "jobs"
    }
    
    NavHost(navController = navController, startDestination = startDestination) {
        composable("login") {
            LoginScreen(
                onLoginSuccess = { isAdminUser ->
                    val destination = if (isAdminUser) "admin" else "jobs"
                    navController.navigate(destination) {
                        popUpTo("login") { inclusive = true }
                    }
                }
            )
        }
        composable("admin") {
            AdminMainScreen(
                onLogout = {
                    navController.navigate("login") {
                        popUpTo("admin") { inclusive = true }
                    }
                }
            )
        }
        composable("jobs") {
            MainScreen(
                onJobClick = { id -> navController.navigate("job/$id") },
                onClockInOutClick = { navController.navigate("clock") },
                onSignOut = {
                    authService.signOut()
                    navController.navigate("login") {
                        popUpTo("jobs") { inclusive = true }
                    }
                }
            )
        }
        composable("clock") {
            ClockInOutScreen()
        }
        composable(
            route = "job/{jobId}",
            arguments = listOf(navArgument("jobId") { type = NavType.StringType }),
            deepLinks = listOf(navDeepLink { uriPattern = "${DeepLinks.JOB_BASE}/{jobId}" })
        ) { backStackEntry ->
            val jobId = backStackEntry.arguments?.getString("jobId") ?: ""
            JobDetailScreen(
                jobId = jobId,
                onNavigateToActiveOrders = {
                    navController.navigate("jobs") {
                        popUpTo("jobs") { inclusive = false }
                    }
                }
            )
        }
    }
}

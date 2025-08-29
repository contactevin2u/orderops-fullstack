package com.orderops.driver.navigation

import androidx.compose.runtime.Composable
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import com.orderops.driver.ui.jobs.JobsListScreen
import com.orderops.driver.ui.jobdetail.JobDetailScreen
import com.orderops.driver.util.DeepLinks

@Composable
fun NavGraph() {
    val navController = rememberNavController()
    NavHost(navController = navController, startDestination = "jobs") {
        composable("jobs") {
            JobsListScreen(onJobClick = { id -> navController.navigate("job/$id") })
        }
        composable(
            route = "job/{jobId}",
            arguments = listOf(navArgument("jobId") { type = NavType.StringType }),
            deepLinks = listOf(navDeepLink { uriPattern = "${DeepLinks.JOB_BASE}/{jobId}" })
        ) { backStackEntry ->
            val jobId = backStackEntry.arguments?.getString("jobId") ?: ""
            JobDetailScreen(jobId)
        }
    }
}

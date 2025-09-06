package com.yourco.driverAA

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.Surface
import dagger.hilt.android.AndroidEntryPoint
import com.google.android.play.core.appupdate.AppUpdateManagerFactory
import com.google.android.play.core.install.model.AppUpdateType
import com.google.android.play.core.install.model.UpdateAvailability
import com.yourco.driverAA.navigation.NavGraph
import com.yourco.driverAA.ui.theme.OrderOpsDriverTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        checkForUpdates()
        setContent {
            OrderOpsDriverTheme {
                Surface { NavGraph() }
            }
        }
    }

    private fun checkForUpdates() {
        val manager = AppUpdateManagerFactory.create(this)
        manager.appUpdateInfo.addOnSuccessListener { info ->
            if (info.updateAvailability() == UpdateAvailability.UPDATE_AVAILABLE &&
                info.isUpdateTypeAllowed(AppUpdateType.FLEXIBLE)) {
                manager.startUpdateFlowForResult(info, AppUpdateType.FLEXIBLE, this, 0)
            }
        }
    }
}

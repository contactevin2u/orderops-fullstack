package com.yourco.driverAA

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.yourco.driverAA.push.MyFcmService

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        MyFcmService.requestPermission(this)
        MyFcmService.refreshToken(this)
    }
}

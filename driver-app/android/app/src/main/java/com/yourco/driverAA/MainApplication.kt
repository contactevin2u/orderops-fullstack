package com.yourco.driverAA

import android.app.Application
import com.facebook.react.ReactApplication
import com.facebook.react.ReactNativeHost
import com.facebook.react.PackageList
import com.facebook.soloader.SoLoader
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint
import com.facebook.react.defaults.DefaultReactNativeHost

class MainApplication : Application(), ReactApplication {
  override val reactNativeHost: ReactNativeHost = object : DefaultReactNativeHost(this) {
    override fun getUseDeveloperSupport() = BuildConfig.DEBUG
    override fun getPackages() = PackageList(this).packages
    override fun isNewArchEnabled() = BuildConfig.IS_NEW_ARCHITECTURE_ENABLED
    override fun isHermesEnabled() = BuildConfig.IS_HERMES_ENABLED
  }

  override fun onCreate() {
    super.onCreate()
    SoLoader.init(this, /* native exopackage */ false)
    if (BuildConfig.IS_NEW_ARCHITECTURE_ENABLED) {
      DefaultNewArchitectureEntryPoint.load()
    }
  }
}

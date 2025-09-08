import java.util.Properties
import java.io.FileInputStream
import java.util.Base64

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("kotlin-kapt")
    id("com.google.dagger.hilt.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("com.google.gms.google-services")
    id("com.google.firebase.crashlytics")
    id("com.google.firebase.appdistribution")
}

android {
    namespace = "com.yourco.driverAA"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.yourco.driverAA"
        minSdk = 24
        targetSdk = 35
        versionCode = 40
        versionName = "1.10.0"

        // Priority: Gradle property > local.properties > environment variable > fallback
        val apiBase = (findProperty("API_BASE") as String?)
            ?: run {
                val localProps = rootProject.file("local.properties")
                val props = Properties()
                if (localProps.exists()) {
                    props.load(localProps.inputStream())
                }
                props.getProperty("API_BASE")
            }
            ?: System.getenv("API_BASE")
            ?: "https://orderops-api-v1.onrender.com"
        
        println("DEBUG: Setting API_BASE to: $apiBase")
        buildConfigField("String", "API_BASE", "\"$apiBase\"")
    }

    signingConfigs {
        create("release") {
            val keystoreFile = rootProject.file("keystore.jks")
            val keystorePassword = System.getenv("KEYSTORE_PASSWORD")
            val keyAlias = System.getenv("KEY_ALIAS") 
            val keyPassword = System.getenv("KEY_PASSWORD")
            
            if (keystoreFile.exists() && keystorePassword != null && keyAlias != null && keyPassword != null) {
                storeFile = keystoreFile
                storePassword = keystorePassword
                this.keyAlias = keyAlias
                this.keyPassword = keyPassword
            } else {
                println("WARNING: Release signing not configured - keystore file or environment variables missing")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false  // Temporarily disable for debugging
            isShrinkResources = false  // Temporarily disable for debugging  
            isDebuggable = false
            
            // Only apply signing if keystore is configured
            val releaseSigningConfig = signingConfigs.getByName("release")
            if (releaseSigningConfig.storeFile != null) {
                signingConfig = releaseSigningConfig
            } else {
                println("WARNING: Using debug signing for release build - keystore not configured")
            }
            
            // Disable crashlytics mapping upload to save memory
            configure<com.google.firebase.crashlytics.buildtools.gradle.CrashlyticsExtension> {
                mappingFileUploadEnabled = false
            }
            
            // Firebase App Distribution properties
            firebaseAppDistribution {
                artifactType = "APK"
                groups = "testers"
            }
        }
        debug {
            isMinifyEnabled = false
            // Remove suffix for Firebase App Distribution
            // applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            
            // Firebase App Distribution properties
            firebaseAppDistribution {
                artifactType = "APK"
                groups = "testers"
            }
        }
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.15"
    }
    packaging.resources.excludes += "/META-INF/{AL2.0,LGPL2.1}"
    
    // AAB-specific configuration
    bundle {
        language {
            // Disable language splits - include all languages in base APK
            enableSplit = false
        }
        density {
            // Disable density splits for debugging
            enableSplit = false
        }
        abi {
            // Disable ABI splits for debugging  
            enableSplit = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
        // Reduce Kotlin compiler memory usage
        freeCompilerArgs += listOf(
            "-Xjvm-default=all"
        )
    }

    // Lint optimizations to reduce memory usage
    lint {
        // Disable resource-intensive lint checks
        disable += setOf(
            "UnusedResources",
            "IconDensities",
            "IconDuplicates",
            "IconLocation",
            "IconMissingDensityFolder",
            "IconXmlAndPng"
        )
        checkReleaseBuilds = false
        abortOnError = false
    }
}

kapt {
    correctErrorTypes = true
    // Reduce KAPT memory usage
    arguments {
        arg("room.schemaLocation", "$projectDir/schemas")
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation(platform("androidx.compose:compose-bom:2024.06.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui-tooling-preview")
    debugImplementation("androidx.compose.ui:ui-tooling")
    implementation("androidx.navigation:navigation-compose:2.7.7")
    implementation("androidx.navigation:navigation-runtime-ktx:2.7.7")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.activity:activity-compose:1.9.0")

    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.2")
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.jakewharton.retrofit:retrofit2-kotlinx-serialization-converter:0.8.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")

    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")

    implementation("androidx.work:work-runtime-ktx:2.9.0")
    implementation("androidx.hilt:hilt-work:1.2.0")
    kapt("androidx.hilt:hilt-compiler:1.2.0")

    implementation("com.google.dagger:hilt-android:2.51.1")
    kapt("com.google.dagger:hilt-android-compiler:2.51.1")

    implementation("com.google.android.gms:play-services-location:21.3.0")
    implementation("com.google.android.play:app-update-ktx:2.1.0")

    implementation("com.jakewharton.timber:timber:5.0.1")
    
    // QR Code Scanner
    implementation("com.google.zxing:core:3.5.2")
    implementation("com.journeyapps:zxing-android-embedded:4.3.0")
    implementation("androidx.camera:camera-camera2:1.3.4")
    implementation("androidx.camera:camera-lifecycle:1.3.4")
    implementation("androidx.camera:camera-view:1.3.4")
    
    // Image loading - removed for build issues
    // implementation("io.coil-kt:coil-compose:2.7.0")

    implementation(platform("com.google.firebase:firebase-bom:33.2.0"))
    implementation("com.google.firebase:firebase-messaging-ktx")
    implementation("com.google.firebase:firebase-analytics-ktx")
    implementation("com.google.firebase:firebase-crashlytics-ktx")
    implementation("com.google.firebase:firebase-auth-ktx")
    implementation("com.google.firebase:firebase-appcheck-debug")
}

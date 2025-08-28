# React Native / Hermes
-keep class com.facebook.react.** { *; }
-keep class com.facebook.hermes.** { *; }
-keep class com.facebook.jni.** { *; }
-keep class com.facebook.soloader.** { *; }

# Expo / common RN libs
-keep class expo.modules.** { *; }
-keep class com.swmansion.reanimated.** { *; }
-keep class com.swmansion.gesturehandler.** { *; }
-keep class app.notifee.** { *; }
-keep class io.invertase.** { *; }

# Kotlin metadata
-keep class kotlin.** { *; }
-keep class kotlinx.** { *; }
-dontwarn kotlin.**, kotlinx.**, com.facebook.**

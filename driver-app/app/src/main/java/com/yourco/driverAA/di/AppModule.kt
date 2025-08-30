package com.yourco.driverAA.di

import android.content.Context
import androidx.room.Room
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.data.api.AuthInterceptor
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.auth.AuthService
import com.yourco.driverAA.data.db.AppDatabase
import com.yourco.driverAA.data.db.LocationPingDao
import com.yourco.driverAA.domain.JobsRepository
import com.google.firebase.auth.FirebaseAuth
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideRetrofit(authInterceptor: AuthInterceptor): DriverApi {
        val json = Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
        val contentType = "application/json".toMediaType()
        val client = OkHttpClient.Builder()
            .addInterceptor(authInterceptor)
            .build()
        val retrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE.ifEmpty { "https://api.example.com/" })
            .client(client)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
        return retrofit.create(DriverApi::class.java)
    }

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "app.db").build()

    @Provides
    fun provideLocationDao(db: AppDatabase): LocationPingDao = db.locationDao()

    @Provides
    @Singleton
    fun provideJobsRepository(api: DriverApi): JobsRepository = JobsRepository(api)
    
    @Provides
    @Singleton
    fun provideFirebaseAuth(): FirebaseAuth = FirebaseAuth.getInstance()
    
    @Provides
    @Singleton  
    fun provideAuthService(firebaseAuth: FirebaseAuth): AuthService = AuthService(firebaseAuth)
}

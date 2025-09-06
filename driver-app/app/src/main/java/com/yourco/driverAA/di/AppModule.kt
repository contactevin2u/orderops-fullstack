package com.yourco.driverAA.di

import android.content.Context
import androidx.room.Room
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.data.api.AuthInterceptor
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.auth.AuthService
import com.yourco.driverAA.data.db.*
import com.yourco.driverAA.data.network.ConnectivityManager
import com.yourco.driverAA.data.repository.UserRepository
import com.yourco.driverAA.data.sync.SyncManager
import com.yourco.driverAA.domain.JobsRepository
import com.yourco.driverAA.domain.OfflineJobsRepository
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
        // Log API base for debugging
        val apiBase = BuildConfig.API_BASE.ifEmpty { 
            android.util.Log.e("AppModule", "API_BASE is empty! Using fallback URL")
            "https://api.example.com/" 
        }
        android.util.Log.i("AppModule", "Using API base: $apiBase")
        
        val retrofit = Retrofit.Builder()
            .baseUrl(apiBase)
            .client(client)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
        return retrofit.create(DriverApi::class.java)
    }

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
            .fallbackToDestructiveMigration() // For development - remove in production
            .build()

    // DAOs
    @Provides
    fun provideLocationDao(db: AppDatabase): LocationPingDao = db.locationDao()
    
    @Provides
    fun provideJobsDao(db: AppDatabase): JobsDao = db.jobsDao()
    
    @Provides
    fun provideOutboxDao(db: AppDatabase): OutboxDao = db.outboxDao()
    
    @Provides
    fun providePhotosDao(db: AppDatabase): PhotosDao = db.photosDao()
    
    @Provides
    fun provideUIDScansDao(db: AppDatabase): UIDScansDao = db.uidScansDao()

    // Network and Connectivity
    @Provides
    @Singleton
    fun provideConnectivityManager(@ApplicationContext context: Context): ConnectivityManager =
        ConnectivityManager(context)

    // Sync Manager
    @Provides
    @Singleton
    fun provideSyncManager(
        api: DriverApi,
        jobsDao: JobsDao,
        outboxDao: OutboxDao,
        photosDao: PhotosDao,
        uidScansDao: UIDScansDao,
        connectivityManager: ConnectivityManager
    ): SyncManager = SyncManager(api, jobsDao, outboxDao, photosDao, uidScansDao, connectivityManager)

    // Repositories
    @Provides
    @Singleton
    fun provideJobsRepository(
        api: DriverApi,
        jobsDao: JobsDao,
        outboxDao: OutboxDao,
        photosDao: PhotosDao,
        uidScansDao: UIDScansDao,
        syncManager: SyncManager,
        connectivityManager: ConnectivityManager,
        userRepository: UserRepository
    ): JobsRepository = JobsRepository(api, jobsDao, outboxDao, photosDao, uidScansDao, syncManager, connectivityManager, userRepository)
    
    @Provides
    @Singleton
    fun provideOfflineJobsRepository(
        api: DriverApi,
        jobsDao: JobsDao,
        outboxDao: OutboxDao,
        photosDao: PhotosDao,
        uidScansDao: UIDScansDao,
        syncManager: SyncManager,
        connectivityManager: ConnectivityManager
    ): OfflineJobsRepository = OfflineJobsRepository(
        api, jobsDao, outboxDao, photosDao, uidScansDao, syncManager, connectivityManager
    )

    // Firebase
    @Provides
    @Singleton
    fun provideFirebaseAuth(): FirebaseAuth = FirebaseAuth.getInstance()
    
    @Provides
    @Singleton  
    fun provideAuthService(firebaseAuth: FirebaseAuth): AuthService = AuthService(firebaseAuth)
}

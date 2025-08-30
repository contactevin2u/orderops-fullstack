package com.yourco.driverAA.di

import android.content.Context
import androidx.room.Room
import com.yourco.driverAA.BuildConfig
import com.yourco.driverAA.data.api.DriverApi
import com.yourco.driverAA.data.db.AppDatabase
import com.yourco.driverAA.data.db.LocationPingDao
import com.yourco.driverAA.domain.JobsRepository
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
import retrofit2.converter.kotlinx.serialization.asConverterFactory

@Module
@InstallIn(SingletonComponent::class)
object AppModule {
    @Provides
    @Singleton
    fun provideRetrofit(): DriverApi {
        val json = Json {
            ignoreUnknownKeys = true
            isLenient = true
        }
        val contentType = "application/json".toMediaType()
        val retrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE.ifEmpty { "https://api.example.com/" })
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
        return retrofit.create(DriverApi::class.java)
    }

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase =
        Room.databaseBuilder(context, AppDatabase::class.java, "app.db")
            .addMigrations(AppDatabase.MIGRATION_1_2)
            .build()

    @Provides
    fun provideLocationDao(db: AppDatabase): LocationPingDao = db.locationDao()

    @Provides
    @Singleton
    fun provideJobsRepository(api: DriverApi): JobsRepository = JobsRepository(api)
}

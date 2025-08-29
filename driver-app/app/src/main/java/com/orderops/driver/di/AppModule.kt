package com.orderops.driver.di

import android.content.Context
import androidx.room.Room
import com.orderops.driver.BuildConfig
import com.orderops.driver.data.api.DriverApi
import com.orderops.driver.data.db.AppDatabase
import com.orderops.driver.data.db.LocationPingDao
import com.orderops.driver.domain.JobsRepository
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
        val contentType = "application/json".toMediaType()
        val retrofit = Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE)
            .client(OkHttpClient.Builder().build())
            .addConverterFactory(Json.asConverterFactory(contentType))
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
    fun provideJobsRepository(): JobsRepository = JobsRepository()
}

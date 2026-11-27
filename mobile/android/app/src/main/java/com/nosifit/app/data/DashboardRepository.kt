package com.nosifit.app.data

class DashboardRepository(private val api: ApiClient) {
    suspend fun today(): DashboardToday = api.get("dashboard/today")
}

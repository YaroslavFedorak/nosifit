package com.nosifit.app

import android.app.Application
import com.nosifit.app.data.DashboardRepository
import com.nosifit.app.data.Session

/** Holds the app-wide objects; screens get them from here. */
class NosiFitApplication : Application() {
    lateinit var session: Session
        private set
    lateinit var dashboard: DashboardRepository
        private set

    override fun onCreate() {
        super.onCreate()
        session = Session(this)
        dashboard = DashboardRepository(session.api)
    }
}

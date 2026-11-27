// Inside android { } the name "java" is the Java extension, not the package.
import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

// The app's version is the product's: VERSION at the root of the repository
// (docs/versioning.md). Google Play also needs an always-growing integer;
// MAJOR.MINOR.PATCH packs into one (0.2.0 -> 2000, 1.4.12 -> 1004012).
val appVersion = rootProject.file("../../VERSION").readText().trim()
val appVersionCode = appVersion.split(".").map { it.toInt() }.let { (major, minor, patch) ->
    major * 1_000_000 + minor * 1_000 + patch
}

// The server the app talks to unless the user changes it on the sign-in
// screen. Override per build: ./gradlew assembleRelease -Pnosifit.apiUrl=https://your.domain/
val releaseApiUrl = (findProperty("nosifit.apiUrl") as String?) ?: "https://nosifit-production.up.railway.app/"
// The Android emulator reaches the computer's localhost as 10.0.2.2 (flask run on port 5000).
val debugApiUrl = (findProperty("nosifit.debugApiUrl") as String?) ?: "http://10.0.2.2:5000/"

android {
    namespace = "com.nosifit.app"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nosifit.app"
        minSdk = 26
        targetSdk = 35
        versionCode = appVersionCode
        versionName = appVersion

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    // Release signing comes from keystore.properties (never committed), see mobile/README.md.
    val keystoreFile = rootProject.file("keystore.properties")
    if (keystoreFile.exists()) {
        val props = Properties().apply { keystoreFile.inputStream().use { load(it) } }
        signingConfigs {
            create("release") {
                storeFile = rootProject.file(props.getProperty("storeFile"))
                storePassword = props.getProperty("storePassword")
                keyAlias = props.getProperty("keyAlias")
                keyPassword = props.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            versionNameSuffix = "-debug"
            buildConfigField("String", "DEFAULT_API_URL", "\"$debugApiUrl\"")
        }
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
            buildConfigField("String", "DEFAULT_API_URL", "\"$releaseApiUrl\"")
            signingConfigs.findByName("release")?.let { signingConfig = it }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    implementation(libs.androidx.compose.material.icons)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.okhttp)
    debugImplementation(libs.androidx.compose.ui.tooling)

    testImplementation(libs.junit)
    testImplementation(libs.okhttp.mockwebserver)
    testImplementation(libs.kotlinx.coroutines.test)
}

# NosiFit mobile apps

Two native apps that use the same JSON API as the website and the Telegram bot.

| | Android | iOS |
|---|---|---|
| Folder | `mobile/android` | `mobile/ios` |
| Language, UI | Kotlin, Jetpack Compose, Material 3 | Swift, SwiftUI |
| Minimum OS | Android 8.0 (API 26) | iOS 16 |
| Network | OkHttp + kotlinx.serialization | URLSession + Codable |
| Token storage | Android Keystore (AES-GCM) | Keychain, this device only |
| Store package | `.aab` for Google Play (`.apk` for testing) | `.ipa` through App Store Connect |

## What works now (v0.1.0)

- Sign in with email and password. The server returns a bearer token
  (`POST /api/v1/mobile/auth/login`), and every later request sends
  `Authorization: Bearer <token>`.
- The consent screen, when the account has not accepted the current privacy
  policy yet (the same three answers as the website's `/consent` page).
- **Today**: the day's score, and training, nutrition and recovery for today
  (`GET /api/v1/dashboard/today`). Pull down to refresh.
- Bottom tabs: Today, Nutrition, Training, Recovery, Profile. Nutrition,
  Training and Recovery have a button for now that opens that section on the website.
- Profile: who is signed in, and signing out (the token is revoked on the server).
- English and Ukrainian, following the phone's language.

The server address is set at build time (debug: a local server, release:
production). It can also be changed on the sign-in screen under "Server".

## How sign-in works on the server

- `api/routes/mobile.py`: `login`, `session`, `logout` under `/api/v1/mobile/auth/`.
- `auth/mobile_token.py`: Flask-Login reads the bearer token on `/api/` paths only.
  Pages, sign-in forms and account settings stay with browser sessions.
- `backend/app/services/mobile_auth.py`, `backend/app/models/mobile_token.py`:
  only the SHA-256 of a token is stored. A token dies on sign-out, after 90 days,
  when the password changes, or when the account is deleted. Withdrawing consent
  keeps it, so the app can show the consent screen again.
- Login shares its rate limits with the website's form.
- Tests: `web/tests/security/test_mobile_auth.py`.

## Android

Requirements: Android Studio (or JDK 17 with the Android SDK).

```bash
cd mobile/android
./gradlew assembleDebug          # app/build/outputs/apk/debug/app-debug.apk
./gradlew testDebugUnitTest      # unit tests
./gradlew installDebug           # onto a connected phone or a running emulator
```

Or open `mobile/android` in Android Studio and press Run.

The debug build talks to `http://10.0.2.2:5000/`, which is how the emulator
reaches `python run.py` on your computer. On a real phone, under "Server" on
the sign-in screen, enter your computer's address on the same Wi-Fi, e.g.
`http://192.168.1.20:5000`, and start Flask with `--host 0.0.0.0`. Or set it
at build time: `./gradlew assembleDebug -Pnosifit.debugApiUrl=http://192.168.1.20:5000/`.

Every push that changes `mobile/` builds a debug APK on GitHub Actions
(workflow **Mobile apps**, artifact `nosifit-android-debug-apk`). Download it,
unzip it, and install the `.apk` on your phone.

### Release build for Google Play

1. Create an upload key once (and keep it safe, outside the repository):
   `keytool -genkeypair -v -keystore nosifit-upload.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload`
2. Create `mobile/android/keystore.properties` (it is in `.gitignore`):
   ```properties
   storeFile=/full/path/to/nosifit-upload.jks
   storePassword=...
   keyAlias=upload
   keyPassword=...
   ```
3. `./gradlew bundleRelease -Pnosifit.apiUrl=https://your-domain/` gives
   `app/build/outputs/bundle/release/app-release.aab`, the file Google Play takes.
4. In the Google Play Console ($25 once), create the app, fill in the store
   listing, the data safety form (the app sends health data to your server) and
   the privacy policy URL (`https://your-domain/privacy`), then upload the `.aab`
   to internal testing first.

## iOS

Requirements: a Mac with Xcode 15 or newer, and [XcodeGen](https://github.com/yonaskolb/XcodeGen).
The Xcode project is generated from `project.yml`, so it never has merge conflicts.

```bash
brew install xcodegen
cd mobile/ios
xcodegen                         # creates NosiFit.xcodeproj
open NosiFit.xcodeproj           # choose a simulator and press Run
```

The debug build talks to `http://localhost:5000/`, which is how the simulator
reaches `python run.py` on the same Mac. For a real iPhone, enter the Mac's
address on the same Wi-Fi under "Server" on the sign-in screen.

GitHub Actions builds the app and runs its tests on an iOS simulator on every
push that changes `mobile/`.

### Release for the App Store

1. Join the Apple Developer Program ($99/year).
2. In `project.yml`, set `DEVELOPMENT_TEAM` to your team ID and the release
   `NOSIFIT_API_URL` to your domain, then run `xcodegen` again.
3. In Xcode: Product → Archive → Distribute App → App Store Connect.
4. In App Store Connect: create the app (bundle ID `com.nosifit.app`), fill in
   the privacy section (health and fitness data, linked to the user), add the
   privacy policy URL and test through TestFlight before submitting.

## Next steps

1. Nutrition in the apps: the diary, adding food (search, barcode with the camera), water.
2. Training: today's workout and logging sets.
3. Recovery: sleep and habits.
4. Registration and password reset in the app (today: on the website).
5. A list of signed-in devices in the profile, with "sign out everywhere".
6. Before publishing: a Google and Apple sign-in, push reminders, store screenshots.

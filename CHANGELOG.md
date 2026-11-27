# Changelog

Every version of NosiFit and what changed in it. The website, the API, the
Telegram bot and the mobile apps share one version number (`VERSION`); how
it is chosen is in [docs/versioning.md](docs/versioning.md).

While the version starts with 0 the product is in beta; 1.0.0 will be the
public launch. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-11-27

### Added

- Android and iOS apps (`mobile/`): sign-in, the consent screen, Today
  (the day's score, training, nutrition and recovery), bottom tabs and the
  profile, in English and Ukrainian. A debug APK is built on every change
  to `mobile/`.
- Sign-in for the apps: `POST /api/v1/mobile/auth/login` returns a bearer
  token accepted by the whole API; `GET /mobile/auth/session` and
  `POST /mobile/auth/logout` complete it.
- Version numbers: this changelog, a release on GitHub for every version,
  and the version in the settings, in `/healthz`, in the `NosiFit-Version`
  header of API responses and in the apps' profile.

### Changed

- Signed-in pages show their content 26-38% sooner on a phone: the page's
  code, language and data are requested together instead of one after
  another, and only the page's language is loaded.
- Server texts stay in the browser cache until they change.
- Responses are compressed with brotli first, 8-11% smaller than before.
- The dashboard recommendation and the recovery day details analyse the
  training history once per request instead of twice.

### Fixed

- Clients that accept only gzip received the website's files uncompressed.
- `/api/dashboard/today` read each meal's items with a separate query.

## [0.1.0] - 2026-09-30

The first beta, tagged `v0.1.0-beta`: training, nutrition and recovery
tracking with the daily dashboard, accounts with Google, GitHub and
Telegram sign-in, the Telegram bot, and English, Ukrainian, Polish and
Russian.

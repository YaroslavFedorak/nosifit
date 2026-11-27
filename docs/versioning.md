# Versions and releases

NosiFit has one version number for everything: the website, the JSON API,
the Telegram bot and the Android and iOS apps. It lives in
[`VERSION`](../VERSION) and every merge into `main` is a new one.

## The number

[Semantic Versioning](https://semver.org): `MAJOR.MINOR.PATCH`.

| Part | Raised when | Example |
|---|---|---|
| PATCH | a fix or a small improvement; nothing new to learn | 0.2.0 → 0.2.1 |
| MINOR | something new: a feature, a screen, an endpoint | 0.2.1 → 0.3.0 |
| MAJOR | after 1.0.0, a change that breaks what existed (API v2, a removed feature) | 1.4.2 → 2.0.0 |

- **0.x is the beta.** While MAJOR is 0 the product is in beta: the website
  shows "NosiFit 0.2.0 · beta" and GitHub marks those releases as
  pre-releases. The stage is not written into the number.
- **1.0.0 is the public launch,** decided on purpose, not reached by bumping.
- Raising one part resets the parts after it: 0.3.4 + MINOR = 0.4.0.
- A number is never reused. A mistake in 0.4.0 is fixed in 0.4.1.
- The first beta was tagged `v0.1.0-beta`; from 0.2.0 on, tags are `vX.Y.Z`.

## Releasing: what every pull request does

Every pull request into `main` is a release, so it raises the version:

```bash
python -m web.scripts.version bump minor   # or patch / major
```

This writes the new number into `VERSION` and every file that repeats it
(the two `package.json` files and their lock files, the iOS project with its
build number) and opens a section for it at the top of
[`CHANGELOG.md`](../CHANGELOG.md). Fill that section in: what a user of the
website, the bot or the apps notices, under *Added*, *Changed*, *Fixed* or
*Removed* ([Keep a Changelog](https://keepachangelog.com/en/1.1.0/)).

Several pull requests open at the same time each raise the number; whichever
merges second updates its branch and takes the next one.

## What checks and does it

- **CI** (`.github/workflows/ci.yml`, job `version`) fails a pull request
  whose `VERSION` is not higher than `main`'s, whose copies disagree, or
  whose CHANGELOG has no entry for it: `python -m web.scripts.version check`.
- **Release** (`.github/workflows/release.yml`): on every push to `main`,
  if the version has no tag yet, it creates tag `vX.Y.Z` and a GitHub
  Release whose text is the version's CHANGELOG section
  (`python -m web.scripts.version notes`). Railway deploys the same commit.

## Where the number shows

| Where | How |
|---|---|
| Website | the bottom of Settings: "NosiFit 0.2.0 · beta" |
| API | every response under `/api/` has the header `NosiFit-Version: 0.2.0` |
| Health check | `GET /healthz` → `{"status": "ok", "version": "0.2.0", "commit": "3de09b1"}` (the commit on Railway) |
| Android | `versionName` from `VERSION`; `versionCode` packs it into one number (0.2.0 → 2000, 1.4.12 → 1004012), as Google Play needs a growing integer. Shown in the profile |
| iOS | `MARKETING_VERSION` and the build number `CURRENT_PROJECT_VERSION` (packed the same way) in `mobile/ios/project.yml`. Shown in the profile |
| Open Food Facts | the User-Agent of barcode lookups: `NosiFit/0.2.0 (...)` |
| GitHub | tags `vX.Y.Z` and the Releases page |

In code, `shared.version.app_version()` reads the number and
`shared.version.release_stage()` says whether it is the beta.

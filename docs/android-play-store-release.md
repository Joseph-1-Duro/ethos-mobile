# Android Google Play release automation

Automates Google Play submission for the Android app (#464): signed release bundle, upload
to the internal testing track, generated "What's new", gated promotion to production as a
staged rollout, and rollout controls (increase / complete / halt).

- Workflow: [`.github/workflows/android-play-store-release.yml`](../.github/workflows/android-play-store-release.yml)
- Lanes: [`android/fastlane/Fastfile`](../android/fastlane/Fastfile). fastlane 2.240.1 and Ruby
  3.3.12 are pinned in the repo-root `Gemfile`/`.ruby-version`, shared with the
  [iOS release](ios-app-store-release.md).
- Release notes: [`.github/scripts/generate_release_notes.py`](../.github/scripts/generate_release_notes.py) `--platform android`
  (tests in `.github/scripts/tests/`, run by iOS CI's unittest step)

## What gets shipped: an AAB, not an APK

Google Play requires Android App Bundles (`.aab`) for new apps, and Play generates optimized
APKs per device from them. The pipeline builds `bundleRelease` and uploads the AAB (plus the
R8 `mapping.txt`, so Play Console shows deobfuscated crashes). APKs are still produced by
`android-ci.yml` for CI checks, but never uploaded.

## How a release flows

```
git tag v1.2.0 ──► internal job (ubuntu-24.04, JDK 17)
                    1. validate: tag == versionName, release notes (≤ 500 chars), locale folders
                    2. versionCode = highest on Google Play (internal/alpha/beta/production) + 1
                    3. bundleRelease, signed with the upload key (ANDROID_KEYSTORE_*)
                    4. verify_cert_pins.py (same gate as android-ci.yml) + confirm the AAB is signed
                    5. upload_to_play_store → internal track, release notes per language
                          │
                          ▼ only if promotion was requested
                   production job ── waits for approval on the `play-production` environment
                    6. promote that versionCode internal → production as a staged rollout
                       (status inProgress, default 10% of users)

later, from Actions > Run workflow (rollout_action), also behind `play-production`:
    increase → raise the fraction      complete → 100%      halt → stop serving it
```

**By default a release goes to the internal testing track only.** Nothing reaches production
unless someone asks for it (the `promote_to_production` input, the `promote` rollout action,
or the `ANDROID_PROMOTE_TO_PRODUCTION_ON_TAG` variable for tags) **and** a required reviewer
approves the `play-production` environment.

Committing a production change sends it for Google's review, following the app's Play
Console settings. With **Managed publishing** on, approved changes wait until someone presses
"Publish" in Play Console. Staged rollouts only apply to production; internal testing always
reaches all internal testers.

The workflow never runs on `pull_request`. Uploads are refused from any ref other than
`main` or a `vX.Y.Z` tag. One release runs at a time (`concurrency`).

## Cutting a release

1. Bump `versionName` in `android/app/build.gradle.kts`. Tags are shared with iOS, so bump
   iOS `MARKETING_VERSION` to the same `X.Y.Z` in the same PR. Each platform's workflow
   refuses a tag that doesn't match its version. Don't touch `versionCode`: CI sets it.
2. Optionally commit notes to `android/fastlane/release_notes/<versionName>/en-US.txt`.
3. Merge to `main`, then tag: `git tag v1.2.0 && git push origin v1.2.0`.
4. Test the internal build. To go to production, run the workflow with
   `rollout_action: promote`, `version_code: <the internal versionCode>`, `dry_run` off, and
   the fraction you want. Then approve `play-production`. This promotes the exact bundle
   you tested. Alternatively, `promote_to_production` promotes right after a fresh upload.
5. Watch Play Console (Android vitals, crashes), then `increase` or `complete` the rollout,
   or `halt` it.

### Manual run inputs

| Input | Default | Effect |
| --- | --- | --- |
| `dry_run` | **true** | Validates, builds the release AAB, and prints the plan. Uploads and changes nothing. |
| `promote_to_production` | false | After the internal upload, the `production` job promotes that build (after approval). |
| `rollout_fraction` | `0.1` | Staged rollout fraction for promote/increase/halt (`0.1` = 10%). `1` = everyone (promote only). |
| `rollout_action` | `none` | `none` builds and uploads. `promote` / `increase` / `complete` / `halt` manage production **without building** (see below). |
| `version_code` | empty | The internal-track versionCode to promote (`rollout_action: promote`). |
| `release_notes` | empty | Replaces generated notes for every language (max 500 characters). |

### Staged rollout controls

| Action | Inputs | What happens on Google Play |
| --- | --- | --- |
| `promote` | `version_code`, `rollout_fraction` | Copies that release (with its notes) from internal to production: `inProgress` at the fraction, or `completed` if the fraction is `1`. |
| `increase` | `rollout_fraction` | Raises the production `inProgress` release to the new fraction. Play only accepts increases. |
| `complete` | none | Sets the production release to `completed`: 100% of users. |
| `halt` | `rollout_fraction` (the current one) | Sets the release to `halted`: no new users get it, and existing installs stay. |

To resume a **halted** rollout, use Play Console (Release > Production > Resume rollout).
fastlane's `supply` can only update `inProgress`/`draft` releases, so a halted one can't be
resumed from CI. Rolling back means halting, then shipping a fixed higher versionCode.

Dry runs of these actions use an unprotected `play-dry-run` environment (created
automatically on first use), so they don't need approval.

### Dry run

Run the workflow with `dry_run` checked (the default). It checks the tag/version match,
release notes generation (and the 500-character limit), locale folders, and the rollout
fraction. It builds the release AAB (unsigned: a dry run doesn't decode the keystore) and
runs the certificate-pin check in warn mode. It then prints what it would upload,
promote or change.

Locally (from `android/`):

```sh
bundle install
bundle exec fastlane android validate
bundle exec fastlane android internal dry_run:true
bundle exec fastlane android production dry_run:true version_code:42 rollout:0.1
bundle exec fastlane android rollout dry_run:true action:increase rollout:0.5
```

## Secrets and variables

Settings > Secrets and variables > Actions. Nothing below is ever committed. The lanes
fail with the list of missing names.

| Name | Kind | Used by | What it is / how to create it |
| --- | --- | --- | --- |
| `PLAY_SERVICE_ACCOUNT_JSON_BASE64` | secret | all jobs | Service-account JSON key, base64-encoded: `base64 -w0 key.json`. Decoded in memory only. See below. |
| `ANDROID_KEYSTORE_BASE64` | secret | internal | The **upload** keystore, base64-encoded: `base64 -w0 upload-keystore.jks`. Decoded to the runner's temp dir and deleted after the build. |
| `ANDROID_KEYSTORE_PASSWORD` | secret | internal | Keystore password. |
| `ANDROID_KEY_ALIAS` | secret | internal | Alias of the upload key in that keystore. |
| `ANDROID_KEY_PASSWORD` | secret | internal | Password of that key. |
| `ETHOS_CERT_PINS` | secret (exists) | internal | Already used by Android CI. Real release builds fail without valid pins (`verify_cert_pins.py`). |
| `SENTRY_DSN` | secret (optional) | internal | Compiled into release builds for crash reporting (#425). Unset = reporting off. |
| `ANDROID_PROMOTE_TO_PRODUCTION_ON_TAG` | variable (optional) | internal | `true` to request production promotion on every tag push (still gated). |
| `PLAY_ROLLOUT_FRACTION` | variable (optional) | internal | Fraction used for tag-triggered promotion. Default `0.1`. |
| `PLAY_INTERNAL_RELEASE_STATUS` | variable (optional) | internal | `draft` while the app has never been published (Play only accepts draft releases then). Default `completed`. |
| `PLAY_CHANGES_NOT_SENT_FOR_REVIEW` | variable (optional) | all jobs | `true` if Play Console rejects edits with "changes not sent for review". fastlane already retries with this automatically (`rescue_changes_not_sent_for_review`). |
| `PLAY_DEFAULT_LOCALE` | variable (optional) | all jobs | The listing's default language. Default `en-US`. |

### Google Play service account

1. Google Cloud console: create (or pick) a project, enable the **Google Play Android
   Developer API**, and create a **service account**. Add a **JSON key** and download it once.
2. Play Console > Users and permissions > **Invite new users**, and invite the service
   account's e-mail. Give it **app-level** permissions for Ethos only: *View app information
   (read-only)*, *Release apps to testing tracks*, *Manage testing tracks and edit tester
   lists*, and *Release to production, exclude devices, and use Play App Signing*.
   Account-wide admin isn't needed.
3. Store it: `base64 -w0 key.json` → `PLAY_SERVICE_ACCOUNT_JSON_BASE64`. Delete the local
   copy, or keep it in a password manager.

New service-account permissions can take a while (sometimes up to a day) before the API accepts them.

### Upload keystore and Play App Signing

With Play App Signing (mandatory for AABs), Google holds the **app signing key**. CI only
holds the **upload key**. If the upload key leaks, it can be reset in Play Console without
affecting users.

- No keystore yet:
  ```sh
  keytool -genkeypair -v -keystore upload-keystore.jks -storetype JKS \
    -alias upload -keyalg RSA -keysize 2048 -validity 10000
  ```
- Enrol in Play App Signing when creating the first release in Play Console (the default).
- Store the four `ANDROID_KEYSTORE_*` / `ANDROID_KEY_*` secrets. `app/build.gradle.kts`
  already reads the path and passwords from the environment. Without them, a release build is
  left unsigned, and the pipeline refuses to upload an unsigned bundle.
- `*.jks` and `*.keystore` are git-ignored, and the `check-sensitive-files` pre-commit hook
  also blocks them (and `gradle.properties` edits) from being committed.

### `play-production` environment (the approval gate)

Settings > Environments > **New environment** `play-production`:

1. **Required reviewers**: the maintainers allowed to release to production (enable
   "Prevent self-review" if available).
2. **Deployment branches and tags**: "Selected branches and tags", with `main` and `v*`.
3. Optional: move `PLAY_SERVICE_ACCOUNT_JSON_BASE64` into this environment, and give the
   internal job a separate, testing-only service account.

## The first release is manual (Play API limitation)

The Google Play Developer API can't create an app or upload its very first bundle. Before
this pipeline can run:

1. Create the app in Play Console with package name **`com.ethosprotocol`** (from
   `app/build.gradle.kts`). The package name can never change.
2. Upload the first signed AAB **by hand**, e.g. to Internal testing, and accept Play App
   Signing:
   ```sh
   cd android && ETHOS_VERSION_CODE=1 ./gradlew bundleRelease   # with the ANDROID_KEYSTORE_* env set
   ```
3. Complete the Play Console set-up tasks (store listing, content rating, data safety,
   target audience, app access, ads declaration). Until the app is published, set
   `PLAY_INTERNAL_RELEASE_STATUS=draft`.

It's unknown from this repository whether the app already exists on Google Play. Check
before the first run.

## versionCode rules

- Every upload needs a **strictly higher** `versionCode` than any bundle ever uploaded
  (even deleted drafts). It must be at most 2,100,000,000.
- CI sets it to the highest versionCode on the internal/alpha/beta/production tracks + 1,
  and passes it to Gradle as `ETHOS_VERSION_CODE`. Local builds keep `versionCode = 1`.
- If Play rejects a code (e.g. one used on a custom closed track or by a deleted upload), set
  `VERSION_CODE=<n>` for a local run, or re-run after the next upload.
- `versionName` (`X.Y.Z`) is what users see. It must match the release tag.

## Release notes

Same generator and rules as iOS, with `--platform android`:

- **Kept:** `feat:` → "New", `perf:` → "Improvements", `fix:` → "Fixes" (PR titles since the previous `v*` tag).
- **Dropped:** `chore`/`ci`/`test`/`docs`/`build`/`refactor`/`style`, non-conventional titles,
  **iOS-only scopes** (`fix(ios): ...`), and reference-only titles. `#123` refs are stripped.
- **500 characters per language** (Google Play's limit), trimmed by whole bullets, Fixes
  first, never mid-word. With nothing user-facing, the text is "Bug fixes and performance
  improvements."
- **Languages:** folders in `android/fastlane/metadata/android/` (see its README). Languages
  without their own text get the default language's.
- **Overrides** (highest first): `android/fastlane/release_notes/<versionName>/<locale>.txt`,
  then the `release_notes` input, then generated. An override over 500 characters fails the run.
- The notes are attached to the internal release and carried along when it's promoted.

The listing itself (title, descriptions, graphics) is never uploaded. It stays in Play Console.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Tag vX does not match versionName Y` | Bump `versionName` (and iOS's version), commit, re-tag. |
| `Missing required secrets/variables: ...` | Add the listed names. Fork runs never have them, which is expected. |
| `... is not signed; check the upload keystore secrets` | One of the four `ANDROID_KEYSTORE_*` / `ANDROID_KEY_*` secrets is missing or wrong. |
| `verify_cert_pins.py` fails | Set real `ETHOS_CERT_PINS` (see `docs/cert-pin-rotation-runbook.md`). |
| `The caller does not have permission` / 401 / 403 | Service account not invited in Play Console, missing app permissions, or permissions still propagating. |
| `Package not found: com.ethosprotocol` | The app doesn't exist in Play Console yet, or the first manual upload is missing (see above). |
| `Only releases with status draft may be created on draft app` | Set `PLAY_INTERNAL_RELEASE_STATUS=draft` until the app is published. |
| `APK specifies a version code that has already been used` | Re-run with `VERSION_CODE` above the reported code. |
| `Changes cannot be sent for review automatically` | Set `PLAY_CHANGES_NOT_SENT_FOR_REVIEW=true`, then send for review in Play Console. |
| `Unable to find the requested release on track - 'production'` (rollout) | No `inProgress` production release: nothing to increase, or it's halted (resume in Play Console). |
| `Track 'internal' doesn't have any releases` (promote) | Wrong `version_code`: use the one from the internal upload's summary. |

## First-run checklist for maintainers

- [ ] App exists in Play Console as `com.ethosprotocol`, with the first AAB uploaded manually and Play App Signing enabled.
- [ ] Play Console set-up tasks done (listing, content rating, data safety, target audience, app access, ads).
- [ ] Service account created and invited with the app-level permissions above.
- [ ] Secrets set: `PLAY_SERVICE_ACCOUNT_JSON_BASE64`, `ANDROID_KEYSTORE_BASE64`, `ANDROID_KEYSTORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, real `ETHOS_CERT_PINS` (and optionally `SENTRY_DSN`).
- [ ] `PLAY_INTERNAL_RELEASE_STATUS=draft` if the app isn't published yet.
- [ ] Environment `play-production` created with required reviewers, restricted to `main` and `v*`.
- [ ] Listing languages added as folders in `android/fastlane/metadata/android/` (optional; default `en-US`).
- [ ] **Dry run:** Actions > Android Play Store Release > Run workflow on `main` (defaults). Expect a green bundle build.
- [ ] **Internal:** tag `vX.Y.Z` (with iOS bumped too) or run with `dry_run` off. Check the build and notes in Play Console > Internal testing.
- [ ] **Production:** `rollout_action: promote` with that `version_code` and `rollout_fraction: 0.1`; approve `play-production`. Then `increase` / `complete` / `halt` as needed.

## Follow-ups

- Share the small helper block duplicated between the iOS and Android Fastfiles.
- Upload the Play listing text and graphics from git (`supply` metadata), if maintainers want it versioned.
- Create a GitHub Release from the tag (would feed `release-notes-parity-check.yml`).

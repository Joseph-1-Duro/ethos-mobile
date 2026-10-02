# Google Play listing locales

The release pipeline never uploads listing text, images or screenshots. The Play
listing stays managed in Play Console. This folder only tells the release notes
generator which languages need "What's new" text.

Add one empty folder per Play Console listing language, using Google Play's codes
(`en-US`, `de-DE`, `fr-FR`, `es-419`, ...), with a `.gitkeep` inside:

```
metadata/android/
  en-US/.gitkeep
  de-DE/.gitkeep
```

- Without any folders, release notes are published for `en-US` only (or `PLAY_DEFAULT_LOCALE`).
- Each folder gets the default locale's text unless there's an override in
  `../../release_notes/<versionName>/<locale>.txt`.
- `fastlane android validate` rejects folder names that aren't Google Play language codes.
- Google Play limits release notes to **500 characters per language**.

# Release notes overrides (Google Play)

Google Play's "What's new" is generated from the conventional-commit PR titles merged
since the previous `v*` tag (`.github/scripts/generate_release_notes.py --platform android`).
iOS-only changes (`fix(ios): ...`) are left out. To replace the text for one version,
commit hand-written notes here before tagging:

```
release_notes/
  1.1.0/            # versionName from app/build.gradle.kts
    en-US.txt       # default locale; also used by languages without their own file
    de-DE.txt       # optional per-language translation
```

Precedence, highest first:

1. `release_notes/<versionName>/<locale>.txt`
2. The `release_notes` input of a manual workflow run (applies to every language)
3. Generated notes

Google Play allows **500 characters per language**. Generated notes are trimmed by
whole bullets; an override longer than 500 characters fails the run rather than being cut.

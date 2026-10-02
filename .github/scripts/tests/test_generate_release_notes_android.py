#!/usr/bin/env python3
"""Google Play (--platform android) tests for generate_release_notes.py.

The iOS behaviour is covered, unchanged, by test_generate_release_notes.py.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "generate_release_notes.py"

_spec = importlib.util.spec_from_file_location("generate_release_notes_android", SCRIPT_PATH)
notes_module = importlib.util.module_from_spec(_spec)
sys.modules["generate_release_notes_android"] = notes_module  # for @dataclass
_spec.loader.exec_module(notes_module)

Commit = notes_module.Commit
PLAY_LIMIT = 500


def entries_for(commits, platform="android"):
    return notes_module.collect_entries(commits, platform)


class PlatformScopeTests(unittest.TestCase):
    def test_android_notes_drop_ios_only_and_keep_android_and_shared(self):
        commits = [
            Commit("fix(ios): widget refresh on lock screen"),
            Commit("fix(android): correct RTL padding on vault card"),
            Commit("fix(android,ios): keep session after token refresh"),
            Commit("feat(vault): export vault summary"),
        ]
        texts = [e.text for e in entries_for(commits)]
        self.assertEqual(texts, [
            "Correct RTL padding on vault card",
            "Keep session after token refresh",
            "Export vault summary",
        ])

    def test_default_platform_is_still_ios(self):
        classify = notes_module.classify
        self.assertIsNone(classify(Commit("fix(android): correct padding")))
        self.assertIsNotNone(classify(Commit("fix(ios): correct padding")))
        self.assertEqual(notes_module.PLATFORM_LIMITS[notes_module.DEFAULT_PLATFORM], 4000)

    def test_unknown_scopes_are_kept_on_both_platforms(self):
        commit = Commit("feat(widgets): add countdown")
        self.assertIsNotNone(notes_module.classify(commit, "android"))
        self.assertIsNotNone(notes_module.classify(commit, "ios"))


class PlayLimitTests(unittest.TestCase):
    def test_trims_to_500_characters_by_whole_bullets(self):
        commits = [Commit(f"feat: add vault feature number {i} with a longer description")
                   for i in range(20)]
        commits += [Commit(f"fix: repair crash number {i} when opening a vault") for i in range(20)]
        entries = entries_for(commits)
        notes = notes_module.build_notes(entries, limit=PLAY_LIMIT)

        self.assertLessEqual(len(notes), PLAY_LIMIT)
        full_texts = {e.text for e in entries}
        bullets = [line[2:] for line in notes.splitlines() if line.startswith("• ")]
        self.assertTrue(bullets)
        # No cut-off words: every bullet is a complete entry.
        for bullet in bullets:
            self.assertIn(bullet, full_texts)
        # Lowest-priority section (Fixes) goes first.
        self.assertNotIn("Fixes", notes)

    def test_limit_counts_characters_not_bytes(self):
        # 499 characters including the multi-byte bullet; must fit Play's 500.
        text = "x" * (499 - len("New\n• ") - 1)
        notes = notes_module.build_notes(entries_for([Commit(f"feat: a {text}")]), limit=PLAY_LIMIT)
        self.assertLessEqual(len(notes), PLAY_LIMIT)
        self.assertGreater(len(notes.encode("utf-8")), PLAY_LIMIT)
        self.assertTrue(notes.startswith("New\n"))

    def test_override_over_500_is_rejected_but_500_is_accepted(self):
        ok = notes_module.notes_by_locale(
            generated="g", locales=["en-US"], default_locale="en-US",
            override_text="a" * PLAY_LIMIT, limit=PLAY_LIMIT,
        )
        self.assertEqual(len(ok["en-US"]), PLAY_LIMIT)
        with self.assertRaises(ValueError):
            notes_module.notes_by_locale(
                generated="g", locales=["en-US"], default_locale="en-US",
                override_text="a" * (PLAY_LIMIT + 1), limit=PLAY_LIMIT,
            )


class PlayLocaleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def test_play_locale_folders_including_numeric_regions(self):
        for name in ("en-US", "es-419", "de-DE", "images"):
            (self.tmp / name).mkdir()
        self.assertEqual(
            notes_module.resolve_locales("en-US", str(self.tmp)),
            ["en-US", "de-DE", "es-419"],
        )

    def test_locales_without_text_fall_back_to_default_override(self):
        overrides = self.tmp / "overrides"
        overrides.mkdir()
        (overrides / "en-US.txt").write_text("English notes\n", encoding="utf-8")
        (overrides / "de-DE.txt").write_text("Deutsche Notizen\n", encoding="utf-8")
        notes = notes_module.notes_by_locale(
            generated="generated", locales=["en-US", "de-DE", "es-419"],
            default_locale="en-US", override_dir=str(overrides), limit=PLAY_LIMIT,
        )
        self.assertEqual(notes, {
            "en-US": "English notes",
            "de-DE": "Deutsche Notizen",
            "es-419": "English notes",
        })


class AndroidCommandLineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)

    def run_main(self, *args):
        stdout = io.BytesIO()
        fake = io.TextIOWrapper(stdout, encoding="utf-8")
        with contextlib.redirect_stdout(fake), contextlib.redirect_stderr(io.StringIO()):
            code = notes_module.main(list(args))
            fake.flush()
        return code, stdout.getvalue().decode("utf-8")

    def log(self, commits):
        path = self.tmp / "log.json"
        path.write_text(json.dumps([{"subject": c} for c in commits]), encoding="utf-8")
        return str(path)

    def test_platform_android_defaults_to_the_play_limit(self):
        commits = [f"feat: add feature number {i} to the vault screen" for i in range(40)]
        code, stdout = self.run_main("--output-dir", str(self.tmp / "out"),
                                     "--log-file", self.log(commits), "--platform", "android")
        self.assertEqual(code, 0)
        self.assertLessEqual(len(stdout.strip()), PLAY_LIMIT)
        # Without --platform the iOS limit still applies.
        code, stdout = self.run_main("--output-dir", str(self.tmp / "out-ios"),
                                     "--log-file", self.log(commits))
        self.assertGreater(len(stdout.strip()), PLAY_LIMIT)

    def test_platform_android_filters_ios_only_entries(self):
        code, stdout = self.run_main(
            "--output-dir", str(self.tmp / "out"), "--platform", "android",
            "--log-file", self.log(["fix(ios): lock screen widget", "fix(android): back gesture handling"]),
        )
        self.assertEqual(code, 0)
        self.assertEqual(stdout, "Fixes\n• Back gesture handling\n")

    def test_oversized_override_file_fails_at_the_play_limit(self):
        override = self.tmp / "override.txt"
        override.write_text("a" * (PLAY_LIMIT + 1), encoding="utf-8")
        code, _ = self.run_main("--output-dir", str(self.tmp / "out"), "--platform", "android",
                                "--log-file", self.log([]), "--override-file", str(override))
        self.assertEqual(code, 1)

    def test_unknown_platform_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.run_main("--output-dir", str(self.tmp / "out"), "--platform", "web",
                          "--log-file", self.log([]))


if __name__ == "__main__":
    unittest.main()

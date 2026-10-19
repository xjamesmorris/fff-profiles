#!/usr/bin/env python3
# Tests for scripts/validate.py. Copyright (C) 2026 James Morris. GPLv3-or-later.
#
# Run offline (deterministic):   python3 -m unittest discover -s tests -v
# Include the online check:      FFF_NET_TESTS=1 python3 -m unittest discover -s tests -v
"""
Each test builds a small throwaway repo snapshot (no .git, so every file on disk is
validated), breaks one thing, and asserts the matching check fires. TestRealRepo runs
the validator over this repository itself.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import validate  # noqa: E402

PROFILE = "profiles/Acme/filament/Tuned_PLA__PrusaCOREOne_Prusaslicer.ini"

GOOD_INI = """\
# leading comment is fine
[filament:Acme Tuned PLA @COREONE]
compatible_printers =
compatible_printers_condition = printer_model=~/(COREONE|COREONEL)/ and nozzle_diameter[0]==0.4
filament_type = PLA
filament_vendor = Acme
inherits = Generic PLA @COREONE
temperature = 215
"""

GOOD_MANIFEST = """\
{
  "source": "../PrusaSlicer_config_bundle.ini",
  "out_root": "profiles",
  "filaments": [{"name": "Acme Tuned PLA @COREONE", "vendor": "Acme"}],
  "processes": []
}
"""

GOOD_DOC = """\
# Guide

See [the profile](../profiles/Acme/filament/Tuned_PLA__PrusaCOREOne_Prusaslicer.ini)
and [setup](#printer-setup-pla). The file is `profiles/Acme/filament/`.

## Printer setup: `PLA`

```sh
[not a link](missing.md)
```
"""


class RepoCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write(PROFILE, GOOD_INI)
        self.write("manifest.example.json", GOOD_MANIFEST)
        self.write("docs/guide.md", GOOD_DOC)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, text, binary=False):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if binary:
            p.write_bytes(text)
        else:
            p.write_text(text, encoding="utf-8")

    def edit(self, rel, old, new):
        p = self.root / rel
        text = p.read_text(encoding="utf-8")
        self.assertIn(old, text)
        p.write_text(text.replace(old, new), encoding="utf-8")

    def findings(self, level=None, check=None):
        report = validate.validate(self.root)
        return [f for f in report.findings
                if (level is None or f.level == level) and (check is None or f.check == check)]

    def assertFinds(self, level, check, fragment=""):
        hits = [f for f in self.findings(level, check) if fragment in f.message]
        self.assertTrue(hits, f"expected a {level} [{check}] containing {fragment!r}; got "
                              f"{[str(f) for f in self.findings()]}")


class TestBaseline(RepoCase):
    def test_good_snapshot_is_clean(self):
        self.assertEqual([str(f) for f in self.findings()], [])


class TestProfiles(RepoCase):
    def test_bad_filename(self):
        (self.root / PROFILE).rename(self.root / "profiles/Acme/filament/Tuned PLA.ini")
        self.assertFinds("error", "layout")

    def test_wrong_category_dir(self):
        self.write("profiles/Acme/misc/X__PrusaCOREOne_Prusaslicer.ini", GOOD_INI)
        self.assertFinds("error", "layout")

    def test_presets_block(self):
        self.write(PROFILE, GOOD_INI + "\n[presets]\nfilament = Acme Tuned PLA @COREONE\n")
        self.assertFinds("error", "syntax", "[presets]")

    def test_malformed_line(self):
        self.edit(PROFILE, "temperature = 215", "temperature: 215")
        self.assertFinds("error", "syntax", "malformed")

    def test_duplicate_key(self):
        self.write(PROFILE, GOOD_INI + "temperature = 220\n")
        self.assertFinds("error", "syntax", "duplicate key 'temperature'")

    def test_duplicate_preset(self):
        self.write(PROFILE, GOOD_INI + "\n" + GOOD_INI.split("\n", 1)[1])
        self.assertFinds("error", "syntax", "duplicate preset")

    def test_unknown_kind(self):
        self.write(PROFILE, GOOD_INI + "\n[filamnet:Typo]\nx = 1\n")
        self.assertFinds("error", "syntax", "unknown section kind")

    def test_not_utf8(self):
        self.write(PROFILE, GOOD_INI.encode("utf-8") + b"filament_notes = \xff\n", binary=True)
        self.assertFinds("error", "syntax", "UTF-8")

    def test_missing_filament_type(self):
        self.edit(PROFILE, "filament_type = PLA\n", "")
        self.assertFinds("error", "content", "filament_type")

    def test_process_dir_needs_print(self):
        self.write("profiles/Acme/process/Fast__PrusaCOREOne_Prusaslicer.ini", GOOD_INI)
        self.assertFinds("error", "content", "[print:...]")

    def test_inheritance_cycle(self):
        self.write(PROFILE, GOOD_INI.replace("inherits = Generic PLA @COREONE",
                                             "inherits = Acme Base")
                   + "\n[filament:Acme Base]\nfilament_type = PLA\n"
                     "inherits = Acme Tuned PLA @COREONE\n")
        self.assertFinds("error", "inherits", "cycle")

    def test_no_inherits_warns(self):
        self.edit(PROFILE, "inherits = Generic PLA @COREONE\n", "")
        self.assertFinds("warning", "inherits", "complete preset")

    def test_vendor_mismatch_warns(self):
        self.edit(PROFILE, "filament_vendor = Acme", "filament_vendor = Generic")
        self.assertFinds("warning", "vendor")

    def test_vendor_match_ignores_spacing_and_case(self):
        self.write("profiles/PushPlastic/filament/PC__PrusaCOREOne_Prusaslicer.ini",
                   GOOD_INI.replace("filament_vendor = Acme", "filament_vendor = Push Plastic"))
        self.assertEqual(self.findings("warning", "vendor"), [])

    def test_compatible_printers_pinned_warns(self):
        self.edit(PROFILE, "compatible_printers =\n", 'compatible_printers = "My Printer"\n')
        self.assertFinds("warning", "conditions", "pins")

    def test_condition_must_target_coreone(self):
        self.edit(PROFILE, "printer_model=~/(COREONE|COREONEL)/", "printer_model==\"MK4S\"")
        self.assertFinds("warning", "conditions", "COREONE")

    def test_bad_condition_reported(self):
        self.edit(PROFILE, "nozzle_diameter[0]==0.4", "nozzle_diameter[0==0.4")
        self.assertFinds("error", "conditions", "unclosed")

    def test_custom_filament_type_needs_docs(self):
        self.edit(PROFILE, "filament_type = PLA", "filament_type = PEKK-A")
        self.assertFinds("warning", "printer-side", "PEKK-A")
        self.write("docs/setup.md", "# Setup\n\nCreate a `PEKK-A` filament on the printer.\n")
        self.assertEqual(self.findings("warning", "printer-side"), [])


class TestConditions(unittest.TestCase):
    def test_valid_conditions(self):
        for cond in [
            'printer_model=="COREONE" and nozzle_diameter[0]==0.6 and ! nozzle_high_flow[0] '
            'and printer_notes=~/.*HT400.*/',
            "printer_model=~/(COREONE|COREONEOAK|COREONEL)/ and nozzle_diameter[0]!=0.6",
            r'notes=~/.*\/path.*/ and printer_notes!~/.*PG.*/',
            "",
        ]:
            self.assertIsNone(validate.condition_problem(cond), cond)

    def test_invalid_conditions(self):
        cases = {
            "printer_model==\"COREONE": "string",
            "(printer_model==\"A\"": "unclosed",
            "nozzle_diameter[0]]==0.4": "unbalanced",
            "printer_notes=~.*HT400.*": "expected /regex/",
            "printer_notes=~/.*HT400.*": "unterminated /regex/",
            "printer_model=~/(COREONE/": "invalid regex",
        }
        for cond, fragment in cases.items():
            self.assertIn(fragment, validate.condition_problem(cond) or "", cond)


class TestMarkdown(RepoCase):
    def test_broken_relative_link(self):
        self.edit("docs/guide.md", "(../profiles/Acme", "(../profiles/Nope")
        self.assertFinds("error", "links", "doesn't exist")

    def test_broken_local_anchor(self):
        self.edit("docs/guide.md", "(#printer-setup-pla)", "(#printer-setup)")
        self.assertFinds("error", "links", "#printer-setup")

    def test_cross_file_anchor(self):
        self.write("README.md", "[ok](docs/guide.md#printer-setup-pla) "
                                "[bad](docs/guide.md#nope)\n")
        hits = self.findings("error", "links")
        self.assertEqual(len(hits), 1)
        self.assertIn("#nope", hits[0].message)

    def test_duplicate_heading_anchor_suffix(self):
        self.write("README.md", "# A\n\n# A\n\n[second](#a-1)\n")
        self.assertEqual(self.findings("error", "links"), [])

    def test_external_and_repo_escaping_links_ignored(self):
        self.write("README.md", "[gh](https://github.com/) [issues](../../issues) "
                                "[mail](mailto:a@b.c)\n")
        self.assertEqual(self.findings("error"), [])

    def test_stale_backticked_path(self):
        self.write("README.md", "See `profiles/Acme/filament/Old_Name__PrusaCOREOne_Prusaslicer.ini`"
                                " and `profiles/<Vendor>/filament/` (template, ignored).\n")
        hits = self.findings("error", "paths")
        self.assertEqual(len(hits), 1)
        self.assertIn("Old_Name", hits[0].message)

    def test_unclosed_fence(self):
        self.write("README.md", "# X\n\n```sh\nmake test\n")
        self.assertFinds("error", "fences")

    def test_links_inside_fences_ignored(self):
        # GOOD_DOC has a broken link inside a code fence; the baseline stays clean.
        self.assertEqual(self.findings("error", "links"), [])

    def test_profile_readme_ok(self):
        self.write("profiles/Acme/filament/README__Tuned_PLA__PrusaCOREOne_Prusaslicer.md", "# PLA\n")
        self.assertEqual(self.findings("error", "orphans"), [])

    def test_orphan_profile_readme(self):
        self.write("profiles/Acme/filament/README__Gone__PrusaCOREOne_Prusaslicer.md", "# Gone\n")
        self.assertFinds("error", "orphans", "no matching profile")

    def test_profile_readme_needs_prefix(self):
        self.write("profiles/Acme/filament/Tuned_PLA__PrusaCOREOne_Prusaslicer.md", "# PLA\n")
        self.assertFinds("error", "orphans", "README__")

    def test_profiles_readme_not_orphan(self):
        self.write("profiles/README.md", "# profiles\n")
        self.assertEqual(self.findings("error", "orphans"), [])


class TestRepoHygiene(RepoCase):
    def test_master_bundle_rejected(self):
        self.write("PrusaSlicer_config_bundle.ini", "[filament:x]\n")
        self.assertFinds("error", "hygiene")

    def test_real_manifest_rejected(self):
        self.write("manifest.json", GOOD_MANIFEST)
        self.assertFinds("error", "hygiene")

    def test_manifest_example_invalid_json(self):
        self.write("manifest.example.json", "{ nope")
        self.assertFinds("error", "manifest", "invalid JSON")

    def test_manifest_example_entry_needs_vendor(self):
        self.edit("manifest.example.json", ', "vendor": "Acme"', "")
        self.assertFinds("error", "manifest", "vendor")


class TestSystemPresets(RepoCase):
    def test_dangling_parent_reported(self):
        bundle = "[filament:Generic PETG @COREONE]\nfilament_type = PETG\n"
        report = validate.validate(self.root, ("9.9.9", bundle))
        hits = [f for f in report.errors if f.check == "inherits"]
        self.assertEqual(len(hits), 1)
        self.assertIn("Generic PLA @COREONE", hits[0].message)

    def test_known_parent_ok(self):
        bundle = "[filament:Generic PLA @COREONE]\nfilament_type = PLA\n"
        report = validate.validate(self.root, ("9.9.9", bundle))
        self.assertEqual(report.errors, [])


class TestRealRepo(unittest.TestCase):
    def test_repository_has_no_errors(self):
        report = validate.validate(REPO)
        self.assertEqual([str(f) for f in report.errors], [])


@unittest.skipUnless(os.environ.get("FFF_NET_TESTS"), "network test; set FFF_NET_TESTS=1 to run")
class TestRealSystemPresets(unittest.TestCase):
    def test_published_parents_exist_in_prusa_bundle(self):
        try:
            bundle = validate.fetch_prusa_system_bundle()
        except Exception as e:  # pragma: no cover - network dependent
            self.skipTest(f"could not fetch Prusa's system bundle: {e}")
        report = validate.validate(REPO, bundle)
        self.assertEqual([str(f) for f in report.errors], [])


if __name__ == "__main__":
    unittest.main()

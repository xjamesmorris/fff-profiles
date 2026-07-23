#!/usr/bin/env python3
# Tests for scripts/extract.py. Copyright (C) 2026 James Morris. GPLv3-or-later.
#
# Run offline (deterministic):   python3 -m unittest discover -s tests -v
# Include the Prusa smoke test:  FFF_NET_TESTS=1 python3 -m unittest discover -s tests -v
"""
The core suite runs entirely against the committed fixture
(tests/fixtures/sample_bundle.ini) — no network, fully deterministic.

TestPristinePrusaBundle is an optional smoke test that pulls a real, pristine
vendor profile from the PrusaSlicer GitHub repo and asserts the parser handles
it without choking. It is skipped unless FFF_NET_TESTS=1 so the default run
stays offline.
"""

import os
import sys
import unittest
import urllib.request
from pathlib import Path

# Make scripts/extract.py importable.
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import extract  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "sample_bundle.ini"


class TestParse(unittest.TestCase):
    def setUp(self):
        self.sections = extract.parse_bundle(FIXTURE.read_text(encoding="utf-8"))

    def test_section_counts(self):
        kinds = [s.kind for s in self.sections]
        self.assertEqual(kinds.count("filament"), 3)
        self.assertEqual(kinds.count("print"), 2)
        self.assertEqual(kinds.count("printer"), 1)
        self.assertEqual(kinds.count("presets"), 1)

    def test_leading_comment_ignored(self):
        # The file starts with '#' comment lines before any header.
        self.assertEqual(self.sections[0].kind, "print")

    def test_get_value(self):
        idx = extract.index(self.sections)
        self.assertEqual(idx[("filament", "Tuned PLA")].get("temperature"), "215")
        self.assertEqual(idx[("filament", "Tuned PLA")].get("inherits"), "Base PLA")

    def test_empty_inherits_has_no_parents(self):
        idx = extract.index(self.sections)
        self.assertEqual(extract.parents_of(idx[("filament", "Standalone ABS")]), [])

    def test_encoded_newline_preserved_verbatim(self):
        idx = extract.index(self.sections)
        line = [l for l in idx[("filament", "Tuned PLA")].body if l.startswith("filament_notes")][0]
        self.assertIn(r"first line\nsecond line", line)


class TestBuildOutput(unittest.TestCase):
    def setUp(self):
        self.sections = extract.parse_bundle(FIXTURE.read_text(encoding="utf-8"))

    def test_user_parent_included_in_chain(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, None)
        names = {(s.kind, s.name) for s in emitted}
        self.assertIn(("filament", "Tuned PLA"), names)
        self.assertIn(("filament", "Base PLA"), names)  # user parent pulled in

    def test_external_parent_referenced_not_included(self):
        emitted, warnings = extract.build_output(self.sections, "Tuned PLA", None, None)
        names = {s.name for s in emitted}
        self.assertNotIn("Generic PLA @SYSTEM", names)          # not emitted as a section
        self.assertTrue(any("Generic PLA @SYSTEM" in w for w in warnings))  # but warned

    def test_unrelated_presets_excluded(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, None)
        names = {s.name for s in emitted}
        self.assertNotIn("Standalone ABS", names)
        self.assertNotIn("Base Process", names)  # no print requested

    def test_ancestor_emitted_before_descendant(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, None)
        order = [s.name for s in emitted]
        self.assertLess(order.index("Base PLA"), order.index("Tuned PLA"))

    def test_paired_print_chain_resolved(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", "Fast Process", None)
        names = {(s.kind, s.name) for s in emitted}
        self.assertIn(("print", "Fast Process"), names)
        self.assertIn(("print", "Base Process"), names)  # print parent pulled in

    def test_paired_printer_included(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, "Test Printer 0.4")
        names = {(s.kind, s.name) for s in emitted}
        self.assertIn(("printer", "Test Printer 0.4"), names)

    def test_kind_emit_order_printer_print_filament(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", "Fast Process", "Test Printer 0.4")
        kinds = [s.kind for s in emitted]
        self.assertLess(kinds.index("printer"), kinds.index("print"))
        self.assertLess(kinds.index("print"), kinds.index("filament"))

    def test_missing_filament_raises(self):
        with self.assertRaises(KeyError):
            extract.build_output(self.sections, "Nope", None, None)

    def test_missing_paired_print_raises(self):
        with self.assertRaises(KeyError):
            extract.build_output(self.sections, "Tuned PLA", "Ghost Process", None)


class TestRender(unittest.TestCase):
    def setUp(self):
        self.sections = extract.parse_bundle(FIXTURE.read_text(encoding="utf-8"))

    def test_presets_block_dropped(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", "Fast Process", "Test Printer 0.4")
        text = extract.render(emitted)
        self.assertNotIn("[presets]", text)

    def test_render_is_reparseable(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, None)
        reparsed = extract.parse_bundle(extract.render(emitted))
        idx = extract.index(reparsed)
        self.assertEqual(idx[("filament", "Tuned PLA")].get("temperature"), "215")
        self.assertEqual(idx[("filament", "Base PLA")].get("bed_temperature"), "60")

    def test_render_preserves_values_exactly(self):
        emitted, _ = extract.build_output(self.sections, "Tuned PLA", None, None)
        text = extract.render(emitted)
        self.assertIn(r'filament_notes = "first line\nsecond line"', text)


class TestNaming(unittest.TestCase):
    def test_sanitize_label_strips_spaces_and_punct(self):
        self.assertEqual(extract.sanitize_label("Prusa CORE One"), "PrusaCOREOne")
        self.assertEqual(extract.sanitize_label("PrusaSlicer 2.9"), "PrusaSlicer2.9")

    def test_derive_base_drops_vendor_and_at_suffix(self):
        self.assertEqual(
            extract.derive_base("3DXTech 3DXLABS EMI-ABS", "3DXTech"),
            "3DXLABS_EMI-ABS",
        )
        self.assertEqual(
            extract.derive_base("Generic ABS @COREONE HF0.4 JM", "Generic"),
            "ABS",
        )

    def test_build_filename(self):
        self.assertEqual(
            extract.build_filename("3DXLABS_EMI-ABS", "PrusaCOREOne", "Prusaslicer"),
            "3DXLABS_EMI-ABS__PrusaCOREOne_Prusaslicer.ini",
        )

    def test_output_path(self):
        p = extract.output_path("profiles", "3DXTech", "filament", "X__Y_Z.ini")
        self.assertEqual(p, Path("profiles/3DXTech/filament/X__Y_Z.ini"))


class TestPublish(unittest.TestCase):
    def setUp(self):
        self.sections = extract.parse_bundle(FIXTURE.read_text(encoding="utf-8"))

    def test_filament_written_to_vendor_layout(self):
        import tempfile
        manifest = {
            "printer_label": "PrusaCOREOne", "slicer_label": "Prusaslicer",
            "filaments": [{"name": "Tuned PLA", "vendor": "TestCo", "base": "Tuned_PLA"}],
        }
        with tempfile.TemporaryDirectory() as d:
            written = extract.publish(self.sections, manifest, out_root=d)
            self.assertEqual(len(written), 1)
            out = written[0]
            self.assertEqual(out, Path(d) / "TestCo" / "filament" / "Tuned_PLA__PrusaCOREOne_Prusaslicer.ini")
            text = out.read_text(encoding="utf-8")
            self.assertIn("[filament:Tuned PLA]", text)
            self.assertIn("[filament:Base PLA]", text)   # user parent pulled in
            self.assertNotIn("[presets]", text)

    def test_process_written_to_process_dir(self):
        import tempfile
        manifest = {"processes": [{"name": "Fast Process", "vendor": "Generic", "base": "Fast"}]}
        with tempfile.TemporaryDirectory() as d:
            written = extract.publish(self.sections, manifest, out_root=d)
            out = written[0]
            self.assertEqual(out.parent, Path(d) / "Generic" / "process")
            text = out.read_text(encoding="utf-8")
            self.assertIn("[print:Fast Process]", text)
            self.assertIn("[print:Base Process]", text)  # print parent pulled in

    def test_base_derived_when_omitted(self):
        import tempfile
        manifest = {"filaments": [{"name": "Standalone ABS", "vendor": "Acme"}]}
        with tempfile.TemporaryDirectory() as d:
            out = extract.publish(self.sections, manifest, out_root=d)[0]
            self.assertEqual(out.name, "Standalone_ABS__PrusaCOREOne_Prusaslicer.ini")


@unittest.skipUnless(os.environ.get("FFF_NET_TESTS"), "network smoke test; set FFF_NET_TESTS=1 to run")
class TestPristinePrusaBundle(unittest.TestCase):
    """Smoke test against a pristine vendor profile from the PrusaSlicer repo."""

    URL = ("https://raw.githubusercontent.com/prusa3d/PrusaSlicer/master/"
           "resources/profiles/PrusaResearch.ini")

    @classmethod
    def setUpClass(cls):
        try:
            with urllib.request.urlopen(cls.URL, timeout=30) as r:
                cls.text = r.read().decode("utf-8")
        except Exception as e:  # pragma: no cover - network dependent
            raise unittest.SkipTest(f"could not fetch pristine Prusa bundle: {e}")

    def test_parses_real_bundle(self):
        sections = extract.parse_bundle(self.text)
        self.assertTrue(any(s.kind == "filament" for s in sections))
        self.assertTrue(any(s.kind == "printer" for s in sections))

    def test_extract_first_filament_without_error(self):
        sections = extract.parse_bundle(self.text)
        first = next(s for s in sections if s.kind == "filament" and s.name)
        emitted, warnings = extract.build_output(sections, first.name, None, None)
        # The chosen filament must be present; render must be reparseable.
        self.assertTrue(any(s.name == first.name for s in emitted))
        reparsed = extract.parse_bundle(extract.render(emitted))
        self.assertTrue(any(s.name == first.name for s in reparsed))


if __name__ == "__main__":
    unittest.main()

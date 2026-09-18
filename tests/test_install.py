"""Offline tests; all source and destination files live in temporary directories."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "installer", Path(__file__).resolve().parents[1] / "scripts" / "install.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "source"
        self.dest = Path(self.tmp.name) / "skills"
        for name in installer.SKILLS:
            source = self.root / name
            (source / "agents").mkdir(parents=True)
            (source / "references").mkdir()
            (source / "SKILL.md").write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
            (source / "agents/openai.yaml").write_text("interface: {}\n", encoding="utf-8")
            (source / "references/rules.md").write_text("Keep the full skill.\n", encoding="utf-8")

    def test_copies_all_skills_and_support_files_in_order(self):
        targets = installer.install(self.root, self.dest)
        self.assertEqual([p.name for p in targets], list(installer.SKILLS))
        for name in installer.SKILLS:
            for filename in ("SKILL.md", "agents/openai.yaml", "references/rules.md"):
                self.assertEqual((self.root / name / filename).read_bytes(),
                                 (self.dest / name / filename).read_bytes())

    def test_dry_run_creates_nothing(self):
        self.assertEqual(len(installer.install(self.root, self.dest, dry_run=True)), 4)
        self.assertFalse(self.dest.exists())

    def test_conflict_prevents_partial_install(self):
        existing = self.dest / installer.SKILLS[-1]
        existing.mkdir(parents=True)
        (existing / "keep.txt").write_text("mine", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            installer.install(self.root, self.dest)
        self.assertEqual(list(self.dest.iterdir()), [existing])
        self.assertEqual((existing / "keep.txt").read_text(encoding="utf-8"), "mine")

    def test_second_install_preserves_first(self):
        installer.install(self.root, self.dest)
        with self.assertRaises(FileExistsError):
            installer.install(self.root, self.dest)
        self.assertTrue((self.dest / installer.SKILLS[0] / "SKILL.md").is_file())

    def test_missing_source_creates_nothing(self):
        (self.root / installer.SKILLS[-1] / "SKILL.md").unlink()
        with self.assertRaises(FileNotFoundError):
            installer.install(self.root, self.dest)
        self.assertFalse(self.dest.exists())

    def test_nested_destination_is_rejected(self):
        with self.assertRaises(ValueError):
            installer.install(self.root, self.root / installer.SKILLS[0] / "nested")

    def test_file_destination_is_rejected(self):
        self.dest.write_text("keep", encoding="utf-8")
        with self.assertRaises(OSError):
            installer.install(self.root, self.dest)
        self.assertEqual(self.dest.read_text(encoding="utf-8"), "keep")

    def test_copy_failure_rolls_back_only_new_targets(self):
        self.dest.mkdir()
        unrelated = self.dest / "unrelated.txt"
        unrelated.write_text("keep", encoding="utf-8")
        with patch.object(installer.shutil, "copytree", side_effect=PermissionError("test")):
            with self.assertRaises(PermissionError):
                installer.install(self.root, self.dest)
        self.assertEqual(list(self.dest.iterdir()), [unrelated])


if __name__ == "__main__":
    unittest.main()

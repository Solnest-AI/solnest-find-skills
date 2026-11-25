"""scripts/update.py: installs only a published release into the skill folder, keeps the
user's own files (.env, bin/, anything they added), removes only what a past release
shipped, and --undo puts the old version back. Offline: releases are read from a local
folder (FIND_SKILLS_RELEASE_DIR)."""
import io
import os
import pathlib
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "skill" / "find-skills" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import update  # noqa: E402

FAKE_ENV = "SOME_KEY=fake_test_" + "0" * 24 + "\n"   # a made-up value, never a real key


def tarball(folder, version, files, top=None):
    """A GitHub-style source tarball: one top folder, the skill under skill/find-skills/."""
    top = top or f"solnest-find-skills-{version}"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        def add(rel, data):
            info = tarfile.TarInfo(f"{top}/{rel}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        add("VERSION", f"{version}\n".encode())
        add("README.md", b"repo readme, not installed\n")
        for rel, text in files.items():
            add(f"skill/find-skills/{rel}", text.encode())
    (pathlib.Path(folder) / f"v{version}.tar.gz").write_bytes(buf.getvalue())


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = pathlib.Path(self.tmp.name)
        self.rel = base / "releases"
        self.rel.mkdir()
        self.root = base / "skills" / "find-skills"
        self.root.mkdir(parents=True)
        env = mock.patch.dict(os.environ, {update.LOCAL_RELEASES: str(self.rel)})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(self.tmp.cleanup)
        old = {"SKILL.md": "old skill\n", "LICENSE": "license\n", "scripts/update.py": "old updater\n",
               "scripts/dropped.py": "gone next\n"}
        tarball(self.rel, "1.0.0", old)
        for rel, text in old.items():
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.root / rel).write_text(text, encoding="utf-8")
        (self.root / "VERSION").write_text("1.0.0\n", encoding="utf-8")
        (self.root / ".env").write_text(FAKE_ENV, encoding="utf-8")
        (self.root / "bin").mkdir()
        (self.root / "bin" / "py").write_text("fake launcher\n", encoding="utf-8")
        (self.root / "my-notes.md").write_text("mine\n", encoding="utf-8")
        (self.root / "scripts" / "my-own.py").write_text("mine too\n", encoding="utf-8")

    def _new_release(self):
        tarball(self.rel, "1.1.0", {"SKILL.md": "new skill\n", "LICENSE": "license\n",
                                    "scripts/update.py": "new updater\n", "scripts/new.py": "brand new\n",
                                    "bin/py": "release must not win\n", ".env": "SOME_KEY=from_release\n"})

    def _user_files_untouched(self):
        self.assertEqual((self.root / ".env").read_text(), FAKE_ENV)
        self.assertEqual((self.root / "bin" / "py").read_text(), "fake launcher\n")
        self.assertEqual((self.root / "my-notes.md").read_text(), "mine\n")
        self.assertEqual((self.root / "scripts" / "my-own.py").read_text(), "mine too\n")

    def test_update_keeps_user_files_and_undo_goes_back(self):
        self._new_release()
        r = update.update(self.root)
        self.assertEqual(r["status"], "updated")
        self.assertEqual((self.root / "VERSION").read_text().strip(), "1.1.0")
        self.assertEqual((self.root / "SKILL.md").read_text(), "new skill\n")
        self.assertTrue((self.root / "scripts" / "new.py").is_file())
        self.assertFalse((self.root / "scripts" / "dropped.py").exists())   # shipped by 1.0.0, not 1.1.0
        self.assertFalse((self.root / "README.md").exists())                # repo files are not installed
        self._user_files_untouched()
        self.assertEqual(update.update(self.root)["status"], "current")

        update.undo(self.root)
        self.assertEqual((self.root / "VERSION").read_text().strip(), "1.0.0")
        self.assertEqual((self.root / "SKILL.md").read_text(), "old skill\n")
        self.assertEqual((self.root / "scripts" / "update.py").read_text(), "old updater\n")
        self.assertTrue((self.root / "scripts" / "dropped.py").is_file())
        self.assertFalse((self.root / "scripts" / "new.py").exists())
        self._user_files_untouched()

    def test_manifest_lists_what_shipped_and_never_the_user_files(self):
        self._new_release()
        update.update(self.root)
        listed = set(update.load_manifest(self.root))
        self.assertEqual(listed, {"VERSION", "SKILL.md", "LICENSE", "scripts/update.py", "scripts/new.py"})
        # the next release drops scripts/new.py: the manifest is what gets it removed
        tarball(self.rel, "1.2.0", {"SKILL.md": "newer skill\n", "LICENSE": "license\n",
                                    "scripts/update.py": "newer updater\n"})
        r = update.update(self.root)
        self.assertEqual(r["removed"], ["scripts/new.py"])
        self.assertFalse((self.root / "scripts" / "new.py").exists())
        self._user_files_untouched()

    def test_a_file_the_user_edited_is_saved_in_the_backup(self):
        (self.root / "SKILL.md").write_text("old skill, edited by the user\n", encoding="utf-8")
        self._new_release()
        r = update.update(self.root)
        self.assertEqual(r["edited"], ["SKILL.md"])
        self.assertEqual((pathlib.Path(r["backup"]) / "SKILL.md").read_text(), "old skill, edited by the user\n")
        update.undo(self.root)
        self.assertEqual((self.root / "SKILL.md").read_text(), "old skill, edited by the user\n")

    def test_release_labelled_with_another_version_is_refused(self):
        tarball(self.rel, "1.1.0", {"SKILL.md": "new\n"})
        blob = (self.rel / "v1.1.0.tar.gz").read_bytes()
        (self.rel / "v1.1.0.tar.gz").unlink()
        (self.rel / "v1.3.0.tar.gz").write_bytes(blob)      # tag says 1.3.0, VERSION inside says 1.1.0
        with self.assertRaises(update.UpdateError):
            update.update(self.root)
        self.assertEqual((self.root / "SKILL.md").read_text(), "old skill\n")

    def test_refuses_a_git_checkout(self):
        (self.root.parent.parent / "skill").mkdir()
        clone_skill = self.root.parent.parent / "skill" / "find-skills"
        clone_skill.mkdir()
        (self.root.parent.parent / ".git").mkdir()
        tarball(self.rel, "1.1.0", {"SKILL.md": "new\n"})
        with self.assertRaises(update.UpdateError):
            update.update(clone_skill)

    def test_unsafe_release_changes_nothing(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for name in ("top/VERSION", "../evil"):
                info = tarfile.TarInfo(name)
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        (self.rel / "v1.1.0.tar.gz").write_bytes(buf.getvalue())
        with self.assertRaises(update.UpdateError):
            update.update(self.root)
        self.assertEqual((self.root / "VERSION").read_text().strip(), "1.0.0")
        self.assertEqual((self.root / "SKILL.md").read_text(), "old skill\n")

    def test_no_release_yet_is_a_plain_error(self):
        for p in self.rel.glob("*"):
            p.unlink()
        with self.assertRaises(update.UpdateError):
            update.update(self.root)


if __name__ == "__main__":
    unittest.main()

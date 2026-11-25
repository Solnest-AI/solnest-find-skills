"""install.sh: installs the skill into a (fake) home, writes the launcher, leaves the user's
own files alone on a second run, never installs a stray .cursor folder, says so when Node.js
is missing, and refuses to overwrite a link or a different skill.
Offline: it installs from this copy of the repo, or from a local archive."""
import os
import pathlib
import shutil
import subprocess
import tarfile
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parent.parent
BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "needs bash")
class InstallTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name) / "home"
        self.home.mkdir()
        self.dest = self.home / ".claude" / "skills" / "find-skills"
        # a stand-in for npx, so the test does not depend on Node.js being installed here
        self.npx = pathlib.Path(self.tmp.name) / "fake-npx"
        self.npx.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        self.npx.chmod(0o755)

    def run_install(self, script=None, stdin=None, **extra):
        env = dict(os.environ, HOME=str(self.home), FIND_SKILLS_NPX=str(self.npx))
        env.update(extra)
        args = [BASH, str(script)] if script else [BASH]
        return subprocess.run(args, env=env, capture_output=True, text=True, timeout=300,
                              stdin=stdin or subprocess.DEVNULL, cwd=self.tmp.name)

    def test_installs_and_a_second_run_keeps_user_files(self):
        r = self.run_install(REPO / "install.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("[ok] updater", r.stdout)
        self.assertIn("[ok] Node.js", r.stdout)
        for rel in ("SKILL.md", "LICENSE", "VERSION", "bin/py", "scripts/update.py",
                    "scripts/solnest_autoupdate.py"):
            self.assertTrue((self.dest / rel).is_file(), rel)
        self.assertEqual((self.dest / "VERSION").read_text(), (REPO / "VERSION").read_text())
        self.assertFalse((self.dest / ".cursor").exists())
        h = subprocess.run([str(self.dest / "bin" / "py"), str(self.dest / "scripts" / "update.py"), "--help"],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(h.returncode, 0, h.stderr)

        (self.dest / "my-notes.md").write_text("mine\n", encoding="utf-8")
        r = self.run_install(REPO / "install.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual((self.dest / "my-notes.md").read_text(), "mine\n")

    def test_a_stray_cursor_folder_is_never_installed(self):
        """A sync job can drop private editor rules into any folder: they must not ship."""
        copy = pathlib.Path(self.tmp.name) / "repo"
        shutil.copytree(REPO, copy, ignore=shutil.ignore_patterns(".git", ".cursor", "__pycache__", ".pytest_cache"))
        rules = copy / "skill" / "find-skills" / ".cursor" / "rules"
        rules.mkdir(parents=True)
        (rules / "private.mdc").write_text("private\n", encoding="utf-8")
        r = self.run_install(copy / "install.sh")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertTrue((self.dest / "SKILL.md").is_file())
        self.assertFalse((self.dest / ".cursor").exists())

    def test_missing_node_is_reported(self):
        r = self.run_install(REPO / "install.sh", FIND_SKILLS_NPX="no-such-npx-anywhere")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("[!!] Node.js", r.stdout)
        self.assertTrue((self.dest / "SKILL.md").is_file())     # the skill is in place; only Node is missing

    def test_piped_install_from_an_archive(self):
        """The `curl ... | bash` path: no local repo, the skill comes from an archive."""
        archive = pathlib.Path(self.tmp.name) / "main.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(REPO / "VERSION", "solnest-find-skills-main/VERSION")
            tar.add(REPO / "skill", "solnest-find-skills-main/skill",
                    filter=lambda t: None if "__pycache__" in t.name or ".cursor" in t.name else t)
        with open(REPO / "install.sh", "rb") as script:
            r = self.run_install(stdin=script, FIND_SKILLS_ARCHIVE_URL=archive.as_uri())
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("downloading the skill", r.stdout)
        self.assertTrue((self.dest / "SKILL.md").is_file())
        self.assertEqual((self.dest / "VERSION").read_text(), (REPO / "VERSION").read_text())

    def test_refuses_a_different_skill(self):
        self.dest.mkdir(parents=True)
        (self.dest / "SKILL.md").write_text("---\nname: something-else\n---\n", encoding="utf-8")
        r = self.run_install(REPO / "install.sh")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertEqual((self.dest / "SKILL.md").read_text(), "---\nname: something-else\n---\n")
        self.assertFalse((self.dest / "scripts").exists())

    def test_refuses_a_link(self):
        """The original installed by `npx skills add` is often a link: never write through it."""
        real = self.home / ".agents" / "skills" / "find-skills"
        real.mkdir(parents=True)
        (real / "SKILL.md").write_text("---\nname: find-skills\n---\noriginal\n", encoding="utf-8")
        self.dest.parent.mkdir(parents=True)
        self.dest.symlink_to(real)
        r = self.run_install(REPO / "install.sh")
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("is a link", r.stdout)
        self.assertEqual(sorted(p.name for p in real.iterdir()), ["SKILL.md"])


if __name__ == "__main__":
    unittest.main()

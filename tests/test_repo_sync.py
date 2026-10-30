import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.lib import repo_sync as rs


def run(*cmd, cwd=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True, env=env).stdout


def make_remote(base: Path, name: str, files: dict) -> Path:
    bare = base / f"{name}.git"
    run("git", "init", "-q", "--bare", "-b", "main", str(bare))
    seed = base / f"{name}-seed"
    run("git", "clone", "-q", str(bare), str(seed))
    for rel, body in files.items():
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text(body)
    run("git", "add", "-A", cwd=seed)
    run("git", "commit", "-q", "-m", "seed", cwd=seed)
    run("git", "push", "-q", "origin", "HEAD:main", cwd=seed)
    return bare


class Fixture:
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.org = make_remote(self.tmp, "org", {"CLAUDE.md": "x\n", ".gitignore": "me/\nstaged/\n"})
        self.priv = make_remote(self.tmp, "priv", {"README.md": "p\n"})
        self.root = self.tmp / "root"

    def boot(self, root=None):
        return rs.bootstrap(root or self.root, str(self.org), str(self.priv))


class RepoSyncTest(Fixture, unittest.TestCase):
    def test_bootstrap_creates_layout_and_is_idempotent(self):
        info = self.boot()
        self.assertTrue(info["ok"])
        for rel in rs.PRIVATE_LINKS:
            self.assertTrue((self.root / rel).is_symlink(), rel)
        (self.root / "memory/me/identity.md").write_text("me\n")
        self.assertTrue((self.root / ".private/me/identity.md").exists())
        again = self.boot()
        self.assertEqual(again["links_created"], [])
        self.assertIn("/me", (self.root / "memory/.gitignore").read_text())

    def test_private_content_never_reaches_org(self):
        self.boot()
        (self.root / "memory/me/identity.md").write_text("secret\n")
        (self.root / "memory/staged/draft.md").write_text("draft\n")
        (self.root / "memory/person.md").write_text("shared\n")
        report = rs.sync(self.root, host="h1")
        self.assertTrue(report.ok, report.to_dict())
        org_files = run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.org).split()
        self.assertIn("person.md", org_files)
        self.assertFalse([f for f in org_files if f.startswith(("me", "staged"))], org_files)
        priv_files = run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.priv).split()
        self.assertIn("me/identity.md", priv_files)
        self.assertIn("staged/draft.md", priv_files)

    def test_privacy_guard_blocks_tracked_private_path(self):
        self.boot()
        mem = self.root / "memory"
        run("git", "add", "-f", "-A", cwd=mem)  # no-op baseline
        bad = mem / "staged"
        bad.unlink()  # simulate a checkout where staged/ is a real, trackable dir
        bad.mkdir()
        (bad / "raw.md").write_text("raw\n")
        run("git", "add", "-f", "staged/raw.md", cwd=mem)
        run("git", "commit", "-q", "-m", "oops", cwd=mem)
        with self.assertRaises(rs.PrivacyViolation):
            rs.check_org_privacy(mem)
        report = rs.sync(self.root, host="h1")
        self.assertFalse(report.ok)
        self.assertNotIn("staged/raw.md", run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.org))

    def test_privacy_guard_blocks_tracked_symlink(self):
        self.boot()
        mem = self.root / "memory"
        (mem / "link").symlink_to("../.private/me")
        run("git", "add", "link", cwd=mem)
        with self.assertRaises(rs.PrivacyViolation):
            rs.check_org_privacy(mem)

    def test_two_hosts_converge_without_force(self):
        self.boot()
        other = self.tmp / "other"
        self.boot(other)
        (self.root / "memory/a.md").write_text("a\n")
        (other / "memory/b.md").write_text("b\n")
        self.assertTrue(rs.sync(self.root, "mac").ok)
        self.assertTrue(rs.sync(other, "cloud").ok)  # must rebase over mac's push
        self.assertTrue(rs.sync(self.root, "mac").ok)
        self.assertTrue((self.root / "memory/b.md").exists())
        self.assertTrue((other / "memory/a.md").exists())

    def test_conflict_goes_to_branch_and_main_is_untouched(self):
        self.boot()
        other = self.tmp / "other"
        self.boot(other)
        (self.root / "memory/CLAUDE.md").write_text("mac edit\n")
        (other / "memory/CLAUDE.md").write_text("cloud edit\n")
        self.assertTrue(rs.sync(self.root, "mac").ok)
        report = rs.sync(other, "cloud")
        self.assertFalse(report.ok)
        org = next(r for r in report.results if r.name == "org")
        self.assertEqual(org.action, "conflict")
        self.assertTrue(org.conflict_branch.startswith("conflict/cloud/"))
        self.assertEqual(run("git", "show", "main:CLAUDE.md", cwd=self.org), "mac edit\n")
        self.assertEqual(run("git", "show", org.conflict_branch + ":CLAUDE.md", cwd=self.org), "cloud edit\n")
        self.assertEqual((other / "memory/CLAUDE.md").read_text(), "mac edit\n")

    def test_failure_is_logged_not_silent(self):
        self.boot()
        run("git", "remote", "set-url", "origin", str(self.tmp / "gone.git"), cwd=self.root / ".private")
        (self.root / "memory/me/x.md").write_text("x\n")
        report = rs.sync(self.root, "h1")
        self.assertFalse(report.ok)
        status = json.loads((self.root / rs.STATUS_FILE).read_text())
        self.assertFalse(status["ok"])

    def test_real_content_blocks_link_creation(self):
        rs.clone_or_open(str(self.org), self.root / "memory")
        (self.root / "memory/me").mkdir()
        (self.root / "memory/me/identity.md").write_text("real\n")
        with self.assertRaises(rs.SyncError):
            rs.ensure_links(self.root)


if __name__ == "__main__":
    unittest.main()


class AdoptAndResolveTest(Fixture, unittest.TestCase):
    def test_adopt_existing_checkouts(self):
        org_co = self.tmp / "nucleus-memory"
        priv_co = self.tmp / "cortex-private"
        run("git", "clone", "-q", str(self.org), str(org_co))
        run("git", "clone", "-q", str(self.priv), str(priv_co))
        info = rs.bootstrap(self.root, str(self.org), str(self.priv), org_co, priv_co)
        self.assertTrue(info["ok"])
        self.assertTrue((self.root / "memory").is_symlink())
        (self.root / "memory/me/identity.md").write_text("me\n")
        self.assertTrue(rs.sync(self.root, "cloud").ok)
        self.assertNotIn("me/identity.md", run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.org))

    def test_config_root_resolves_bootstrapped_cloud_root(self):
        from scripts.lib.config_root import resolve_config_root

        home = self.tmp / "home"
        (home / "cortex-root").mkdir(parents=True)
        self.assertEqual(resolve_config_root(home=home).source, "default (~/Documents/Claude)")
        self.boot(home / "cortex-root")
        res = resolve_config_root(home=home)
        self.assertEqual(res.path, home / "cortex-root")


class RemoteNameTest(Fixture, unittest.TestCase):
    def test_nonstandard_remote_name_and_memory_archive_is_not_private(self):
        self.boot()
        mem = self.root / "memory"
        run("git", "remote", "rename", "origin", "nucleus-memory", cwd=mem)
        (mem / "archive").mkdir()
        (mem / "archive/old-node.md").write_text("archived node\n")
        (mem / "n.md").write_text("n\n")
        report = rs.sync(self.root, "mac")
        self.assertTrue(report.ok, report.to_dict())
        files = run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.org).split()
        self.assertIn("archive/old-node.md", files)


class QuietNoopTest(Fixture, unittest.TestCase):
    def test_noop_sync_writes_no_log_line_and_no_commit(self):
        self.boot()
        rs.sync(self.root, "h")  # may commit the initial symlink/gitignore state
        before = run("git", "rev-list", "--count", "HEAD", cwd=self.root / ".private").strip()
        rs.sync(self.root, "h")
        rs.sync(self.root, "h")
        after = run("git", "rev-list", "--count", "HEAD", cwd=self.root / ".private").strip()
        self.assertEqual(before, after)


class DetachedHeadTest(Fixture, unittest.TestCase):
    def test_sync_works_from_detached_head(self):
        self.boot()
        for repo in (self.root / "memory", self.root / ".private"):
            run("git", "checkout", "-q", "--detach", cwd=repo)
        (self.root / "memory/n.md").write_text("n\n")
        (self.root / "memory/me/x.md").write_text("x\n")
        report = rs.sync(self.root, "cloud")
        self.assertTrue(report.ok, report.to_dict())
        self.assertIn("n.md", run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.org))
        self.assertIn("me/x.md", run("git", "ls-tree", "-r", "--name-only", "main", cwd=self.priv))


class PrivateScopeWriteTest(Fixture, unittest.TestCase):
    def test_cli_paths_may_go_through_private_symlinks_only(self):
        from scripts.lib.node_paths import PathTraversalError, resolve_node_path

        self.boot()
        mem = self.root / "memory"
        ok = resolve_node_path(mem, "staged/queues/reindex")
        self.assertEqual(ok, (self.root / ".private/staged/queues/reindex").resolve())
        self.assertTrue(resolve_node_path(mem, "me/identity.md"))
        with self.assertRaises(PathTraversalError):
            resolve_node_path(mem, "staged/../../outside.md")
        with self.assertRaises(PathTraversalError):
            resolve_node_path(mem, "../.private/briefs/x.md")


class DiscoveryTest(Fixture, unittest.TestCase):
    def test_bootstrap_with_no_urls_discovers_marked_checkouts(self):
        # remotes carry the role markers, as the real repos do
        org2 = make_remote(self.tmp, "org2", {".cortex-role": "org\n", "CLAUDE.md": "x\n"})
        priv2 = make_remote(self.tmp, "priv2", {".cortex-role": "private\n", "README.md": "p\n"})
        sources = self.tmp / "sources"
        run("git", "clone", "-q", str(org2), str(sources / "nucleus-memory"))
        run("git", "clone", "-q", str(priv2), str(sources / "cortex-private"))
        run("git", "clone", "-q", str(self.org), str(sources / "unrelated"))  # no marker
        info = rs.bootstrap(self.root, search_dirs=[sources])
        self.assertTrue(info["ok"], info)
        self.assertEqual((self.root / "memory").resolve(), (sources / "nucleus-memory").resolve())
        cfg = json.loads((self.root / rs.REPOS_FILE).read_text())
        self.assertEqual(cfg["org"], str(org2))
        self.assertEqual(cfg["private"], str(priv2))

    def test_bootstrap_without_anything_still_errors_clearly(self):
        with self.assertRaises(rs.SyncError):
            rs.bootstrap(self.root, search_dirs=[self.tmp / "empty"])

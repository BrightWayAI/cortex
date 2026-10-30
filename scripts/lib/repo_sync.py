"""Two-repo git sync for a cloud-first Cortex config-root.

Layout (see references/core-contract.md §11B):

    <root>/memory/      clone of the shared/org memory repo
    <root>/.private/    clone of the per-user private repo
                        (me/ staged/ archive/ briefs/ plugins/)
    <root>/memory/me, memory/staged, archive, briefs, plugins
                        directory symlinks into .private/, so every existing
                        path in the workflows keeps resolving.

Rules enforced here, deterministically (never by prose):
  * never force-push;
  * pull before write is `pull_repo`; push after write is `push_repo`;
  * a rebase conflict is aborted, the local commits are pushed to a
    `conflict/<host>/<ts>` branch, and main is left untouched;
  * the org repo must never track private paths or any symlink
    (`check_org_privacy`) and `sync` refuses to push it if it does.
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# link path (relative to root) -> symlink target (relative to the link's parent)
PRIVATE_LINKS = {
    "memory/me": "../.private/me",
    "memory/staged": "../.private/staged",
    "archive": ".private/archive",
    "briefs": ".private/briefs",
    "plugins": ".private/plugins",
}
PRIVATE_DIRS = ("me", "staged", "archive", "briefs", "plugins")
# Inside the org repo only me/ and staged/ are private. Root-level archive/, briefs/
# and plugins/ live outside the org checkout; memory/archive/ (archived nodes) is org content.
_FORBIDDEN_ORG = re.compile(r"^(me|staged)(/|$)")
ORG_GITIGNORE_LINES = ("/me", "/staged")
REPOS_FILE = ".cortex-repos.json"
STATUS_FILE = ".sync-status.json"
SYNC_LOG = "staged/sync-log.md"
MAX_PUSH_ATTEMPTS = 3


class SyncError(Exception):
    pass


class PrivacyViolation(SyncError):
    pass


@dataclass
class RepoResult:
    name: str
    ok: bool = True
    action: str = "noop"  # noop | pulled | pushed | conflict | failed
    detail: str = ""
    conflict_branch: str | None = None


@dataclass
class SyncReport:
    host: str
    at: str
    results: list[RepoResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.results)

    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "at": self.at,
            "ok": self.ok,
            "repos": [r.__dict__ for r in self.results],
        }


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    cmd = ["git", "-C", str(repo)]
    if not _has_identity(repo, env):
        cmd += ["-c", "user.name=cortex-sync", "-c", "user.email=cortex-sync@users.noreply.github.com"]
    proc = subprocess.run(cmd + list(args), capture_output=True, text=True, env=env)
    if check and proc.returncode != 0:
        raise SyncError(f"git {' '.join(args)} failed in {repo}: {(proc.stderr or proc.stdout).strip()}")
    return proc


def _has_identity(repo: Path, env: dict) -> bool:
    out = subprocess.run(
        ["git", "-C", str(repo), "config", "user.email"], capture_output=True, text=True, env=env
    )
    return bool(out.stdout.strip())


def _remote(repo: Path) -> str:
    names = git(repo, "remote").stdout.split()
    if not names:
        raise SyncError(f"{repo} has no git remote")
    return "origin" if "origin" in names else names[0]


def _branch(repo: Path) -> str:
    return git(repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def _dirty(repo: Path) -> bool:
    return bool(git(repo, "status", "--porcelain").stdout.strip())


def _counts(repo: Path, branch: str) -> tuple[int, int]:
    """(ahead, behind) of HEAD relative to origin/<branch>."""
    out = git(repo, "rev-list", "--left-right", "--count", f"HEAD...{_remote(repo)}/{branch}").stdout.split()
    return int(out[0]), int(out[1])


def clone_or_open(url: str, dest: Path, adopt: Path | None = None) -> Path:
    if (dest / ".git").exists():
        return dest
    if adopt is not None and (adopt / ".git").exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(adopt.resolve())  # reuse a host-provided checkout (cloud sources)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    proc = subprocess.run(["git", "clone", url, str(dest)], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise SyncError(f"clone of {url} failed: {proc.stderr.strip()}")
    return dest


def commit_all(repo: Path, message: str) -> bool:
    if not _dirty(repo):
        return False
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    return True


def pull_repo(repo: Path, name: str = "") -> RepoResult:
    """Fast-forward, or rebase local commits; abort (never force) on conflict."""
    res = RepoResult(name=name or repo.name)
    git(repo, "fetch", "-q", _remote(repo))
    branch = _branch(repo)
    if git(repo, "rev-parse", "--verify", "-q", f"{_remote(repo)}/{branch}", check=False).returncode != 0:
        return res  # empty remote
    ahead, behind = _counts(repo, branch)
    if behind == 0:
        return res
    if ahead == 0:
        git(repo, "merge", "--ff-only", f"{_remote(repo)}/{branch}")
        res.action = "pulled"
        return res
    if git(repo, "rebase", f"{_remote(repo)}/{branch}", check=False).returncode != 0:
        git(repo, "rebase", "--abort", check=False)
        res.ok, res.action = False, "conflict"
        res.detail = "rebase conflict on pull; local commits kept"
        return res
    res.action = "pulled"
    return res


def push_repo(repo: Path, name: str, host: str) -> RepoResult:
    res = RepoResult(name=name)
    branch = _branch(repo)
    pulled = pull_repo(repo, name)
    if not pulled.ok:
        return _divert_to_conflict_branch(repo, name, host, branch, pulled.detail)
    try:
        ahead, _ = _counts(repo, branch)
    except SyncError:
        ahead = 1  # empty remote: first push
    if ahead == 0:
        return res
    for _ in range(MAX_PUSH_ATTEMPTS):
        if git(repo, "push", "-q", _remote(repo), f"HEAD:{branch}", check=False).returncode == 0:
            res.action = "pushed"
            return res
        pulled = pull_repo(repo, name)  # lost a race: re-fetch, rebase, retry
        if not pulled.ok:
            return _divert_to_conflict_branch(repo, name, host, branch, pulled.detail)
    res.ok, res.action, res.detail = False, "failed", f"push rejected {MAX_PUSH_ATTEMPTS}x"
    return res


def _divert_to_conflict_branch(repo: Path, name: str, host: str, branch: str, why: str) -> RepoResult:
    safe_host = re.sub(r"[^A-Za-z0-9._-]", "-", host)
    cb = f"conflict/{safe_host}/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    res = RepoResult(name=name, ok=False, action="conflict", conflict_branch=cb, detail=why)
    if git(repo, "push", "-q", _remote(repo), f"HEAD:refs/heads/{cb}", check=False).returncode != 0:
        res.detail += "; ALSO failed to push conflict branch (local commits kept)"
        return res
    # Local commits are now safe on the remote branch; realign main with origin.
    git(repo, "reset", "-q", "--hard", f"{_remote(repo)}/{branch}")
    return res


def check_org_privacy(repo: Path) -> None:
    """Refuse if the org repo tracks private paths or symlinks (HEAD or unpushed)."""
    bad: list[str] = []
    for line in git(repo, "ls-files", "-s").stdout.splitlines():
        meta, _, path = line.partition("\t")
        if meta.startswith("120000") or _FORBIDDEN_ORG.match(path):
            bad.append(path)
    branch = _branch(repo)
    if git(repo, "rev-parse", "--verify", "-q", f"{_remote(repo)}/{branch}", check=False).returncode == 0:
        names = git(repo, "diff", "--name-only", f"{_remote(repo)}/{branch}..HEAD").stdout.splitlines()
        bad += [n for n in names if _FORBIDDEN_ORG.match(n)]
    if bad:
        raise PrivacyViolation(
            "org repo would publish private paths: " + ", ".join(sorted(set(bad))[:10])
        )


def ensure_org_gitignore(memory: Path) -> bool:
    """Symlinks are not matched by trailing-slash patterns, so add /me and /staged."""
    path = memory / ".gitignore"
    existing = path.read_text().splitlines() if path.exists() else []
    missing = [ln for ln in ORG_GITIGNORE_LINES if ln not in existing]
    if not missing:
        return False
    body = "\n".join(existing + ([""] if existing and existing[-1] else []) + missing) + "\n"
    path.write_text(body)
    return True


def ensure_links(root: Path) -> list[str]:
    """Create the private-dir symlinks. Never moves or deletes real content."""
    private = root / ".private"
    for d in PRIVATE_DIRS:
        (private / d).mkdir(parents=True, exist_ok=True)
    made: list[str] = []
    for rel, target in PRIVATE_LINKS.items():
        link = root / rel
        if rel.startswith("memory/") and (root / "memory").is_symlink():
            # memory/ is an adopted checkout elsewhere: a relative target would
            # resolve against that checkout's real parent, so pin it absolute.
            target = str(root / target.replace("../", "", 1))
        if link.is_symlink():
            if os.readlink(link) != target:
                raise SyncError(f"{link} is a symlink to {os.readlink(link)}, expected {target}")
            continue
        if link.exists():
            if link.is_dir() and not any(link.iterdir()):
                link.rmdir()
            else:
                raise SyncError(
                    f"{link} holds real content; run the one-time migration before bootstrap/sync"
                )
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target)
        made.append(rel)
    return made


def load_repo_urls(root: Path, org_url: str | None, private_url: str | None) -> tuple[str, str]:
    cfg_path = root / REPOS_FILE
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    org = org_url or os.environ.get("CORTEX_ORG_REPO") or cfg.get("org")
    priv = private_url or os.environ.get("CORTEX_PRIVATE_REPO") or cfg.get("private")
    if not org or not priv:
        raise SyncError(
            "org and private repo URLs unresolved: pass --org-repo/--private-repo, set "
            f"CORTEX_ORG_REPO/CORTEX_PRIVATE_REPO, or record them in {cfg_path}"
        )
    root.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"org": org, "private": priv}, indent=2) + "\n")
    return org, priv


def bootstrap(
    root: Path,
    org_url: str | None = None,
    private_url: str | None = None,
    adopt_org: Path | None = None,
    adopt_private: Path | None = None,
) -> dict:
    """Idempotently materialize the config-root from the two repos."""
    org, priv = load_repo_urls(root, org_url, private_url)
    memory = clone_or_open(org, root / "memory", adopt_org)
    private = clone_or_open(priv, root / ".private", adopt_private)
    pulls = [pull_repo(memory, "org"), pull_repo(private, "private")]
    links = ensure_links(root)
    ensure_org_gitignore(memory)
    return {
        "root": str(root),
        "memory_root": str(memory),
        "links_created": links,
        "pulls": [r.__dict__ for r in pulls],
        "ok": all(r.ok for r in pulls),
    }


def sync(root: Path, host: str | None = None) -> SyncReport:
    """Commit stragglers, pull, push both repos. Logs every run; never silent."""
    host = host or socket.gethostname()
    report = SyncReport(host=host, at=_now())
    memory, private = root / "memory", root / ".private"
    for name, repo in (("org", memory), ("private", private)):
        try:
            if name == "org":
                ensure_org_gitignore(memory)
            commit_all(repo, f"autosync {host} {report.at}")
            if name == "org":
                check_org_privacy(repo)
            report.results.append(push_repo(repo, name, host))
        except PrivacyViolation as exc:
            report.results.append(RepoResult(name=name, ok=False, action="failed", detail=str(exc)))
        except SyncError as exc:
            report.results.append(RepoResult(name=name, ok=False, action="failed", detail=str(exc)))
    _record(root, report)
    return report


def _record(root: Path, report: SyncReport) -> None:
    (root / STATUS_FILE).write_text(json.dumps(report.to_dict(), indent=2) + "\n")
    if report.ok and all(r.action == "noop" for r in report.results):
        return  # nothing happened: status file only, no log line (and no commit) per tick
    line = "- {at} {host} {state}: {detail}\n".format(
        at=report.at,
        host=report.host,
        state="ok" if report.ok else "FAILED",
        detail="; ".join(
            f"{r.name}={r.action}" + (f" ({r.detail})" if r.detail else "") for r in report.results
        ),
    )
    log = root / ".private" / SYNC_LOG
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a") as fh:
            fh.write(line)
    except OSError:
        pass  # status file above is the fallback sink

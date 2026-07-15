"""GitCommitter push durability (TECH_SPEC §14).

A checkpoint that is only committed locally is invisible to the next Actions
dispatch and to the backend's status proxy the moment the runner's container is
torn down — so every commit must be pushed immediately, and a non-fast-forward
(another writer landed a commit first) must be absorbed by fetch→rebase→push
rather than failing the run. These tests exercise that against a real local
bare repo standing in for ``origin`` — no network, no GitHub — so they run
everywhere ``git`` does.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from run import GitCommitter, GitPushError


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _init_repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    """A bare 'origin' plus a clone with an initial commit on 'main', pushed."""
    bare = tmp_path / "origin.git"
    bare.mkdir()
    _git("init", "--bare", "-b", "main", cwd=bare)

    clone = tmp_path / "clone"
    clone.mkdir()
    _git("init", "-b", "main", cwd=clone)
    _git("config", "user.email", "test@example.com", cwd=clone)
    _git("config", "user.name", "Test", cwd=clone)
    _git("remote", "add", "origin", str(bare), cwd=clone)
    (clone / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "-A", cwd=clone)
    _git("commit", "-m", "seed", cwd=clone)
    _git("push", "-u", "origin", "main", cwd=clone)
    return bare, clone


def test_commit_pushes_immediately(tmp_path):
    bare, clone = _init_repo_with_remote(tmp_path)
    committer = GitCommitter(repo_root=clone, sleep=lambda _s: None)

    run_dir = clone / "runs" / "WT-TEST-01"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text('{"stage": "X"}\n', encoding="utf-8")

    sha = committer.commit(run_dir, "checkpoint")

    # A fresh clone of the bare 'origin' must already see the commit — proof the
    # checkpoint is durable beyond this container, not just committed locally.
    verify = tmp_path / "verify"
    _git("clone", str(bare), str(verify), cwd=tmp_path)
    assert (verify / "runs" / "WT-TEST-01" / "run.json").is_file()
    log = _git("log", "-1", "--format=%H", cwd=verify)
    assert log.stdout.strip() == sha


def test_commit_is_noop_when_nothing_staged(tmp_path):
    _bare, clone = _init_repo_with_remote(tmp_path)
    committer = GitCommitter(repo_root=clone, sleep=lambda _s: None)
    head_before = _git("rev-parse", "HEAD", cwd=clone).stdout.strip()

    run_dir = clone / "runs" / "WT-TEST-02"
    run_dir.mkdir(parents=True)
    sha = committer.commit(run_dir, "nothing to commit")

    assert sha == head_before


def test_commit_rebases_and_retries_on_non_fast_forward(tmp_path):
    """Two disjoint-path writers (two runs) push to the same branch; the second
    committer's push loses the race and must rebase-and-retry rather than fail."""
    bare, clone_a = _init_repo_with_remote(tmp_path)

    clone_b = tmp_path / "clone_b"
    _git("clone", str(bare), str(clone_b), cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=clone_b)
    _git("config", "user.name", "Test", cwd=clone_b)

    # clone_a commits+pushes first, behind clone_b's back.
    committer_a = GitCommitter(repo_root=clone_a, sleep=lambda _s: None)
    run_dir_a = clone_a / "runs" / "WT-TEST-A"
    run_dir_a.mkdir(parents=True)
    (run_dir_a / "run.json").write_text('{"stage": "A"}\n', encoding="utf-8")
    committer_a.commit(run_dir_a, "run A checkpoint")

    # clone_b, still on the old tip, commits its own disjoint path and must
    # recover from the resulting non-fast-forward.
    committer_b = GitCommitter(repo_root=clone_b, sleep=lambda _s: None)
    run_dir_b = clone_b / "runs" / "WT-TEST-B"
    run_dir_b.mkdir(parents=True)
    (run_dir_b / "run.json").write_text('{"stage": "B"}\n', encoding="utf-8")
    sha_b = committer_b.commit(run_dir_b, "run B checkpoint")

    verify = tmp_path / "verify"
    _git("clone", str(bare), str(verify), cwd=tmp_path)
    assert (verify / "runs" / "WT-TEST-A" / "run.json").is_file()
    assert (verify / "runs" / "WT-TEST-B" / "run.json").is_file()
    log = _git("log", "-1", "--format=%H", cwd=verify)
    assert log.stdout.strip() == sha_b


def test_push_raises_after_exhausting_retries(tmp_path, monkeypatch):
    _bare, clone = _init_repo_with_remote(tmp_path)
    committer = GitCommitter(repo_root=clone, push_retries=2, sleep=lambda _s: None)

    run_dir = clone / "runs" / "WT-TEST-03"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text('{"stage": "X"}\n', encoding="utf-8")
    subprocess.run(["git", "add", "-A", str(run_dir)], cwd=clone, check=True)
    subprocess.run(["git", "commit", "-m", "checkpoint"], cwd=clone, check=True)

    # Point 'origin' at a repo that doesn't exist so every push attempt fails,
    # regardless of rebase — proves the retry loop terminates loudly (§14).
    subprocess.run(
        ["git", "remote", "set-url", "origin", str(tmp_path / "does-not-exist.git")],
        cwd=clone,
        check=True,
    )
    with pytest.raises(GitPushError, match="failed after 2 attempts"):
        committer._push_with_retry()

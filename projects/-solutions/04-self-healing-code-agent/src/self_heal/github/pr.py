"""GitHub PR creation via the GitHub REST API.

We use the REST API directly (via `requests`) rather than PyGithub to keep the
dependency footprint small and the behavior auditable. The integration is
env-gated: if `GITHUB_TOKEN` or `GITHUB_REPO` is missing, callers should skip
PR creation.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from self_heal.logging import get_logger

log = get_logger(__name__)

GITHUB_API = "https://api.github.com"


def _ensure_remote(repo_path: Path, repo_full_name: str) -> None:
    """Make sure the local repo has a remote `origin` pointing at the GitHub repo."""
    proc = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    expected = f"https://github.com/{repo_full_name}.git"
    if proc.returncode != 0:
        subprocess.run(
            ["git", "remote", "add", "origin", expected],
            cwd=repo_path,
            check=True,
            capture_output=True,
        )
    elif proc.stdout.strip() != expected:
        log.warning(
            "github.remote.mismatch",
            current=proc.stdout.strip(),
            expected=expected,
        )


def _push_branch(repo_path: Path, branch: str) -> None:
    """Push the branch to origin. Requires the user to have push access."""
    proc = subprocess.run(
        ["git", "push", "-u", "origin", branch],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git push origin {branch} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )


def create_pull_request(
    *,
    repo_path: Path,
    repo_full_name: str,
    token: str,
    branch: str,
    title: str,
    body: str,
    base: str = "main",
) -> str:
    """Push `branch` to origin and open a pull request.

    Returns the PR HTML URL.
    Raises RuntimeError on any failure.
    """
    import requests  # lazy import; only needed when PRs are actually opened

    _ensure_remote(repo_path, repo_full_name)
    _push_branch(repo_path, branch)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {
        "title": title,
        "body": body,
        "head": branch,
        "base": base,
        "draft": False,
    }
    resp = requests.post(
        f"{GITHUB_API}/repos/{repo_full_name}/pulls",
        headers=headers,
        data=json.dumps(payload),
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"GitHub PR creation failed ({resp.status_code}): {resp.text}")
    data = resp.json()
    url: str = data["html_url"]
    log.info("github.pr.created", url=url, number=data.get("number"))
    return url

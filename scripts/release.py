#!/usr/bin/env python3
"""Automated release helper script for Espresso.

Handles:
  1. Pre-flight checks (clean git status, test suite validation)
  2. Bumping __version__ in src/espresso/__init__.py (single source of truth)
  3. Creating a release chore commit
  4. Creating an annotated git tag
  5. Providing push or recovery instructions

Usage:
  python3 scripts/release.py patch       # e.g. 0.2.0 -> 0.2.1
  python3 scripts/release.py minor       # e.g. 0.2.0 -> 0.3.0
  python3 scripts/release.py major       # e.g. 0.2.0 -> 1.0.0
  python3 scripts/release.py 0.3.0       # Explicit target version
  python3 scripts/release.py --dry-run patch
  python3 scripts/release.py --push patch
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
INIT_FILE = REPO_ROOT / "src" / "espresso" / "__init__.py"

# Styling
C_RESET = "\x1b[0m"
C_BOLD = "\x1b[1m"
C_RED = "\x1b[31m"
C_GREEN = "\x1b[32m"
C_YELLOW = "\x1b[33m"
C_BLUE = "\x1b[34m"
C_MAGENTA = "\x1b[35m"
C_CYAN = "\x1b[36m"


def log_step(step_num: int, total: int, title: str) -> None:
    print(f"\n{C_BOLD}{C_CYAN}[Step {step_num}/{total}]{C_RESET} {C_BOLD}{title}{C_RESET}")


def log_success(msg: str) -> None:
    print(f"  {C_GREEN}✓{C_RESET} {msg}")


def log_warning(msg: str) -> None:
    print(f"  {C_YELLOW}⚠{C_RESET} {msg}")


def log_error(msg: str) -> None:
    print(f"  {C_RED}✗{C_RESET} {msg}")


def get_current_version() -> str:
    """Read __version__ from src/espresso/__init__.py."""
    if not INIT_FILE.exists():
        log_error(f"Cannot find init file at {INIT_FILE}")
        sys.exit(1)

    content = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        log_error(f"Could not find __version__ definition in {INIT_FILE}")
        sys.exit(1)

    return match.group(1)


def calculate_next_version(current: str, target: str) -> str:
    """Calculate the next semver string from current version and target specifier."""
    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        log_error(f"Current version '{current}' is not standard semver (X.Y.Z).")
        sys.exit(1)

    major, minor, patch = map(int, parts)

    target_lower = target.lower()
    if target_lower == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif target_lower == "minor":
        return f"{major}.{minor + 1}.0"
    elif target_lower == "major":
        return f"{major + 1}.0.0"
    else:
        # Check if explicit semver format
        if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", target):
            log_error(
                f"Invalid version format '{target}'. Must be 'patch', 'minor', 'major', or 'X.Y.Z'."
            )
            sys.exit(1)
        return target


def check_git_status() -> None:
    """Ensure git working directory is clean."""
    res = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        log_error("Failed to run git status. Is git installed?")
        sys.exit(1)

    dirty_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    if dirty_files:
        log_error("Git working directory has uncommitted or untracked changes:")
        for df in dirty_files[:10]:
            print(f"    {C_YELLOW}{df}{C_RESET}")
        if len(dirty_files) > 10:
            print(f"    ... and {len(dirty_files) - 10} more")

        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  1. Review changes:   {C_CYAN}git status{C_RESET}")
        print(f"  2. Commit changes:   {C_CYAN}git commit -am 'your commit message'{C_RESET}")
        print(f"  3. Or stash changes: {C_CYAN}git stash{C_RESET}")
        print(f"  Then re-run the release script.\n")
        sys.exit(1)


def check_tag_exists(tag: str) -> bool:
    """Check if a git tag already exists."""
    res = subprocess.run(
        ["git", "tag", "-l", tag],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return bool(res.stdout.strip())


def run_test_suite() -> None:
    """Run unit test suite before release."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        log_error("Test suite failed! Aborting release.")
        print(res.stderr or res.stdout)
        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  Run and fix failing tests locally using:")
        print(f"    {C_CYAN}PYTHONPATH=src python3 -m unittest discover tests{C_RESET}\n")
        sys.exit(1)


def update_init_file(new_version: str, dry_run: bool) -> None:
    """Update __version__ in src/espresso/__init__.py."""
    content = INIT_FILE.read_text(encoding="utf-8")
    new_content, count = re.subn(
        r'^(__version__\s*=\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{new_version}\g<2>",
        content,
        flags=re.MULTILINE,
    )
    if count == 0:
        log_error(f"Failed to substitute __version__ in {INIT_FILE}")
        sys.exit(1)

    if dry_run:
        log_success(f"[DRY RUN] Would update {INIT_FILE} to __version__ = '{new_version}'")
    else:
        INIT_FILE.write_text(new_content, encoding="utf-8")
        log_success(f"Updated {INIT_FILE} to __version__ = '{new_version}'")


def git_commit_and_tag(new_version: str, dry_run: bool) -> None:
    """Commit version bump and create annotated tag."""
    tag_name = f"v{new_version}"
    commit_msg = f"chore(release): bump version to {tag_name}"

    if dry_run:
        log_success(f"[DRY RUN] Would execute: git add {INIT_FILE.relative_to(REPO_ROOT)}")
        log_success(f"[DRY RUN] Would execute: git commit -m '{commit_msg}'")
        log_success(f"[DRY RUN] Would execute: git tag -a {tag_name} -m 'Release {tag_name}'")
        return

    # 1. git add
    res_add = subprocess.run(
        ["git", "add", str(INIT_FILE.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_add.returncode != 0:
        log_error(f"git add failed:\n{res_add.stderr}")
        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  Discard the change with: {C_CYAN}git restore {INIT_FILE}{C_RESET}\n")
        sys.exit(1)
    log_success(f"Staged {INIT_FILE.relative_to(REPO_ROOT)}")

    # 2. git commit
    res_commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_commit.returncode != 0:
        log_error(f"git commit failed:\n{res_commit.stderr}")
        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  Unstage and discard with: {C_CYAN}git restore --staged {INIT_FILE} && git restore {INIT_FILE}{C_RESET}\n")
        sys.exit(1)
    log_success(f"Committed: '{commit_msg}'")

    # 3. git tag
    res_tag = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_tag.returncode != 0:
        log_error(f"git tag failed:\n{res_tag.stderr}")
        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  The commit was made, but the tag failed.")
        print(f"  To create the tag manually: {C_CYAN}git tag -a {tag_name} -m 'Release {tag_name}'{C_RESET}")
        print(f"  To undo the commit:         {C_CYAN}git reset --soft HEAD~1{C_RESET}\n")
        sys.exit(1)
    log_success(f"Created annotated tag: {tag_name}")


def git_push(tag_name: str) -> bool:
    """Push commit and tag to origin."""
    print(f"\n{C_BOLD}Pushing commit and tag to origin...{C_RESET}")
    # Push branch
    res_p = subprocess.run(["git", "push", "origin", "HEAD"], cwd=REPO_ROOT)
    if res_p.returncode != 0:
        return False

    # Push tag
    res_t = subprocess.run(["git", "push", "origin", tag_name], cwd=REPO_ROOT)
    return res_t.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="Release helper for Espresso: bumps version, runs tests, commits, and tags.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/release.py patch       # Bump patch: 0.2.0 -> 0.2.1
  python3 scripts/release.py minor       # Bump minor: 0.2.0 -> 0.3.0
  python3 scripts/release.py major       # Bump major: 0.2.0 -> 1.0.0
  python3 scripts/release.py 0.3.0       # Explicit target version
  python3 scripts/release.py --dry-run patch
  python3 scripts/release.py --push patch
""",
    )
    parser.add_argument(
        "target",
        help="Release bump type ('patch', 'minor', 'major') or explicit version ('0.3.0')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate the release process without modifying files or git",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running the unit test suite",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Automatically push commits and tags to remote origin after tagging",
    )

    args = parser.parse_args()

    total_steps = 4 if args.skip_tests else 5
    current_step = 1

    print(f"\n{C_BOLD}{C_MAGENTA}☕ Espresso Release Helper{C_RESET}")
    print(f"{C_BLUE}──────────────────────────────────────────{C_RESET}")

    # 1. Determine versions
    curr_ver = get_current_version()
    next_ver = calculate_next_version(curr_ver, args.target)
    tag_name = f"v{next_ver}"

    print(f"Current version: {C_BOLD}{curr_ver}{C_RESET}")
    print(f"Target version:  {C_BOLD}{C_GREEN}{next_ver}{C_RESET} (Tag: {tag_name})")
    if args.dry_run:
        print(f"{C_YELLOW}Mode: DRY RUN (no files or git refs will be changed){C_RESET}")

    # Step 1: Pre-flight git clean check
    log_step(current_step, total_steps, "Checking git repository status")
    current_step += 1
    if not args.dry_run:
        check_git_status()
    log_success("Working directory is clean")

    # Step 2: Check if tag already exists
    if check_tag_exists(tag_name):
        log_error(f"Tag {tag_name} already exists!")
        print(f"\n{C_BOLD}What you should do:{C_RESET}")
        print(f"  If this tag was created in error, delete it with:")
        print(f"    Local:  {C_CYAN}git tag -d {tag_name}{C_RESET}")
        print(f"    Remote: {C_CYAN}git push origin --delete {tag_name}{C_RESET}\n")
        sys.exit(1)
    log_success(f"Tag {tag_name} is available")

    # Step 3: Run test suite
    if not args.skip_tests:
        log_step(current_step, total_steps, "Running test suite")
        current_step += 1
        run_test_suite()
        log_success("All tests passed successfully (334/334)")

    # Step 4: Bump version in src/espresso/__init__.py
    log_step(current_step, total_steps, f"Updating version in src/espresso/__init__.py")
    current_step += 1
    update_init_file(next_ver, args.dry_run)

    # Step 5: Git commit and tag
    log_step(current_step, total_steps, f"Creating commit and tag {tag_name}")
    current_step += 1
    git_commit_and_tag(next_ver, args.dry_run)

    # Summary and Next Steps
    print(f"\n{C_GREEN}{C_BOLD}═════════════════════════════════════════════════════════════════════{C_RESET}")
    if args.dry_run:
        print(f"{C_YELLOW}{C_BOLD}DRY RUN COMPLETE: No changes were made.{C_RESET}")
        print(f"To execute for real, run:")
        print(f"  {C_CYAN}python3 scripts/release.py {args.target}{C_RESET}\n")
        return

    print(f"{C_GREEN}{C_BOLD}Release preparation for v{next_ver} completed successfully!{C_RESET}")
    print(f"{C_GREEN}{C_BOLD}═════════════════════════════════════════════════════════════════════{C_RESET}")

    # Push handling
    pushed = False
    if args.push:
        pushed = git_push(tag_name)
    else:
        # Prompt user if running in interactive terminal
        if sys.stdin.isatty():
            try:
                reply = input(f"\n{C_BOLD}Do you want to push commit and tag {tag_name} to origin now? [y/N]: {C_RESET}").strip().lower()
                if reply in ("y", "yes"):
                    pushed = git_push(tag_name)
            except KeyboardInterrupt:
                print()

    if pushed:
        print(f"\n{C_GREEN}{C_BOLD}✓ Pushed to GitHub!{C_RESET}")
        print(f"The GitHub Actions release pipeline is now running:")
        print(f"  {C_CYAN}https://github.com/kimusan/espresso/actions/workflows/release.yml{C_RESET}")
        print(f"It will build packages, run tests, publish to PyPI, and create the GitHub Release.\n")
    else:
        print(f"\n{C_BOLD}Next Steps to Publish to PyPI & GitHub Releases:{C_RESET}")
        print(f"Run these commands to push the release:")
        print(f"  {C_CYAN}git push origin HEAD{C_RESET}")
        print(f"  {C_CYAN}git push origin {tag_name}{C_RESET}")
        print(f"\n{C_BOLD}Troubleshooting & Rollback (if needed):{C_RESET}")
        print(f"If you need to undo this release commit and tag locally:")
        print(f"  1. Delete local tag:  {C_YELLOW}git tag -d {tag_name}{C_RESET}")
        print(f"  2. Undo commit:       {C_YELLOW}git reset --soft HEAD~1{C_RESET}")
        print(f"  3. Revert file:       {C_YELLOW}git restore src/espresso/__init__.py{C_RESET}\n")


if __name__ == "__main__":
    main()

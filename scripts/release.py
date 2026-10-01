#!/usr/bin/env python3
"""Automated, interactive release manager for Espresso.

Powered by Espresso itself (TEA, Crema styling, PipelineProgress, ToastManager,
Dialog, and Confetti particles).

Usage:
  # Interactive Espresso TUI Mode (Default in terminal):
  ./scripts/release.py patch       # e.g. 0.2.0 -> 0.2.1
  ./scripts/release.py minor       # e.g. 0.2.0 -> 0.3.0
  ./scripts/release.py major       # e.g. 0.2.0 -> 1.0.0
  ./scripts/release.py 0.3.0       # Explicit target version
  ./scripts/release.py --dry-run patch
  ./scripts/release.py --push patch

  # Headless / Plain CLI Mode:
  ./scripts/release.py --cli patch
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Ensure src/ is on sys.path to import espresso
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

INIT_FILE = SRC_DIR / "espresso" / "__init__.py"

# Espresso Framework Imports
from espresso import Cmd, KeyMsg, Model, Msg, Program, WindowSizeMsg, batch, quit_app
from espresso.beans import (
    Confetti,
    Dialog,
    DialogResultMsg,
    PipelineCompleteMsg,
    PipelineProgress,
    PipelineStage,
    StageCompleteMsg,
    StageFailedMsg,
    StageStartMsg,
    StageStatus,
    ToastLevel,
    ToastManager,
)
from espresso.crema import (
    ROUNDED_BORDER,
    Align,
    Style,
    linear_gradient,
    place,
    place_overlay,
    string_width,
    truncate_ansi,
)

# ANSI styling for CLI mode
C_RESET = "\x1b[0m"
C_BOLD = "\x1b[1m"
C_RED = "\x1b[31m"
C_GREEN = "\x1b[32m"
C_YELLOW = "\x1b[33m"
C_BLUE = "\x1b[34m"
C_MAGENTA = "\x1b[35m"
C_CYAN = "\x1b[36m"


def get_current_version() -> str:
    """Read __version__ from src/espresso/__init__.py."""
    if not INIT_FILE.exists():
        print(f"{C_RED}Error: Cannot find init file at {INIT_FILE}{C_RESET}")
        sys.exit(1)

    content = INIT_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
    if not match:
        print(f"{C_RED}Error: Could not find __version__ in {INIT_FILE}{C_RESET}")
        sys.exit(1)

    return match.group(1)


def calculate_next_version(current: str, target: str) -> str:
    """Calculate the next semver string from current version and target specifier."""
    parts = current.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        print(f"{C_RED}Error: Current version '{current}' is not standard semver (X.Y.Z).{C_RESET}")
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
        if not re.match(r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$", target):
            print(
                f"{C_RED}Error: Invalid version format '{target}'. Must be 'patch', 'minor', 'major', or 'X.Y.Z'.{C_RESET}"
            )
            sys.exit(1)
        return target


# ==============================================================================
# Core Release Actions (Used by both TUI and CLI modes)
# ==============================================================================

def check_git_status() -> None:
    res = subprocess.run(["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("git status failed. Is git installed?")
    dirty_files = [line.strip() for line in res.stdout.splitlines() if line.strip()]
    if dirty_files:
        sample = dirty_files[0]
        extra = f" (+{len(dirty_files) - 1} more)" if len(dirty_files) > 1 else ""
        raise RuntimeError(f"Uncommitted files present: {sample}{extra}. Commit or stash changes.")


def check_tag_available(tag_name: str) -> None:
    res = subprocess.run(["git", "tag", "-l", tag_name], cwd=REPO_ROOT, capture_output=True, text=True)
    if res.stdout.strip():
        raise RuntimeError(f"Tag {tag_name} already exists locally!")


def run_unit_tests() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR)
    res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise RuntimeError("Test suite failed! Run: PYTHONPATH=src python3 -m unittest discover tests")
    match = re.search(r"Ran (\d+) tests", res.stderr or res.stdout)
    return int(match.group(1)) if match else 0


def update_version_in_init(new_version: str, dry_run: bool) -> None:
    content = INIT_FILE.read_text(encoding="utf-8")
    new_content, count = re.subn(
        r'^(__version__\s*=\s*["\'])[^"\']+(["\'])',
        rf"\g<1>{new_version}\g<2>",
        content,
        flags=re.MULTILINE,
    )
    if count == 0:
        raise RuntimeError(f"Failed to substitute __version__ in {INIT_FILE}")
    if not dry_run:
        INIT_FILE.write_text(new_content, encoding="utf-8")


def git_commit_and_tag(new_version: str, dry_run: bool) -> None:
    tag_name = f"v{new_version}"
    commit_msg = f"chore(release): bump version to {tag_name}"

    if dry_run:
        return

    # 1. git add
    res_add = subprocess.run(
        ["git", "add", str(INIT_FILE.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_add.returncode != 0:
        raise RuntimeError(f"git add failed: {res_add.stderr.strip()}")

    # 2. git commit
    res_commit = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {res_commit.stderr.strip()}")

    # 3. git tag
    res_tag = subprocess.run(
        ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if res_tag.returncode != 0:
        raise RuntimeError(f"git tag failed: {res_tag.stderr.strip()}")


def do_rollback(new_version: str) -> None:
    tag_name = f"v{new_version}"
    subprocess.run(["git", "tag", "-d", tag_name], cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "reset", "--soft", "HEAD~1"], cwd=REPO_ROOT, capture_output=True)
    subprocess.run(["git", "restore", str(INIT_FILE)], cwd=REPO_ROOT, capture_output=True)


@dataclass(frozen=True)
class GitPushResultMsg(Msg):
    success: bool
    error: str = ""


def do_git_push_cmd(tag_name: str) -> Cmd:
    def _run() -> Msg:
        res1 = subprocess.run(["git", "push", "origin", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True)
        if res1.returncode != 0:
            return GitPushResultMsg(success=False, error=res1.stderr.strip() or "Failed to push branch")
        res2 = subprocess.run(["git", "push", "origin", tag_name], cwd=REPO_ROOT, capture_output=True, text=True)
        if res2.returncode != 0:
            return GitPushResultMsg(success=False, error=res2.stderr.strip() or f"Failed to push tag {tag_name}")
        return GitPushResultMsg(success=True)

    return _run


# ==============================================================================
# Rich Espresso TUI Application
# ==============================================================================

class ReleaseTUI(Model):
    """Full-screen interactive release manager powered by Espresso TEA."""

    def __init__(
        self,
        curr_ver: str,
        next_ver: str,
        dry_run: bool = False,
        skip_tests: bool = False,
        push_immediate: bool = False,
    ) -> None:
        self.curr_ver = curr_ver
        self.next_ver = next_ver
        self.tag_name = f"v{next_ver}"
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.push_immediate = push_immediate

        self.width = 80
        self.height = 24
        self.status_line = "Preparing pipeline..."
        self.push_status: str | None = None
        self.is_rolled_back = False
        self.is_finished = False

        # 1. Pipeline Progress Stages
        stages = [
            PipelineStage(
                title="Git Working Tree Status",
                action=lambda: check_git_status() if not self.dry_run else None,
                description="Verify repository has no uncommitted changes",
            ),
            PipelineStage(
                title=f"Tag Availability ({self.tag_name})",
                action=lambda: check_tag_available(self.tag_name) if not self.dry_run else None,
                description="Ensure tag does not already exist",
            ),
        ]

        if not self.skip_tests:
            stages.append(
                PipelineStage(
                    title="Unit Test Suite",
                    action=run_unit_tests,
                    description="Run full automated regression test suite",
                )
            )

        stages.append(
            PipelineStage(
                title=f"Bump Version (➔ {self.next_ver})",
                action=lambda: update_version_in_init(self.next_ver, self.dry_run),
                description="Update __version__ in src/espresso/__init__.py",
            )
        )
        stages.append(
            PipelineStage(
                title=f"Chore Commit & Tag ({self.tag_name})",
                action=lambda: git_commit_and_tag(self.next_ver, self.dry_run),
                description="Commit version bump and create annotated git tag",
            )
        )

        self.pipeline = PipelineProgress(
            stages=stages,
            title="Release Execution Pipeline",
            width=68,
            auto_start=True,
            show_stages=True,
            show_timer=True,
        )

        # 2. Toast Notifications
        self.toasts = ToastManager()

        # 3. Celebratory Confetti Emitter
        self.confetti = Confetti(width=self.width, height=self.height)

        # 4. Confirmation Dialog Modal
        self.dialog: Dialog | None = None

    def init(self) -> Cmd | None:
        cmds: list[Cmd] = []
        pipe_cmd = self.pipeline.init()
        if pipe_cmd:
            cmds.append(pipe_cmd)
        _, toast_cmd = self.toasts.add(
            f"Release v{self.next_ver} initiated{' (Dry Run)' if self.dry_run else ''}",
            ToastLevel.INFO,
            duration=3.0,
        )
        cmds.append(toast_cmd)
        return batch(*cmds)

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        cmds: list[Cmd] = []

        # Handle Window Resize
        if isinstance(msg, WindowSizeMsg):
            self.width = max(msg.width, 60)
            self.height = max(msg.height, 20)
            self.pipeline.width = min(self.width - 8, 72)
            self.confetti.width = self.width
            self.confetti.height = self.height
            return self, None

        # Route to Dialog Modal if open
        if self.dialog is not None:
            if isinstance(msg, KeyMsg) and msg.key in ("esc",):
                self.dialog = None
                return self, None

            self.dialog, d_cmd = self.dialog.update(msg)
            if d_cmd:
                cmds.append(d_cmd)

            if isinstance(msg, DialogResultMsg):
                # Selected dialog action
                action = msg.action
                self.dialog = None
                if action == "Push to GitHub":
                    self.push_status = "Pushing to GitHub origin..."
                    _, t_cmd = self.toasts.add("Pushing commit and tag to GitHub...", ToastLevel.INFO, 3.0)
                    cmds.append(t_cmd)
                    cmds.append(do_git_push_cmd(self.tag_name))
                elif action == "Rollback / Undo":
                    do_rollback(self.next_ver)
                    self.is_rolled_back = True
                    self.is_finished = True
                    self.status_line = "Release rolled back locally."
                    _, t_cmd = self.toasts.add("Release commit and tag rolled back.", ToastLevel.WARNING, 4.0)
                    cmds.append(t_cmd)
                else:  # Keep Local
                    self.is_finished = True
                    self.push_status = "Release saved locally (not pushed to GitHub)."
                    _, t_cmd = self.toasts.add("Release kept locally. You can push anytime.", ToastLevel.INFO, 4.0)
                    cmds.append(t_cmd)

            return self, batch(*cmds) if cmds else None

        # Update Toasts
        self.toasts, t_cmd = self.toasts.update(msg)
        if t_cmd:
            cmds.append(t_cmd)

        # Update Confetti
        self.confetti, c_cmd = self.confetti.update(msg)
        if c_cmd:
            cmds.append(c_cmd)

        # Handle Git Push Result
        if isinstance(msg, GitPushResultMsg):
            self.is_finished = True
            if msg.success:
                self.push_status = "Successfully pushed to GitHub! Release pipeline triggered."
                _, t_cmd = self.toasts.add("✓ Pushed to GitHub! Release workflow active.", ToastLevel.SUCCESS, 5.0)
                cmds.append(t_cmd)
                b_cmd = self.confetti.fire(count=55, origin=(self.width // 2, self.height // 3))
                if b_cmd:
                    cmds.append(b_cmd)
            else:
                self.push_status = f"Push failed: {msg.error}"
                _, t_cmd = self.toasts.add(f"Push failed: {msg.error}", ToastLevel.ERROR, 6.0)
                cmds.append(t_cmd)
            return self, batch(*cmds) if cmds else None

        # Handle Pipeline Events
        if isinstance(msg, StageCompleteMsg):
            idx = msg.stage_index
            stage_name = self.pipeline.stages[idx].title if idx < len(self.pipeline.stages) else f"Stage {idx}"
            _, t_cmd = self.toasts.add(f"Completed: {stage_name}", ToastLevel.SUCCESS, 2.0)
            cmds.append(t_cmd)

        elif isinstance(msg, StageFailedMsg):
            _, t_cmd = self.toasts.add(f"Failed: {msg.error}", ToastLevel.ERROR, 5.0)
            cmds.append(t_cmd)

        elif isinstance(msg, PipelineCompleteMsg):
            if msg.success:
                self.status_line = f"All pipeline stages completed in {msg.total_duration:.2f}s!"
                if self.dry_run:
                    self.is_finished = True
                    _, t_cmd = self.toasts.add("Dry run completed successfully!", ToastLevel.SUCCESS, 4.0)
                    cmds.append(t_cmd)
                elif self.push_immediate:
                    self.push_status = "Pushing to GitHub origin..."
                    cmds.append(do_git_push_cmd(self.tag_name))
                else:
                    # Present user with action dialog
                    self.dialog = Dialog(
                        title=f"Release {self.tag_name} Ready!",
                        message=(
                            f"Version {self.next_ver} has been committed and tagged locally.\n\n"
                            f"Push to GitHub to trigger PyPI publishing and the\n"
                            f"automated multi-platform release builds?"
                        ),
                        buttons=("Push to GitHub", "Keep Local", "Rollback / Undo"),
                        width=56,
                    )
            else:
                self.status_line = "Pipeline aborted due to errors."

        # Forward to Pipeline
        self.pipeline, p_cmd = self.pipeline.update(msg)
        if p_cmd:
            cmds.append(p_cmd)

        # Keyboard Controls
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        inner_w = max(40, self.width - 2)

        # 1. Top Header Banner with TrueColor Gradient
        banner_text = f"☕ ESPRESSO RELEASE MANAGER • v{self.curr_ver} ➔ v{self.next_ver}"
        gradient_banner = linear_gradient(banner_text, "#00E5FF", "#7D56F4")
        header_card = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#7D56F4")
            .width(inner_w)
            .align(Align.CENTER)
            .render(gradient_banner)
        )

        # 2. Pipeline Container
        pipeline_view = self.pipeline.view()
        pipeline_card = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#00E5FF" if self.pipeline.is_running else ("#9ECE6A" if self.pipeline.is_finished and not self.pipeline.is_failed else "#555577"))
            .width(inner_w)
            .padding(0, 1)
            .render(pipeline_view)
        )

        # 3. Status & Instruction Panel
        status_lines: list[str] = []
        if self.dry_run:
            status_lines.append(f"{C_YELLOW}⚠ Mode: DRY RUN (no files modified, no git commits or tags made){C_RESET}")
        elif self.is_rolled_back:
            status_lines.append(f"{C_YELLOW}↩️ Release was rolled back. Working directory restored.{C_RESET}")
        elif self.push_status:
            status_lines.append(f"{C_BOLD}{self.push_status}{C_RESET}")
            if "Successfully pushed" in self.push_status:
                status_lines.append(f"{C_CYAN}View CI workflow: https://github.com/kimusan/espresso/actions{C_RESET}")
                status_lines.append(f"{C_CYAN}PyPI project:     https://pypi.org/project/espressoTUI{C_RESET}")
        elif self.pipeline.is_finished and not self.pipeline.is_failed:
            status_lines.append(f"{C_GREEN}✓ Release {self.tag_name} prepared locally!{C_RESET}")
            status_lines.append(f"Push manually with: {C_CYAN}git push origin HEAD && git push origin {self.tag_name}{C_RESET}")
        elif self.pipeline.is_failed:
            status_lines.append(f"{C_RED}✗ Pipeline failed. Review the failed stage error above.{C_RESET}")
            status_lines.append("Discard any uncommitted changes with: git restore src/espresso/__init__.py")

        status_content = "\n".join(status_lines) if status_lines else f"Status: {self.status_line}"
        status_card = (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#414868")
            .width(inner_w)
            .padding(0, 1)
            .render(status_content)
        )

        # 4. Bottom Keybindings Bar
        bottom_bar = Style().foreground("#8888AA").render(
            " [q] Quit   [Tab/Arrows] Navigate Dialog   [Enter] Confirm Choice "
        )

        # Composite screen
        content = f"{header_card}\n{pipeline_card}\n{status_card}\n{bottom_bar}"

        # 5. Composite Floating Toast Notifications
        if self.toasts.has_toasts:
            toast_str = self.toasts.view()
            content = place_overlay(content, toast_str, center=False, dim_backdrop=False)

        # 6. Composite Modal Dialog (if open)
        if self.dialog is not None:
            content = place_overlay(content, self.dialog.view(), center=True, dim_backdrop=True)

        # 7. Composite Confetti Particles
        if self.confetti.is_active:
            content = place_overlay(content, self.confetti.view(), center=False, dim_backdrop=False)

        return content


# ==============================================================================
# CLI Runner (Fallback for Non-Interactive / CI environments)
# ==============================================================================

def run_cli_mode(curr_ver: str, next_ver: str, dry_run: bool, skip_tests: bool, push: bool) -> int:
    tag_name = f"v{next_ver}"
    total_steps = 4 if skip_tests else 5
    step = 1

    print(f"\n{C_BOLD}{C_MAGENTA}☕ Espresso Release Helper (CLI Mode){C_RESET}")
    print(f"{C_BLUE}──────────────────────────────────────────{C_RESET}")
    print(f"Current version: {C_BOLD}{curr_ver}{C_RESET}")
    print(f"Target version:  {C_BOLD}{C_GREEN}{next_ver}{C_RESET} (Tag: {tag_name})")
    if dry_run:
        print(f"{C_YELLOW}Mode: DRY RUN (no files or git refs will be changed){C_RESET}")

    # Step 1
    print(f"\n{C_BOLD}{C_CYAN}[Step {step}/{total_steps}]{C_RESET} Checking git repository status")
    step += 1
    if not dry_run:
        check_git_status()
    print(f"  {C_GREEN}✓{C_RESET} Working directory is clean")

    # Step 2
    check_tag_available(tag_name)
    print(f"  {C_GREEN}✓{C_RESET} Tag {tag_name} is available")

    # Step 3
    if not skip_tests:
        print(f"\n{C_BOLD}{C_CYAN}[Step {step}/{total_steps}]{C_RESET} Running test suite")
        step += 1
        num_tests = run_unit_tests()
        print(f"  {C_GREEN}✓{C_RESET} All {num_tests} tests passed successfully")

    # Step 4
    print(f"\n{C_BOLD}{C_CYAN}[Step {step}/{total_steps}]{C_RESET} Updating version in src/espresso/__init__.py")
    step += 1
    update_version_in_init(next_ver, dry_run)
    print(f"  {C_GREEN}✓{C_RESET} Updated __version__ to '{next_ver}'")

    # Step 5
    print(f"\n{C_BOLD}{C_CYAN}[Step {step}/{total_steps}]{C_RESET} Creating chore commit and tag {tag_name}")
    step += 1
    git_commit_and_tag(next_ver, dry_run)
    print(f"  {C_GREEN}✓{C_RESET} Created commit & tag: {tag_name}")

    if dry_run:
        print(f"\n{C_YELLOW}{C_BOLD}DRY RUN COMPLETE: No changes were made.{C_RESET}\n")
        return 0

    if push:
        print(f"\nPushing {tag_name} to origin...")
        subprocess.run(["git", "push", "origin", "HEAD"], cwd=REPO_ROOT, check=True)
        subprocess.run(["git", "push", "origin", tag_name], cwd=REPO_ROOT, check=True)
        print(f"\n{C_GREEN}{C_BOLD}✓ Pushed to GitHub! Release pipeline triggered.{C_RESET}\n")
    else:
        print(f"\n{C_GREEN}{C_BOLD}Release v{next_ver} prepared locally!{C_RESET}")
        print("To publish, push to origin:")
        print(f"  {C_CYAN}git push origin HEAD && git push origin {tag_name}{C_RESET}\n")

    return 0


# ==============================================================================
# Entry Point
# ==============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="release.py",
        description="Espresso Release Manager with interactive TUI, progress tracking, and notifications.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  ./scripts/release.py patch       # Interactive TUI: bump patch (0.2.0 -> 0.2.1)
  ./scripts/release.py minor       # Interactive TUI: bump minor (0.2.0 -> 0.3.0)
  ./scripts/release.py 0.3.0       # Interactive TUI: explicit version
  ./scripts/release.py --push patch # Interactive TUI with automated push
  ./scripts/release.py --cli patch  # Headless CLI mode
""",
    )
    parser.add_argument(
        "target",
        help="Release bump type ('patch', 'minor', 'major') or explicit version ('0.3.0')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate release process without modifying files or git",
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
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Force plain CLI mode instead of interactive Espresso TUI",
    )

    args = parser.parse_args()

    curr_ver = get_current_version()
    next_ver = calculate_next_version(curr_ver, args.target)

    # If user requested --cli or stdin is not a TTY: use CLI mode
    if args.cli or not sys.stdin.isatty():
        sys.exit(run_cli_mode(curr_ver, next_ver, args.dry_run, args.skip_tests, args.push))

    # Otherwise launch full Espresso TUI application!
    app = ReleaseTUI(
        curr_ver=curr_ver,
        next_ver=next_ver,
        dry_run=args.dry_run,
        skip_tests=args.skip_tests,
        push_immediate=args.push,
    )
    program = Program(app, alt_screen=True, mouse=True)
    program.run()


if __name__ == "__main__":
    main()

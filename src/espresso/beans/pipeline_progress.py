"""Multi-stage task pipeline progress runner component.

Inspired by mritd/bubbles/progressbar.
Executes a sequence of stages asynchronously, tracking progress,
elapsed execution times, and reporting success/error diagnostics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.border import ROUNDED_BORDER
from espresso.crema.style import Style
from espresso.crema.width import string_width, truncate_ansi


class StageStatus(Enum):
    """Execution status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """An individual stage in an execution pipeline."""

    title: str
    action: Callable[[], Any] | None = None
    description: str = ""
    status: StageStatus = StageStatus.PENDING
    duration: float = 0.0
    error: str | None = None
    result: Any = None


@dataclass(frozen=True)
class StageStartMsg(Msg):
    """Message emitted when a pipeline stage begins execution."""

    stage_index: int


@dataclass(frozen=True)
class StageCompleteMsg(Msg):
    """Message emitted when a stage completes successfully."""

    stage_index: int
    duration: float
    result: Any = None


@dataclass(frozen=True)
class StageFailedMsg(Msg):
    """Message emitted when a stage raises an exception or fails."""

    stage_index: int
    error: str


@dataclass(frozen=True)
class PipelineCompleteMsg(Msg):
    """Message emitted when all stages have completed (or aborted)."""

    success: bool
    total_duration: float


class PipelineProgress(Model):
    """Active multi-stage task runner with progress animation and status reporting."""

    def __init__(
        self,
        stages: Sequence[PipelineStage | tuple[str, Callable[[], Any] | None]] = (),
        title: str = "Pipeline Tasks",
        width: int = 50,
        auto_start: bool = False,
        show_stages: bool = True,
        show_timer: bool = True,
    ) -> None:
        self.title = title
        self.width = max(30, width)
        self.auto_start = auto_start
        self.show_stages = show_stages
        self.show_timer = show_timer

        self.stages: list[PipelineStage] = []
        for s in stages:
            if isinstance(s, PipelineStage):
                self.stages.append(s)
            elif isinstance(s, tuple) and len(s) == 2:
                self.stages.append(PipelineStage(title=s[0], action=s[1]))
            else:
                self.stages.append(PipelineStage(title=str(s)))

        self.current_stage: int = 0
        self.is_running: bool = False
        self.is_finished: bool = False
        self.is_failed: bool = False
        self.start_time: float | None = None
        self.total_duration: float = 0.0

        # Styling
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.pending_style = Style().faint(True)
        self.running_style = Style().bold(True).foreground("#00E5FF")
        self.success_style = Style().bold(True).foreground("#00E676")
        self.failed_style = Style().bold(True).foreground("#FF5252")
        self.bar_fill_style = Style().foreground("#00E676")
        self.bar_empty_style = Style().faint(True)
        self.dim_style = Style().faint(True)

    @property
    def progress(self) -> float:
        """Return the completion percentage as a float between 0.0 and 1.0."""
        if not self.stages:
            return 1.0 if self.is_finished else 0.0
        success_count = sum(1 for s in self.stages if s.status == StageStatus.SUCCESS)
        return success_count / len(self.stages)

    def start(self) -> tuple[PipelineProgress, Cmd | None]:
        """Start or restart the pipeline execution from the current pending stage."""
        if not self.stages or self.is_running:
            return self, None

        self.is_running = True
        self.is_finished = False
        self.is_failed = False
        if self.start_time is None:
            self.start_time = time.monotonic()

        # Find the first non-completed stage
        for i, s in enumerate(self.stages):
            if s.status in (StageStatus.PENDING, StageStatus.RUNNING, StageStatus.FAILED):
                self.current_stage = i
                break

        stage_idx = self.current_stage
        def _cmd() -> Msg:
            return StageStartMsg(stage_index=stage_idx)

        return self, _cmd

    def init(self) -> Cmd | None:
        """TEA init callback."""
        if self.auto_start and self.stages:
            _, cmd = self.start()
            return cmd
        return None

    def update(self, msg: Msg) -> tuple[PipelineProgress, Cmd | None]:
        """Process pipeline progression and control messages."""
        if isinstance(msg, StageStartMsg):
            idx = msg.stage_index
            if 0 <= idx < len(self.stages):
                stage = self.stages[idx]
                stage.status = StageStatus.RUNNING
                self.current_stage = idx

                # Run the stage action asynchronously
                def _run_action() -> Msg:
                    t0 = time.monotonic()
                    try:
                        res = None
                        if stage.action is not None:
                            res = stage.action()
                        dur = time.monotonic() - t0
                        return StageCompleteMsg(stage_index=idx, duration=dur, result=res)
                    except Exception as exc:
                        dur = time.monotonic() - t0
                        return StageFailedMsg(stage_index=idx, error=str(exc))

                return self, _run_action
            return self, None

        elif isinstance(msg, StageCompleteMsg):
            idx = msg.stage_index
            if 0 <= idx < len(self.stages):
                stage = self.stages[idx]
                stage.status = StageStatus.SUCCESS
                stage.duration = msg.duration
                stage.result = msg.result

            # Check next stage
            next_idx = idx + 1
            if next_idx < len(self.stages):
                self.current_stage = next_idx
                def _start_next() -> Msg:
                    return StageStartMsg(stage_index=next_idx)
                return self, _start_next
            else:
                self.is_running = False
                self.is_finished = True
                self.total_duration = time.monotonic() - (self.start_time or time.monotonic())
                def _pipe_done() -> Msg:
                    return PipelineCompleteMsg(success=True, total_duration=self.total_duration)
                return self, _pipe_done

        elif isinstance(msg, StageFailedMsg):
            idx = msg.stage_index
            if 0 <= idx < len(self.stages):
                stage = self.stages[idx]
                stage.status = StageStatus.FAILED
                stage.error = msg.error

            self.is_running = False
            self.is_finished = True
            self.is_failed = True
            self.total_duration = time.monotonic() - (self.start_time or time.monotonic())
            def _pipe_failed() -> Msg:
                return PipelineCompleteMsg(success=False, total_duration=self.total_duration)
            return self, _pipe_failed

        elif isinstance(msg, KeyMsg):
            match msg.key:
                case "enter" | "r":
                    if not self.is_running:
                        return self.start()
                case "s":
                    # Step one stage manually if not currently running
                    if not self.is_running and self.current_stage < len(self.stages):
                        idx = self.current_stage
                        self.is_running = True
                        def _step() -> Msg:
                            return StageStartMsg(stage_index=idx)
                        return self, _step
                case "q" | "esc":
                    if self.is_running:
                        self.is_running = False
                        self.is_finished = True
                        self.is_failed = True
                        return self, None

        return self, None

    def view(self) -> str:
        """Render the pipeline progress bar and stage list."""
        lines: list[str] = []

        # 1. Header with Title and Overall Status Badge
        pct = int(self.progress * 100)
        if self.is_failed:
            status_badge = self.failed_style.render("[FAILED]")
        elif self.is_finished:
            status_badge = self.success_style.render("[COMPLETED]")
        elif self.is_running:
            status_badge = self.running_style.render(f"[RUNNING {self.current_stage + 1}/{len(self.stages)}]")
        else:
            status_badge = self.pending_style.render("[READY]")

        time_str = f"{self.total_duration:.1f}s" if self.is_finished else ""
        header_left = f"{self.title_style.render(self.title)} {status_badge}"
        if self.show_timer and time_str:
            pad = max(1, self.width - string_width(header_left) - len(time_str))
            lines.append(f"{header_left}{' ' * pad}{self.dim_style.render(time_str)}")
        else:
            lines.append(header_left)

        lines.append("")

        # 2. Progress Bar
        pct_label = f" {pct:>3}%"
        bar_width = max(10, self.width - len(pct_label) - 2)
        filled_len = int(round(bar_width * self.progress))
        empty_len = bar_width - filled_len

        bar_filled = self.bar_fill_style.render("█" * filled_len)
        bar_empty = self.bar_empty_style.render("░" * empty_len)
        lines.append(f"[{bar_filled}{bar_empty}]{self.dim_style.render(pct_label)}")

        # 3. Stage Details
        if self.show_stages and self.stages:
            lines.append("")
            for idx, stage in enumerate(self.stages):
                match stage.status:
                    case StageStatus.SUCCESS:
                        icon = self.success_style.render("✔")
                        dur_text = f" ({stage.duration:.2f}s)" if stage.duration > 0 else ""
                        title_text = self.success_style.render(stage.title)
                        stage_line = f" {icon} {title_text}{self.dim_style.render(dur_text)}"
                    case StageStatus.RUNNING:
                        icon = self.running_style.render("▶")
                        stage_line = f" {icon} {self.running_style.render(stage.title)} {self.dim_style.render('(running...)')}"
                    case StageStatus.FAILED:
                        icon = self.failed_style.render("✖")
                        err_text = f" - {stage.error}" if stage.error else ""
                        stage_line = f" {icon} {self.failed_style.render(stage.title)}{self.failed_style.render(err_text)}"
                    case StageStatus.SKIPPED:
                        icon = self.dim_style.render("↷")
                        stage_line = f" {icon} {self.dim_style.render(stage.title)} {self.dim_style.render('(skipped)')}"
                    case _:
                        icon = self.pending_style.render("○")
                        stage_line = f" {icon} {self.pending_style.render(stage.title)}"

                lines.append(truncate_ansi(stage_line, self.width))

        # 4. Footer controls
        if not self.is_running and not self.is_finished:
            lines.append("")
            lines.append(self.dim_style.render("Press Enter to run pipeline • s to step"))
        elif self.is_failed:
            lines.append("")
            lines.append(self.dim_style.render("Press Enter to retry pipeline"))

        return "\n".join(lines)

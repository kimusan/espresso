"""Unit tests for PipelineProgress component."""

from __future__ import annotations

import unittest

from espresso.beans.pipeline_progress import (
    PipelineCompleteMsg,
    PipelineProgress,
    PipelineStage,
    StageCompleteMsg,
    StageFailedMsg,
    StageStartMsg,
    StageStatus,
)
from espresso.core.keys import KeyMsg
from espresso.crema import strip_ansi


class TestPipelineProgress(unittest.TestCase):
    def test_initial_state(self) -> None:
        pipe = PipelineProgress(
            stages=[
                ("Task 1", lambda: "ok"),
                ("Task 2", lambda: "ok"),
            ],
            title="Build",
        )
        self.assertEqual(len(pipe.stages), 2)
        self.assertEqual(pipe.progress, 0.0)
        self.assertFalse(pipe.is_running)
        self.assertFalse(pipe.is_finished)
        view = strip_ansi(pipe.view())
        self.assertIn("Build", view)
        self.assertIn("[READY]", view)
        self.assertIn("○ Task 1", view)
        self.assertIn("○ Task 2", view)

    def test_pipeline_execution_success(self) -> None:
        side_effects = []
        pipe = PipelineProgress(
            stages=[
                PipelineStage(title="Step 1", action=lambda: side_effects.append(1)),
                PipelineStage(title="Step 2", action=lambda: side_effects.append(2)),
            ]
        )

        # Start pipeline
        pipe, cmd1 = pipe.start()
        self.assertTrue(pipe.is_running)
        self.assertIsNotNone(cmd1)
        msg1 = cmd1()
        self.assertIsInstance(msg1, StageStartMsg)
        self.assertEqual(msg1.stage_index, 0)

        # Process StageStartMsg(0) -> runs action and returns StageCompleteMsg
        pipe, cmd_run1 = pipe.update(msg1)
        self.assertIsNotNone(cmd_run1)
        res1 = cmd_run1()
        self.assertIsInstance(res1, StageCompleteMsg)
        self.assertEqual(res1.stage_index, 0)
        self.assertIn(1, side_effects)

        # Process StageCompleteMsg(0) -> advances to stage 1
        pipe, cmd2 = pipe.update(res1)
        self.assertEqual(pipe.stages[0].status, StageStatus.SUCCESS)
        self.assertEqual(pipe.progress, 0.5)
        self.assertIsNotNone(cmd2)
        msg2 = cmd2()
        self.assertIsInstance(msg2, StageStartMsg)
        self.assertEqual(msg2.stage_index, 1)

        # Run stage 1
        pipe, cmd_run2 = pipe.update(msg2)
        res2 = cmd_run2()
        self.assertIsInstance(res2, StageCompleteMsg)
        self.assertIn(2, side_effects)

        # Process StageCompleteMsg(1) -> pipeline finished
        pipe, cmd_done = pipe.update(res2)
        self.assertEqual(pipe.progress, 1.0)
        self.assertTrue(pipe.is_finished)
        self.assertFalse(pipe.is_running)
        self.assertIsNotNone(cmd_done)
        done_msg = cmd_done()
        self.assertIsInstance(done_msg, PipelineCompleteMsg)
        self.assertTrue(done_msg.success)

        view = strip_ansi(pipe.view())
        self.assertIn("[COMPLETED]", view)
        self.assertIn("✔ Step 1", view)
        self.assertIn("✔ Step 2", view)

    def test_pipeline_execution_failure(self) -> None:
        def failing_action():
            raise ValueError("Network connection refused")

        pipe = PipelineProgress(
            stages=[
                ("Compile", lambda: True),
                ("Deploy", failing_action),
            ]
        )

        pipe, cmd = pipe.start()
        msg_start = cmd()
        pipe, cmd_run = pipe.update(msg_start)
        msg_comp = cmd_run()
        pipe, cmd_next = pipe.update(msg_comp)

        # Stage 1 starts
        msg_start2 = cmd_next()
        self.assertEqual(msg_start2.stage_index, 1)

        # Stage 1 runs and fails
        pipe, cmd_run2 = pipe.update(msg_start2)
        msg_fail = cmd_run2()
        self.assertIsInstance(msg_fail, StageFailedMsg)
        self.assertEqual(msg_fail.stage_index, 1)
        self.assertIn("Network connection refused", msg_fail.error)

        # Process failure
        pipe, cmd_done = pipe.update(msg_fail)
        self.assertTrue(pipe.is_failed)
        self.assertTrue(pipe.is_finished)
        self.assertFalse(pipe.is_running)
        done_msg = cmd_done()
        self.assertIsInstance(done_msg, PipelineCompleteMsg)
        self.assertFalse(done_msg.success)

        view = strip_ansi(pipe.view())
        self.assertIn("[FAILED]", view)
        self.assertIn("✖ Deploy", view)
        self.assertIn("Network connection refused", view)

    def test_key_controls(self) -> None:
        pipe = PipelineProgress(stages=[("Task", lambda: 42)])
        self.assertFalse(pipe.is_running)

        # Enter triggers start
        pipe, cmd = pipe.update(KeyMsg("enter"))
        self.assertTrue(pipe.is_running)
        self.assertIsNotNone(cmd)

        # Esc cancels
        pipe, _ = pipe.update(KeyMsg("esc"))
        self.assertFalse(pipe.is_running)
        self.assertTrue(pipe.is_failed)


if __name__ == "__main__":
    unittest.main()

"""Integration tests for Program runtime event loop."""

from __future__ import annotations

import io
import unittest

from espresso import Cmd, KeyMsg, Model, Msg, Program, QuitMsg, quit_app


class StepModel:
    def __init__(self) -> None:
        self.step = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case KeyMsg(key="n"):
                self.step += 1
                return self, None
            case KeyMsg(key="q"):
                return self, quit_app
        return self, None

    def view(self) -> str:
        return f"Step: {self.step}"


class TestProgramRuntime(unittest.TestCase):
    def test_program_runs_and_quits_cleanly(self) -> None:
        out = io.StringIO()
        p = Program(StepModel(), input_stream=io.StringIO(""), output_stream=out)

        # Directly send messages to the program queue
        async def run_test() -> Model:
            import asyncio

            async def send_events() -> None:
                while p._queue is None:
                    await asyncio.sleep(0.005)
                await p._queue.put(KeyMsg("n"))
                await p._queue.put(KeyMsg("n"))
                await p._queue.put(KeyMsg("q"))

            asyncio.create_task(send_events())
            return await p.run_async()

        import asyncio

        final_model = asyncio.run(run_test())
        self.assertEqual(final_model.step, 2)
        output = out.getvalue()
        self.assertIn("Step: 0", output)
        self.assertIn("Step: 2", output)

    def test_program_quits_with_quit_app_call(self) -> None:
        """Test returning quit_app() with parentheses terminates loop."""
        class QuitCallModel:
            def init(self) -> Cmd | None:
                return None
            def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
                if isinstance(msg, KeyMsg) and msg.key == "q":
                    return self, quit_app()
                return self, None
            def view(self) -> str:
                return "running"

        import asyncio

        out = io.StringIO()
        p = Program(QuitCallModel(), input_stream=io.StringIO(""), output_stream=out)

        async def run_test() -> Model:
            async def send_q() -> None:
                while p._queue is None:
                    await asyncio.sleep(0.005)
                await p._queue.put(KeyMsg("q"))

            asyncio.create_task(send_q())
            return await p.run_async()

        final_model = asyncio.run(run_test())
        self.assertIsNotNone(final_model)

    def test_program_quits_on_unhandled_ctrl_c(self) -> None:
        """Test pressing Ctrl+C when unhandled by model cleanly exits."""
        class NoExitModel:
            def init(self) -> Cmd | None:
                return None
            def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
                return self, None
            def view(self) -> str:
                return "stuck"

        import asyncio

        out = io.StringIO()
        p = Program(NoExitModel(), input_stream=io.StringIO(""), output_stream=out)

        async def run_test() -> Model:
            async def send_ctrl_c() -> None:
                while p._queue is None:
                    await asyncio.sleep(0.005)
                await p._queue.put(KeyMsg("ctrl+c"))

            asyncio.create_task(send_ctrl_c())
            return await p.run_async()

        final_model = asyncio.run(run_test())
        self.assertIsNotNone(final_model)


if __name__ == "__main__":
    unittest.main()

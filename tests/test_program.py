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
        p = Program(StepModel(), output_stream=out)

        # Directly send messages to the program queue
        async def run_test() -> Model:
            import asyncio

            async def send_events() -> None:
                await asyncio.sleep(0.02)
                if p._queue is not None:
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


if __name__ == "__main__":
    unittest.main()

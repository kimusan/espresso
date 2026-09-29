"""Unit tests for TEA protocols, commands, and messages."""

from __future__ import annotations

import asyncio
import unittest
from dataclasses import dataclass

from espresso import Cmd, Model, Msg, QuitMsg, batch, quit_app, sequence, tick


@dataclass(frozen=True)
class CustomMsg(Msg):
    value: int


class CounterModel:
    def __init__(self, count: int = 0) -> None:
        self.count = count

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        if isinstance(msg, CustomMsg):
            return CounterModel(self.count + msg.value), None
        return self, None

    def view(self) -> str:
        return f"Count: {self.count}"


class TestTeaCore(unittest.TestCase):
    def test_model_protocol_compliance(self) -> None:
        m = CounterModel()
        self.assertIsInstance(m, Model)

    def test_deterministic_state_transitions(self) -> None:
        m = CounterModel(0)
        m2, cmd = m.update(CustomMsg(5))
        self.assertIsNone(cmd)
        self.assertEqual(m2.count, 5)
        self.assertEqual(m.count, 0)  # Original unchanged

        m3, _ = m2.update(CustomMsg(-2))
        self.assertEqual(m3.count, 3)

    def test_quit_app_cmd(self) -> None:
        msg = quit_app()
        self.assertIsInstance(msg, QuitMsg)

    def test_batch_execution(self) -> None:
        def sync_cmd1() -> Msg:
            return CustomMsg(10)

        async def async_cmd2() -> Msg:
            await asyncio.sleep(0.01)
            return CustomMsg(20)

        b = batch(sync_cmd1, async_cmd2)

        async def run_batch() -> Msg:
            return await b()

        res = asyncio.run(run_batch())
        self.assertIsNotNone(res)
        # Should return a BatchMsg containing both results
        self.assertEqual(len(res.messages), 2)
        values = {m.value for m in res.messages if isinstance(m, CustomMsg)}
        self.assertEqual(values, {10, 20})

    def test_sequence_execution(self) -> None:
        events = []

        def cmd1() -> Msg:
            events.append(1)
            return CustomMsg(1)

        def cmd2() -> Msg:
            events.append(2)
            return CustomMsg(2)

        seq = sequence(cmd1, cmd2)

        async def run_seq() -> Msg:
            return await seq()

        res = asyncio.run(run_seq())
        self.assertEqual(events, [1, 2])
        self.assertEqual(len(res.messages), 2)

    def test_tick_execution(self) -> None:
        t = tick(0.01, lambda: CustomMsg(99))

        async def run_tick() -> Msg:
            return await t()

        res = asyncio.run(run_tick())
        self.assertIsInstance(res, CustomMsg)
        self.assertEqual(res.value, 99)


if __name__ == "__main__":
    unittest.main()

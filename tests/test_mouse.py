"""Unit tests for mouse event decoding."""

from __future__ import annotations

import unittest

from espresso import MouseAction, MouseButton, MouseMsg
from espresso.core.keys import parse_keys
from espresso.core.mouse import parse_sgr_mouse


class TestMouseParser(unittest.TestCase):
    def test_parse_left_click_press(self) -> None:
        # \x1b[<0;15;8M -> Left click press at col 15, row 8 (1-indexed) -> (14, 7)
        msg, consumed = parse_sgr_mouse("\x1b[<0;15;8M")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.button, MouseButton.LEFT)
        self.assertEqual(msg.action, MouseAction.PRESS)
        self.assertEqual(msg.x, 14)
        self.assertEqual(msg.y, 7)
        self.assertEqual(consumed, len("\x1b[<0;15;8M"))

    def test_parse_left_click_release(self) -> None:
        # \x1b[<0;15;8m -> Release
        msg, consumed = parse_sgr_mouse("\x1b[<0;15;8m")
        self.assertIsNotNone(msg)
        self.assertEqual(msg.button, MouseButton.LEFT)
        self.assertEqual(msg.action, MouseAction.RELEASE)

    def test_parse_wheel_events(self) -> None:
        # Wheel up: 64
        msg_up, _ = parse_sgr_mouse("\x1b[<64;10;5M")
        self.assertIsNotNone(msg_up)
        self.assertEqual(msg_up.button, MouseButton.WHEEL_UP)

        # Wheel down: 65
        msg_down, _ = parse_sgr_mouse("\x1b[<65;10;5M")
        self.assertIsNotNone(msg_down)
        self.assertEqual(msg_down.button, MouseButton.WHEEL_DOWN)

    def test_parse_keys_stream_with_mouse(self) -> None:
        raw_stream = "a\x1b[<0;10;10Mq"
        events = list(parse_keys(raw_stream))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0], "a")
        self.assertIsInstance(events[1], MouseMsg)
        self.assertEqual(events[1].button, MouseButton.LEFT)
        self.assertEqual(events[2], "q")

    def test_translate_and_relative_to(self) -> None:
        msg = MouseMsg(x=25, y=10, button=MouseButton.LEFT, action=MouseAction.PRESS)
        translated = msg.translate(-5, 2)
        self.assertEqual(translated.x, 20)
        self.assertEqual(translated.y, 12)
        self.assertEqual(translated.button, MouseButton.LEFT)

        rel = msg.relative_to(5, 3)
        self.assertEqual(rel.x, 20)
        self.assertEqual(rel.y, 7)


class TestMouseToggle(unittest.TestCase):
    def test_program_fluent_and_direct_mouse_controls(self) -> None:
        from espresso import Model, Program
        from io import StringIO

        class DummyModel(Model):
            def init(self):
                return None
            def update(self, msg):
                return self, None
            def view(self):
                return "hello"

        prog = Program(DummyModel(), input_stream=StringIO(""), output_stream=StringIO())
        self.assertFalse(prog.mouse)

        prog.with_mouse(True)
        self.assertTrue(prog.mouse)

        prog.disable_mouse()
        self.assertFalse(prog.mouse)

        prog.enable_mouse()
        self.assertTrue(prog.mouse)

        res = prog.toggle_mouse()
        self.assertFalse(res)
        self.assertFalse(prog.mouse)

        res2 = prog.toggle_mouse()
        self.assertTrue(res2)
        self.assertTrue(prog.mouse)

    def test_terminal_driver_mouse_toggle(self) -> None:
        from espresso.core.terminal import TerminalDriver

        driver = TerminalDriver(mouse=False)
        self.assertFalse(driver.mouse)

        driver.enable_mouse()
        self.assertTrue(driver.mouse)

        driver.disable_mouse()
        self.assertFalse(driver.mouse)

    def test_tea_mouse_commands(self) -> None:
        from espresso import DisableMouseMsg, EnableMouseMsg, disable_mouse, enable_mouse

        cmd_enable = enable_mouse()
        self.assertIsInstance(cmd_enable, EnableMouseMsg)
        # Verify callable as Cmd
        self.assertIs(cmd_enable(), cmd_enable)

        cmd_disable = disable_mouse()
        self.assertIsInstance(cmd_disable, DisableMouseMsg)
        self.assertIs(cmd_disable(), cmd_disable)

    def test_program_runtime_mouse_toggle(self) -> None:
        import asyncio
        from espresso import Cmd, DisableMouseMsg, EnableMouseMsg, KeyMsg, Model, Msg, Program, quit_app
        from io import StringIO

        class MouseTogglingModel(Model):
            def __init__(self) -> None:
                self.clicks = 0
                self.mouse_on = False

            def init(self) -> Cmd | None:
                return None

            def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
                if isinstance(msg, KeyMsg):
                    if msg.key == "e":
                        self.mouse_on = True
                        from espresso import enable_mouse
                        return self, enable_mouse()
                    elif msg.key == "d":
                        self.mouse_on = False
                        from espresso import disable_mouse
                        return self, disable_mouse()
                    elif msg.key == "q":
                        return self, quit_app
                elif isinstance(msg, MouseMsg):
                    self.clicks += 1
                return self, None

            def view(self) -> str:
                return f"clicks: {self.clicks}, on: {self.mouse_on}"

        model = MouseTogglingModel()
        out = StringIO()
        prog = Program(model, input_stream=StringIO(""), output_stream=out)

        async def run_scenario():
            # Initial state
            self.assertFalse(prog.mouse)

            # Send Key 'e' -> enables mouse via TEA command
            await prog._handle_msg(KeyMsg("e"))
            self.assertTrue(prog.mouse)

            # Send Mouse click when mouse enabled -> should be processed
            click_msg = MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS)
            await prog._handle_msg(click_msg)
            self.assertEqual(prog.model.clicks, 1)

            # Send Key 'd' -> disables mouse via TEA command
            await prog._handle_msg(KeyMsg("d"))
            self.assertFalse(prog.mouse)

            # Send Mouse click when mouse disabled -> ignored by runtime
            await prog._handle_msg(click_msg)
            self.assertEqual(prog.model.clicks, 1)  # Unchanged!

        asyncio.run(run_scenario())


class TestGalleryMouseRowMapping(unittest.TestCase):
    def test_row_coordinate_mappings(self) -> None:
        import importlib.util
        import sys
        from pathlib import Path

        repo_root = Path(__file__).resolve().parent.parent
        spec = importlib.util.spec_from_file_location("gallery", repo_root / "examples" / "10_component_gallery.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        app = mod.ComponentGallery()

        # 1. FilePicker (Tab 1): Row 4 is Entry 0 ('..'), Row 5 is Entry 1
        app.tabs.active_tab = 1
        app.file_picker.cursor = 4
        app, _ = app.update(MouseMsg(x=10, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.file_picker.cursor, 0)
        self.assertEqual(app.file_picker.selected_entry.name, "..")

        app, _ = app.update(MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.file_picker.cursor, 1)

        # 2. Tree View (Tab 3): Row 2 is Node 0, Row 3 is Node 1
        app.tabs.active_tab = 3
        app.tree.cursor = 4
        app, _ = app.update(MouseMsg(x=10, y=2, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.tree.cursor, 0)
        self.assertEqual(app.tree.selected_node.label, "espresso")

        app, _ = app.update(MouseMsg(x=10, y=3, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.tree.cursor, 1)

        # 3. List (Tab 0): Row 4 is Item 0 title, Row 5 is Item 0 desc, Row 6 is Item 1
        app.tabs.active_tab = 0
        app.list.cursor = 4
        app, _ = app.update(MouseMsg(x=10, y=4, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.list.cursor, 0)
        app.list.cursor = 4
        app, _ = app.update(MouseMsg(x=10, y=5, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.list.cursor, 0)
        app, _ = app.update(MouseMsg(x=10, y=6, button=MouseButton.LEFT, action=MouseAction.PRESS))
        self.assertEqual(app.list.cursor, 1)


if __name__ == "__main__":
    unittest.main()


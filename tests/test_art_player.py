"""Unit tests for ArtPlayer bean and .3a / .ans animation parsers."""

from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from espresso.beans.art_player import (
    AnimationDoneMsg,
    AnimationLoopMsg,
    ArtAnimation,
    ArtFrame,
    ArtPlayer,
    ArtPlayerTickMsg,
    parse_3a,
    parse_ans,
)
from espresso.core.keys import Key, KeyMsg
from espresso.crema.border import DOUBLE_BORDER, ROUNDED_BORDER
from espresso.crema.width import string_width, strip_ansi


class TestArtPlayer(unittest.TestCase):
    def test_parse_3a_basic(self) -> None:
        raw_3a = """@3a
title: Spinning Baton
author: PixelMaster
orig-author: RetroSmith
tags: spinner, retro, loader
delay: 60, 0:120
loop: yes
colors: no
@body
 |
-+-
 |

 /
-+-
 /

 -
-+-
 -
"""
        anim = parse_3a(raw_3a)
        self.assertEqual(anim.title, "Spinning Baton")
        self.assertEqual(anim.author, "PixelMaster")
        self.assertEqual(anim.orig_author, "RetroSmith")
        self.assertIn("spinner", anim.tags)
        self.assertIn("loader", anim.tags)
        self.assertTrue(anim.loop)
        self.assertEqual(anim.total_frames, 3)

        # Delays
        self.assertEqual(anim.frames[0].duration_ms, 120)
        self.assertEqual(anim.frames[1].duration_ms, 60)
        self.assertEqual(anim.frames[2].duration_ms, 60)

        # Frame lines
        self.assertEqual(anim.frames[0].lines, [" |", "-+-", " |"])

    def test_parse_3a_colors_and_custom_col(self) -> None:
        raw_3a = """@3a
title: Colored Diamond
delay: 80
loop: no
colors: yes
col * fg:9 bg:0
col # fg:196
col @ fg:#ff5500
col _ fg:_
@body
 *   _*_
*#* _*#*_
 *   _*_

 @   _@_
@#@ _@#@_
 @   _@_
"""
        anim = parse_3a(raw_3a)
        self.assertEqual(anim.title, "Colored Diamond")
        self.assertFalse(anim.loop)
        self.assertEqual(anim.total_frames, 2)

        # Verify ANSI codes in frame lines
        f0 = anim.frames[0]
        # Frame 0 line 1 has * with bright red (91) and black bg (40)
        line0 = f0.lines[0]
        self.assertIn("\x1b[91;40m", line0)
        self.assertIn("*", line0)

        # Line 1 has # with 256-color (38;5;196)
        line1 = f0.lines[1]
        self.assertIn("\x1b[38;5;196m", line1)

        # Frame 1 has @ with 24-bit TrueColor (38;2;255;85;0)
        f1 = anim.frames[1]
        self.assertIn("\x1b[38;2;255;85;0m", f1.lines[0])

    def test_parse_3a_color_pin(self) -> None:
        raw_3a = """@3a
title: Color Pin Test
delay: 50
@color-pin
123
456
@body
ABC
DEF

GHI
JKL
"""
        anim = parse_3a(raw_3a)
        self.assertEqual(anim.total_frames, 2)
        # In frame 0, line 0 has A with color 1 (red: \x1b[31m), B with 2 (\x1b[32m), C with 3 (\x1b[33m)
        f0_line0 = anim.frames[0].lines[0]
        self.assertIn("\x1b[31m", f0_line0)
        self.assertIn("A", f0_line0)
        self.assertIn("B", f0_line0)
        self.assertIn("C", f0_line0)

        # Frame 1 also uses the color pin
        f1_line0 = anim.frames[1].lines[0]
        self.assertIn("\x1b[31m", f1_line0)
        self.assertIn("G", f1_line0)

    def test_parse_3a_text_pin(self) -> None:
        raw_3a = """@3a
title: Text Pin Test
delay: 50
@text-pin
HELLO
WORLD
@body
11111
22222

33333
44444
"""
        anim = parse_3a(raw_3a)
        self.assertEqual(anim.total_frames, 2)
        # Frame 0 line 0 is HELLO colored with 1 (red: \x1b[31m)
        f0_line0 = anim.frames[0].lines[0]
        self.assertIn("\x1b[31m", f0_line0)
        self.assertIn("HELLO", f0_line0)

        # Frame 1 line 0 is HELLO colored with 3 (yellow: \x1b[33m)
        f1_line0 = anim.frames[1].lines[0]
        self.assertIn("\x1b[33m", f1_line0)
        self.assertIn("HELLO", f1_line0)

    def test_parse_3a_comments(self) -> None:
        raw_3a = """@3a
;; Full line comment
title: Commented Animation ;; inline comment
delay: 75 ;; milliseconds
loop: no
@body
;; Comments inside body
Hello
World
"""
        anim = parse_3a(raw_3a)
        self.assertEqual(anim.title, "Commented Animation")
        self.assertEqual(anim.default_delay_ms, 75)
        self.assertFalse(anim.loop)
        self.assertEqual(anim.frames[0].lines, ["Hello", "World"])

    def test_parse_ans_plain_and_cp437(self) -> None:
        # CP437 box drawing and shade blocks: 0xdb=█, 0xdf=▀, 0xdc=▄, 0xb0=░
        raw_bytes = b"\x1b[32m\xdb\xdf\xdc\xb0\x1b[0m\r\n\x1b[34m\xc4\xc4\xc4\x1b[0m"
        anim = parse_ans(raw_bytes, default_delay_ms=40)
        self.assertEqual(anim.total_frames, 1)
        lines = anim.frames[0].lines
        self.assertEqual(len(lines), 2)
        self.assertEqual(strip_ansi(lines[0]), "█▀▄░")
        self.assertEqual(strip_ansi(lines[1]), "───")
        self.assertIn("\x1b[32m", lines[0])

    def test_parse_ans_sauce_metadata(self) -> None:
        raw_ans = b"\x1b[36mTest Art\x1b[0m\r\n"
        # Construct 128-byte SAUCE
        sauce = (
            b"SAUCE00"
            + b"Neon Horizon".ljust(35)
            + b"AcidBurn".ljust(20)
            + b"BBS Elite".ljust(20)
            + b"20261009"
            + struct.pack("<I", len(raw_ans))
            + b"\x01\x01"
            + struct.pack("<H", 80)
            + struct.pack("<H", 25)
            + struct.pack("<H", 0)
            + struct.pack("<H", 0)
            + b"\x00\x00"
            + b"\x00" * 22
        )
        self.assertEqual(len(sauce), 128)
        data = raw_ans + sauce

        anim = parse_ans(data)
        self.assertEqual(anim.title, "Neon Horizon")
        self.assertEqual(anim.author, "AcidBurn")
        self.assertEqual(anim.orig_author, "BBS Elite")
        self.assertEqual(strip_ansi(anim.frames[0].lines[0]), "Test Art")

    def test_parse_ans_animation_multiframe(self) -> None:
        # Multi-frame ANSImation separated by \x1b[2J
        raw_anim = (
            "Frame 1: █\x1b[0m\r\n"
            "\x1b[2J\x1b[H"
            "Frame 2: ▀\x1b[0m\r\n"
            "\x1b[2J\x1b[H"
            "Frame 3: ▄\x1b[0m"
        )
        anim = parse_ans(raw_anim, default_delay_ms=50)
        self.assertEqual(anim.total_frames, 3)
        self.assertEqual(strip_ansi(anim.frames[0].lines[0]), "Frame 1: █")
        self.assertEqual(strip_ansi(anim.frames[1].lines[0]), "Frame 2: ▀")
        self.assertEqual(strip_ansi(anim.frames[2].lines[0]), "Frame 3: ▄")
        self.assertTrue(anim.loop)

    def test_parse_ans_progressive(self) -> None:
        raw_ans = "Line 1\r\nLine 2\r\nLine 3\r\nLine 4"
        anim = parse_ans(raw_ans, default_delay_ms=25, progressive_lines=True, lines_per_frame=1)
        self.assertEqual(anim.total_frames, 4)
        self.assertEqual(len(anim.frames[0].lines), 1)
        self.assertEqual(len(anim.frames[1].lines), 2)
        self.assertEqual(len(anim.frames[2].lines), 3)
        self.assertEqual(len(anim.frames[3].lines), 4)
        self.assertFalse(anim.loop)

    def test_art_player_lifecycle_and_loop(self) -> None:
        frames = [
            ArtFrame(lines=["Frame 0"], duration_ms=50),
            ArtFrame(lines=["Frame 1"], duration_ms=50),
        ]
        anim = ArtAnimation(frames=frames, loop=True, title="Looping Test")
        player = ArtPlayer(animation=anim, auto_play=True)

        # Initial state
        self.assertEqual(player.current_frame_idx, 0)
        self.assertTrue(player.is_playing)

        # Advance to frame 1
        player, cmd = player.update(ArtPlayerTickMsg(tag=player.tag, frame_index=1))
        self.assertEqual(player.current_frame_idx, 1)
        self.assertIsNotNone(cmd)

        # Advance past end -> should wrap around to 0
        player, cmd = player.update(ArtPlayerTickMsg(tag=player.tag, frame_index=2))
        self.assertEqual(player.current_frame_idx, 0)
        self.assertEqual(player.loop_count, 1)
        self.assertTrue(player.is_playing)

    def test_art_player_non_loop_done_message(self) -> None:
        frames = [
            ArtFrame(lines=["Splash 1"], duration_ms=50),
            ArtFrame(lines=["Splash 2"], duration_ms=50),
        ]
        anim = ArtAnimation(frames=frames, loop=False, title="Splash Screen")
        player = ArtPlayer(animation=anim, auto_play=True)

        # Advance to frame 1
        player, _ = player.update(ArtPlayerTickMsg(tag=player.tag, frame_index=1))
        self.assertEqual(player.current_frame_idx, 1)

        # Advance past end -> should stop and produce AnimationDoneMsg
        player, cmd = player.update(ArtPlayerTickMsg(tag=player.tag, frame_index=2))
        self.assertEqual(player.current_frame_idx, 1)
        self.assertFalse(player.is_playing)
        self.assertTrue(player.is_finished)

        # Verify command produced AnimationDoneMsg
        self.assertIsNotNone(cmd)
        done_msg = cmd()
        self.assertIsInstance(done_msg, AnimationDoneMsg)
        self.assertEqual(done_msg.title, "Splash Screen")

    def test_art_player_controls(self) -> None:
        frames = [
            ArtFrame(lines=["F0"]),
            ArtFrame(lines=["F1"]),
            ArtFrame(lines=["F2"]),
        ]
        anim = ArtAnimation(frames=frames, loop=True)
        player = ArtPlayer(animation=anim, auto_play=False)

        self.assertFalse(player.is_playing)
        player.play()
        self.assertTrue(player.is_playing)
        player.pause()
        self.assertFalse(player.is_playing)

        # Step forward & backward
        player.seek(0)
        player.step_forward()
        self.assertEqual(player.current_frame_idx, 1)
        player.step_backward()
        self.assertEqual(player.current_frame_idx, 0)

        # Restart
        player.seek(2)
        player.restart()
        self.assertEqual(player.current_frame_idx, 0)
        self.assertTrue(player.is_playing)

        # Speed adjustment
        player.set_speed(1.5)
        self.assertEqual(player.speed, 1.5)

    def test_art_player_keyboard_events(self) -> None:
        frames = [ArtFrame(lines=["A"]), ArtFrame(lines=["B"]), ArtFrame(lines=["C"])]
        player = ArtPlayer(animation=ArtAnimation(frames=frames), auto_play=False)

        # Space toggles play
        player, cmd = player.update(KeyMsg(Key(name=" ", char=" ")))
        self.assertTrue(player.is_playing)

        # Space toggles pause
        player, cmd = player.update(KeyMsg(Key(name=" ", char=" ")))
        self.assertFalse(player.is_playing)

        # Right key steps forward
        player, _ = player.update(KeyMsg(Key("right")))
        self.assertEqual(player.current_frame_idx, 1)

        # Left key steps backward
        player, _ = player.update(KeyMsg(Key("left")))
        self.assertEqual(player.current_frame_idx, 0)

        # Plus / Bracket speeds up
        initial_speed = player.speed
        player, _ = player.update(KeyMsg(Key(name="]", char="]")))
        self.assertEqual(player.speed, initial_speed + 0.25)

    def test_art_player_view_and_framing(self) -> None:
        frames = [ArtFrame(lines=["Hello World", "Line 2"])]
        anim = ArtAnimation(frames=frames, title="My Art")
        player = ArtPlayer(
            animation=anim,
            border=ROUNDED_BORDER,
            border_fg="#FF007F",
            show_title=True,
            show_controls=True,
            center_horizontally=True,
        )

        view_out = player.view()
        # Should include border characters and title
        self.assertIn("╭", view_out)
        self.assertIn("My Art", view_out)
        self.assertIn("Hello World", view_out)
        self.assertIn("Line 2", view_out)
        self.assertIn("Play/Pause", view_out)

    def test_art_player_from_frames_factory(self) -> None:
        player = ArtPlayer.from_frames(
            ["Frame 1\nRow 2", "Frame 2\nRow 2"],
            default_delay_ms=60,
        )
        self.assertEqual(player.total_frames, 2)
        self.assertEqual(player.animation.frames[0].lines, ["Frame 1", "Row 2"])
        self.assertEqual(player.animation.frames[0].duration_ms, 60)

    def test_art_player_from_file(self) -> None:
        raw_3a = "@3a\ntitle: File Test\nloop: yes\n@body\nHello\n\nWorld\n"
        with tempfile.NamedTemporaryFile("w+", suffix=".3a", delete=False) as tf:
            tf.write(raw_3a)
            tf_path = tf.name

        try:
            player = ArtPlayer.from_file(tf_path)
            self.assertEqual(player.animation.title, "File Test")
            self.assertEqual(player.total_frames, 2)
        finally:
            Path(tf_path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

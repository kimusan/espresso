#!/usr/bin/env python3
"""Example 16: Terminal Art & Animation Player (.3a & .ans).

Demonstrates:
1. ArtPlayer bean playing modern .3a Animated ASCII Art (with @3a header,
   colors, frame delays, and looping).
2. ArtPlayer bean rendering classic BBS ANSI Art (.ans) with CP437 box
   characters, vibrant 16-color ANSI gradients, and SAUCE metadata extraction.
3. Progressive BBS Modem Reveal: line-by-line reveal simulating retro 14.4k
   modem download, emitting AnimationDoneMsg on completion.
4. Celebratory Confetti emission triggered by AnimationDoneMsg!
5. Interactive playback controls:
   - Space: Toggle Play/Pause
   - R: Restart from frame 0
   - Left/Right: Step frames backward / forward
   - +/- or [/]: Increase / decrease playback speed
   - B: Cycle border styles (Rounded, Double, Normal, Thick, Block)
   - 1/2/3 or Tab: Switch animation
   - Q: Quit
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import Cmd, KeyMsg, Model, Msg, Program, batch, quit_app
from espresso.beans import (
    AnimationDoneMsg,
    AnimationLoopMsg,
    ArtAnimation,
    ArtFrame,
    ArtPlayer,
    ArtPlayerTickMsg,
    Confetti,
    ConfettiMode,
    ConfettiTickMsg,
    Tabs,
    TabChangeMsg,
    parse_3a,
    parse_ans,
)
from espresso.crema import (
    BLOCK_BORDER,
    DOUBLE_BORDER,
    NORMAL_BORDER,
    ROUNDED_BORDER,
    THICK_BORDER,
    Align,
    Border,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
    strip_ansi,
)

# --- Sample 1: Animated .3a Espresso Cup ---
ESPRESSO_3A = """@3a
title: Steaming Espresso Cup
author: Espresso Studio
delay: 90
loop: yes
colors: yes
col ~ fg:7
col * fg:e
col # fg:b
col = fg:3
col @ fg:1
col _ fg:_
@body
       )  (       ~~~~_~~~~
      (   )      ~~~~_~~~~
       ) (       ~~~~_~~~~
     .------.    ===========
    (  ☕   )__  ==***==####
     `------'  ) ===========
      `------'   ===========

       (  )       ~~~~_~~~~
        ) (       ~~~~_~~~~
       (   )      ~~~~_~~~~
     .------.    ===========
    (  ☕   )__  ==***==####
     `------'  ) ===========
      `------'   ===========

        ) (       ~~~~_~~~~
       (   )      ~~~~_~~~~
        )  (      ~~~~_~~~~
     .------.    ===========
    (  ☕   )__  ==***==####
     `------'  ) ===========
      `------'   ===========

       (   )      ~~~~_~~~~
        ) (       ~~~~_~~~~
       (  )       ~~~~_~~~~
     .------.    ===========
    (  ☕   )__  ==***==####
     `------'  ) ===========
      `------'   ===========
"""

# --- Sample 2: Multi-frame Classic BBS ANSImation with CP437 Characters & ANSI Colors ---
def _generate_bbs_ansimation() -> str:
    """Generate an 8-frame classic BBS ANSImation with CP437 blocks and shifting raster bars."""
    palettes = [
        ("\x1b[36m", "\x1b[96m", "\x1b[94m", "\x1b[95m", "\x1b[35m"),
        ("\x1b[96m", "\x1b[94m", "\x1b[95m", "\x1b[35m", "\x1b[31m"),
        ("\x1b[94m", "\x1b[95m", "\x1b[35m", "\x1b[31m", "\x1b[33m"),
        ("\x1b[95m", "\x1b[35m", "\x1b[31m", "\x1b[33m", "\x1b[92m"),
        ("\x1b[35m", "\x1b[31m", "\x1b[33m", "\x1b[92m", "\x1b[36m"),
        ("\x1b[31m", "\x1b[33m", "\x1b[92m", "\x1b[36m", "\x1b[96m"),
        ("\x1b[33m", "\x1b[92m", "\x1b[96m", "\x1b[94m", "\x1b[95m"),
        ("\x1b[92m", "\x1b[36m", "\x1b[96m", "\x1b[94m", "\x1b[35m"),
    ]
    scanner_pos = [0, 6, 14, 22, 28, 22, 14, 6]
    signals = ["[●○○○]", "[○●○○]", "[○○●○]", "[○○○●]", "[○○●○]", "[○●○○]", "[●○○○]", "[○●○○]"]
    leds = [
        "RX: ●  TX: ○",
        "RX: ○  TX: ●",
        "RX: ●  TX: ●",
        "RX: ○  TX: ○",
        "RX: ●  TX: ○",
        "RX: ○  TX: ●",
        "RX: ●  TX: ●",
        "RX: ○  TX: ○",
    ]

    frames: list[str] = []
    for i in range(8):
        c1, c2, c3, c4, c5 = palettes[i]
        pos = scanner_pos[i]
        sig = signals[i]
        led = leds[i]

        scan = (" " * pos + "░░▒▒▓▓████▓▓▒▒░░").ljust(53)
        frame = (
            f"{c1}    ▄█████████▄   ▄████████    ▄████████    ▄████████ \x1b[0m\n"
            f"{c2}    ███     ███  ███    ███   ███    ███   ███    ███ \x1b[0m\n"
            f"{c3}    ███     ███  ███    █▀    ███    █▀    ███    █▀  \x1b[0m\n"
            f"{c4}    ███     ███ ▄███▄▄▄      ▄███▄▄▄      ▄███▄▄▄     \x1b[0m\n"
            f"{c5}  ▀█████████▀  ▀▀███▀▀▀     ▀▀███▀▀▀     ▀▀███▀▀▀     \x1b[0m\n"
            "\x1b[90m  ─────────────────────────────────────────────────────\x1b[0m\n"
            "\x1b[93m  ★  E S P R E S S O   B B S   S Y S T E M   2 0 2 6  ★\x1b[0m\n"
            "\x1b[90m  ─────────────────────────────────────────────────────\x1b[0m\n"
            f"\x1b[32m  [Node 01]  Online: 28,800 Baud  {sig}  {led}\x1b[0m\n"
            "\x1b[33m  SysOp: AcidBurn  •  Conference: #demoscene-retro    \x1b[0m\n"
            f"\x1b[36m  {scan}\x1b[0m"
        )
        frames.append(frame)

    return "\x1b[2J\x1b[H".join(frames)


BBS_ANIMATION_TEXT = _generate_bbs_ansimation()

# --- Sample 3: BBS Splash Screen Logo for Progressive Reveal ---
SPLASH_SCREEN_TEXT = (
    "\x1b[33m           ╔════════════════════════════════════════════╗\x1b[0m\n"
    "\x1b[33m           ║\x1b[35m       WELCOME TO THE ESPRESSO TERMINAL     \x1b[33m║\x1b[0m\n"
    "\x1b[33m           ║\x1b[36m     A High-Performance TEA Architecture    \x1b[33m║\x1b[0m\n"
    "\x1b[33m           ╚════════════════════════════════════════════╝\x1b[0m\n"
    "\n"
    "\x1b[92m  [1/4] Connecting to remote gateway at 192.168.1.100... OK\x1b[0m\n"
    "\x1b[92m  [2/4] Verifying cryptographic host fingerprint....... OK\x1b[0m\n"
    "\x1b[92m  [3/4] Initializing Crema style & layout renderer..... OK\x1b[0m\n"
    "\x1b[92m  [4/4] Mounting 43 TEA Beans component library........ OK\x1b[0m\n"
    "\n"
    "\x1b[93m  ✨ READY: All subsystems operational at nominal speed!\x1b[0m"
)


BORDER_PRESETS = [
    ("Rounded", ROUNDED_BORDER),
    ("Double", DOUBLE_BORDER),
    ("Normal", NORMAL_BORDER),
    ("Thick", THICK_BORDER),
    ("Block", BLOCK_BORDER),
]


class ArtPlayerDemo(Model):
    """Main showcase application for ArtPlayer."""

    def __init__(self) -> None:
        self.tabs = Tabs(["1. Animated .3a Art", "2. BBS ANSImation (.ans)", "3. BBS Splash Reveal"])
        self.active_tab_index = 0

        # Player 1: .3a Animated Art
        self.player_3a = ArtPlayer.from_3a(
            ESPRESSO_3A,
            border=ROUNDED_BORDER,
            border_fg="#FF8800",
            show_controls=True,
            show_title=True,
            center_horizontally=True,
            tag="player_3a",
        )

        # Player 2: Multi-frame BBS ANSImation
        self.player_ans = ArtPlayer.from_ans(
            BBS_ANIMATION_TEXT,
            default_delay_ms=90,
            border=DOUBLE_BORDER,
            border_fg="#00E5FF",
            show_controls=True,
            show_title=True,
            title="Classic BBS ANSImation (.ans)",
            center_horizontally=True,
            tag="player_ans",
        )

        # Player 3: Progressive BBS Modem Reveal (Splash Screen)
        # Note: auto_play=False so it only begins when the user visits Tab 3
        self.player_splash = ArtPlayer.from_ans(
            SPLASH_SCREEN_TEXT,
            default_delay_ms=50,
            progressive_lines=True,
            lines_per_frame=1,
            auto_play=False,
            border=ROUNDED_BORDER,
            border_fg="#00E676",
            show_controls=True,
            show_title=True,
            title="BBS Modem Connection Stream",
            center_horizontally=True,
            tag="player_splash",
        )

        self.confetti = Confetti(
            width=80,
            height=24,
            gravity=12.0,
            drag=0.4,
            tag="splash_confetti",
        )

        self.border_index = 0
        self.status_msg = "Playing .3a animation"

    @property
    def current_player(self) -> ArtPlayer:
        if self.active_tab_index == 0:
            return self.player_3a
        elif self.active_tab_index == 1:
            return self.player_ans
        return self.player_splash

    def init(self) -> Cmd:
        # Start only looping animations on boot; Tab 3 begins upon switching to it
        return batch(
            self.player_3a.init(),
            self.player_ans.init(),
        )

    def _switch_to_tab(self, idx: int) -> tuple[Model, Cmd | None]:
        """Switch to a tab and manage animation states (restarting splash if Tab 3)."""
        self.active_tab_index = idx
        tab_cmd = self.tabs.set_active(idx)
        cmds: list[Cmd] = [tab_cmd] if tab_cmd else []

        if idx == 2:
            # Clear any active confetti and restart progressive reveal stream from line 0
            self.confetti.particles = []
            self.status_msg = "Streaming BBS splash reveal at 14.4k baud..."
            cmds.append(self.player_splash.restart())
        elif idx == 1:
            self.status_msg = "Playing multi-frame classic BBS ANSImation"
            if not self.player_ans.is_playing:
                cmds.append(self.player_ans.play())
        elif idx == 0:
            self.status_msg = "Playing .3a animation"
            if not self.player_3a.is_playing:
                cmds.append(self.player_3a.play())

        return self, batch(*cmds) if cmds else None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        # Lifecycle done message from progressive splash screen
        if isinstance(msg, AnimationDoneMsg):
            self.status_msg = f"🎉 Finished: '{msg.title}'! Celebration triggered!"
            # Fire celebratory confetti burst
            confetti_cmd = self.confetti.fire(count=60, mode=ConfettiMode.BURST, origin=(35, 8))
            return self, confetti_cmd

        # Loop lifecycle message
        if isinstance(msg, AnimationLoopMsg):
            self.status_msg = f"Animation looped ({msg.loop_count} cycles)"
            return self, None

        # Route confetti ticks
        if isinstance(msg, ConfettiTickMsg):
            self.confetti, c_cmd = self.confetti.update(msg)
            return self, c_cmd

        # Route player ticks
        if isinstance(msg, ArtPlayerTickMsg):
            if msg.tag == "player_3a":
                self.player_3a, cmd = self.player_3a.update(msg)
                return self, cmd
            elif msg.tag == "player_ans":
                self.player_ans, cmd = self.player_ans.update(msg)
                return self, cmd
            elif msg.tag == "player_splash":
                self.player_splash, cmd = self.player_splash.update(msg)
                return self, cmd

        # Route tab changes from keyboard or mouse
        if isinstance(msg, TabChangeMsg):
            return self._switch_to_tab(msg.index)

        # Handle keyboard interactions
        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app()

                case "tab":
                    next_idx = (self.active_tab_index + 1) % 3
                    return self._switch_to_tab(next_idx)

                case "1" | "2" | "3":
                    idx = int(str(msg.key)) - 1
                    return self._switch_to_tab(idx)

                case "r" | "R":
                    if self.active_tab_index == 2:
                        self.confetti.particles = []
                        self.status_msg = "Restarting BBS splash reveal stream..."
                        return self, self.player_splash.restart()
                    return self, self.current_player.restart()

                case "b" | "B":
                    self.border_index = (self.border_index + 1) % len(BORDER_PRESETS)
                    border_name, border_obj = BORDER_PRESETS[self.border_index]
                    self.current_player.set_border(border_obj)
                    self.status_msg = f"Border style: {border_name}"
                    return self, None

                case _:
                    # Pass remaining keys to active player (Space, Left, Right, + / -)
                    active_p = self.current_player
                    updated_p, p_cmd = active_p.update(msg)
                    return self, p_cmd

        return self, None

    def view(self) -> str:
        # Header banner
        header = (
            Style()
            .bold(True)
            .foreground("#FFD54F")
            .render("☕ Espresso Terminal Art Player (.3a & .ans)")
        )

        # Tabs bar
        tabs_view = self.tabs.view()

        # Active player view
        player_view = self.current_player.view()

        # Overlay celebratory confetti particles if active
        if self.confetti.is_active:
            player_view = self.confetti.overlay(player_view)

        # Controls & Hotkey bar
        border_name, _ = BORDER_PRESETS[self.border_index]
        hints = (
            "\x1b[2m[1-3/Tab] Switch Art   [Space] Play/Pause   [R] Restart   "
            f"[←/→] Step   [+/-] Speed   [B] Border ({border_name})   [Q] Quit\x1b[0m"
        )

        status_line = f"\x1b[36mStatus:\x1b[0m {self.status_msg}"

        return join_vertical(
            Align.LEFT,
            header,
            "",
            tabs_view,
            "",
            player_view,
            "",
            hints,
            status_line,
        )


def main() -> None:
    app = ArtPlayerDemo()
    Program(app).run()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Example 12: Interactive Draggable Elements & Live Terminal Animations.

Showcases:
1. Splitter: Draggable & keyboard-resizable horizontal dual-pane layout.
2. Slider & RangeSlider: Tactile direct-manipulation value sliders with mouse drag.
3. Sparkline: Real-time streaming charts with 2D Braille sub-cell curves and Block bars.
4. Marquee: Smooth horizontally scrolling text banner and news ticker.
5. SortableList: Drag-and-drop & keyboard task list reordering.
"""

from __future__ import annotations

import math
import random
import sys
import time
from pathlib import Path

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    MouseButton,
    MouseMsg,
    Msg,
    Program,
    WindowSizeMsg,
    batch,
    quit_app,
)
from espresso.beans import (
    CodeViewer,
    Marquee,
    MarqueeMode,
    RangeSlider,
    Slider,
    SortableItem,
    SortableList,
    Sparkline,
    SparklineMode,
    Splitter,
    SplitterOrientation,
    Tabs,
    TabStyle,
    Tree,
    TreeNode,
)
from espresso.crema import ROUNDED_BORDER, Style, join_horizontal, join_vertical, string_width

SAMPLE_PYTHON_CODE = '''# Resizable Panes Demo
import asyncio

async def monitor_streams():
    while True:
        data = fetch_telemetry()
        sparkline.push(data)
        await asyncio.sleep(0.3)
'''


class StreamTickMsg(Msg):
    """Timer tick for live streaming telemetry."""


class InteractiveAnimatedApp(Model):
    def __init__(self) -> None:
        self.width = 90
        self.height = 26
        self.active_tab = 0

        # Tabs navigation
        self.tab_titles = ["1 Splitter", "2 Sliders", "3 Live Charts", "4 Sortable List"]
        self.tabs = Tabs(
            titles=self.tab_titles,
            active_tab=0,
            tab_style=TabStyle.PILL,
            show_numbers=False,
        )

        # ---------------- Tab 1: Splitter Components ----------------
        file_tree = Tree(
            nodes=[
                TreeNode(
                    "📁 workspace",
                    children=[
                        TreeNode("📁 src", children=[
                            TreeNode("📄 main.py"),
                            TreeNode("📄 telemetry.py"),
                            TreeNode("📄 layout.py"),
                        ], expanded=True),
                        TreeNode("📁 tests", children=[
                            TreeNode("📄 test_splitter.py"),
                            TreeNode("📄 test_slider.py"),
                        ], expanded=True),
                        TreeNode("📄 README.md"),
                    ],
                    expanded=True,
                )
            ]
        )
        code_view = CodeViewer(
            code=SAMPLE_PYTHON_CODE,
            language="python",
            width=48,
            height=18,
            show_footer=False,
        )
        self.splitter = Splitter(
            pane1=file_tree,
            pane2=code_view,
            orientation=SplitterOrientation.HORIZONTAL,
            width=self.width - 4,
            height=self.height - 7,
            ratio=0.35,
            min_pane1=18,
            min_pane2=25,
        )

        # ---------------- Tab 2: Sliders ----------------
        self.slider_vol = Slider(min_val=0, max_val=100, value=65, width=45, label="Master Volume:", value_format="{value:.0f}%")
        self.slider_speed = Slider(min_val=0.25, max_val=4.0, value=1.0, step=0.25, width=45, label="Playback Speed:", value_format="{value:.2f}x")
        self.slider_bright = Slider(min_val=10, max_val=100, value=80, width=45, label="Brightness:", value_format="{value:.0f} nits")
        self.range_slider = RangeSlider(min_val=20, max_val=20000, low=250, high=8000, step=10, width=55, label="EQ Bandpass:", value_format="{low:.0f}Hz - {high:.0f}Hz")

        # ---------------- Tab 3: Charts & Marquee ----------------
        self.spark_cpu = Sparkline(
            width=self.width - 6,
            height=3,
            mode=SparklineMode.BRAILLE,
            label="CPU Load (Braille 2D):",
            min_val=0,
            max_val=100,
            gradient_stops=["#00E5FF", "#7D56F4", "#FF007F"],
        )
        self.spark_ram = Sparkline(
            width=self.width - 6,
            height=2,
            mode=SparklineMode.BLOCK,
            label="RAM Usage (Block 1D):",
            min_val=0,
            max_val=100,
            style=Style().foreground("#00E676"),
        )
        # Pre-seed initial data points
        for i in range(50):
            val_cpu = 40 + 35 * math.sin(i * 0.2) + random.uniform(-5, 5)
            val_ram = 55 + 20 * math.cos(i * 0.15) + random.uniform(-3, 3)
            self.spark_cpu.push(max(5, min(95, val_cpu)))
            self.spark_ram.push(max(10, min(90, val_ram)))

        self.marquee = Marquee(
            text="🚀 ESPRESSO 2.0: High-Performance Pure Python Terminal UI Framework • Double-Buffered Rendering • SGR 1006 Mouse Dragging • Pure Elegance",
            width=self.width - 4,
            speed=0.1,
            mode=MarqueeMode.LOOP,
            separator="   ☕   ",
            style=Style().bold(True).foreground("#FFFFFF").background("#252538"),
        )
        self.stream_step = 50

        # ---------------- Tab 4: Sortable List ----------------
        initial_tasks = [
            SortableItem(id="1", title="Brew 100% Arabica dark roast espresso", description="Critical morning ritual"),
            SortableItem(id="2", title="Design Elm Architecture TEA state loop", description="Core functional reactive runtime"),
            SortableItem(id="3", title="Implement SGR 1006 mouse dragging & deltas", description="Tactile terminal manipulation"),
            SortableItem(id="4", title="Compute 2D Braille sub-cell dot algorithms", description="4x resolution telemetry sparklines"),
            SortableItem(id="5", title="Ship production-ready Espresso components", description="28+ beans standard library"),
        ]
        self.sortable_list = SortableList(
            items=initial_tasks,
            width=self.width - 6,
            height=8,
        )

        # Styles
        self.title_style = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.border_style = Style().border(ROUNDED_BORDER).border_foreground("#7D56F4")
        self.footer_style = Style().foreground("#8888AA")
        self.card_style = Style().padding(1, 2)
        self._sync_sizes()

    def init(self) -> Cmd | None:
        async def _ticker() -> Msg:
            import asyncio
            await asyncio.sleep(0.3)
            return StreamTickMsg()

        mq_cmd = self.marquee.init()
        return batch(_ticker, mq_cmd) if mq_cmd else _ticker

    def _sync_sizes(self) -> None:
        inner_w = max(40, self.width - 4)
        inner_h = max(10, self.height - 6)
        self.splitter.set_size(inner_w, inner_h)
        self.spark_cpu.width = inner_w - 2
        self.spark_ram.width = inner_w - 2
        self.marquee.width = inner_w
        self.sortable_list.width = inner_w - 2
        self.sortable_list.height = max(5, inner_h - 4)

        # Set screen offsets (x, y) for mouse hit-testing within the bordered card
        # Left border is at x=0, so inner content starts at x=1
        self.splitter.set_offset(1, 3)
        self.slider_vol.set_offset(1, 4)
        self.slider_speed.set_offset(1, 6)
        self.slider_bright.set_offset(1, 8)
        self.range_slider.set_offset(1, 10)
        self.sortable_list.set_offset(1, 6)

    def update(self, msg: Msg) -> tuple[InteractiveAnimatedApp, Cmd | None]:
        cmds: list[Cmd] = []

        if isinstance(msg, WindowSizeMsg):
            self.width = max(60, msg.width)
            self.height = max(18, msg.height)
            self._sync_sizes()
            return self, None

        if isinstance(msg, StreamTickMsg):
            self.stream_step += 1
            # Push new simulated telemetry data
            val_cpu = 40 + 35 * math.sin(self.stream_step * 0.25) + random.uniform(-8, 8)
            val_ram = 60 + 15 * math.cos(self.stream_step * 0.12) + random.uniform(-2, 2)
            self.spark_cpu.push(max(5, min(98, val_cpu)))
            self.spark_ram.push(max(10, min(95, val_ram)))

            async def _next_ticker() -> Msg:
                import asyncio
                await asyncio.sleep(0.3)
                return StreamTickMsg()

            cmds.append(_next_ticker)

        # Marquee timer updates
        self.marquee, mq_cmd = self.marquee.update(msg)
        if mq_cmd:
            cmds.append(mq_cmd)

        if isinstance(msg, KeyMsg):
            match msg.key:
                case "q" | "ctrl+c":
                    return self, quit_app
                case "1" | "2" | "3" | "4":
                    idx = int(str(msg.key)) - 1
                    self.active_tab = idx
                    self.tabs.set_active(idx)
                    return self, batch(*cmds) if cmds else None
                case "tab":
                    self.active_tab = (self.active_tab + 1) % len(self.tab_titles)
                    self.tabs.set_active(self.active_tab)
                    return self, batch(*cmds) if cmds else None

        # Mouse clicks on header tab bar
        if isinstance(msg, MouseMsg) and msg.button == MouseButton.LEFT and msg.y == 0:
            header_w = string_width(self.title_style.render("⚡ ESPRESSO INTERACTIVE")) + 3
            if msg.x >= header_w:
                cur_x = header_w
                for idx, title in enumerate(self.tab_titles):
                    t_len = string_width(title) + 2
                    if cur_x <= msg.x < cur_x + t_len:
                        self.active_tab = idx
                        self.tabs.set_active(idx)
                        return self, batch(*cmds) if cmds else None
                    cur_x += t_len + 2

        # Delegate to active tab component
        if self.active_tab == 0:
            self.splitter, c = self.splitter.update(msg)
            if c:
                cmds.append(c)
        elif self.active_tab == 1:
            self.slider_vol, c1 = self.slider_vol.update(msg)
            self.slider_speed, c2 = self.slider_speed.update(msg)
            self.slider_bright, c3 = self.slider_bright.update(msg)
            self.range_slider, c4 = self.range_slider.update(msg)
            for c in (c1, c2, c3, c4):
                if c:
                    cmds.append(c)
        elif self.active_tab == 3:
            self.sortable_list, c = self.sortable_list.update(msg)
            if c:
                cmds.append(c)

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        # Header bar
        header_title = self.title_style.render("⚡ ESPRESSO INTERACTIVE")
        tabs_bar = self.tabs.view()
        header = f"{header_title}   {tabs_bar}"

        # Card content based on active tab
        content_view = ""
        if self.active_tab == 0:
            info = Style().faint(True).render("Drag the vertical bar '│' with your mouse or use Left/Right arrows (Ctrl for big steps):")
            split_view = self.splitter.view()
            content_view = f"{info}\n{split_view}"

        elif self.active_tab == 1:
            title = Style().bold(True).foreground("#00E5FF").render("🎚️ Tactile Sliders & Range Knobs (Click & Drag Thumb with Mouse):")
            spacer = ""
            row1 = self.slider_vol.view()
            row2 = self.slider_speed.view()
            row3 = self.slider_bright.view()
            row4 = self.range_slider.view()
            eq_hint = Style().faint(True).render("Range slider: Click & drag either thumb, or use Tab to switch active thumb and Left/Right arrows.")
            content_view = "\n\n".join([title, row1, row2, row3, row4, eq_hint])

        elif self.active_tab == 2:
            title = Style().bold(True).foreground("#00E5FF").render("📈 Real-Time Live Streaming Charts & Ticker (Streaming at 3.3Hz):")
            spark1 = self.spark_cpu.view()
            spark2 = self.spark_ram.view()
            ticker_label = Style().bold(True).foreground("#FFD54F").render("Live Marquee Banner:")
            ticker = self.marquee.view()
            content_view = f"{title}\n\n{spark1}\n\n{spark2}\n\n{ticker_label}\n{ticker}"

        elif self.active_tab == 3:
            title = Style().bold(True).foreground("#00E5FF").render("📋 Drag-and-Drop Task Prioritization (Mouse Drag or Keyboard):")
            hint = Style().faint(True).render("• Mouse: Click and drag an item to a new row\n• Keyboard: Space/Enter to grab/drop, Up/Down to move (or Shift+Up/Down to move directly)")
            s_list = self.sortable_list.view()
            content_view = f"{title}\n{hint}\n\n{s_list}"

        # Outer card container
        card_h = self.height - 2
        card = self.border_style.width(self.width - 2).height(card_h).render(content_view)

        # Footer
        footer_text = "1-4 / Tab: Switch View • Mouse Wheel & Drag Enabled • q: Quit"
        footer = self.footer_style.render(footer_text)

        return f"{header}\n{card}\n{footer}"


def main() -> None:
    Program(InteractiveAnimatedApp(), alt_screen=True, mouse=True).run()


if __name__ == "__main__":
    main()

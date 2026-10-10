#!/usr/bin/env python3
"""Generate high-fidelity animated GIFs and MP4 videos of Espresso demos.

Renders frames directly from Espresso TEA models using PIL, Rich ANSI parsing,
and ffmpeg for crisp, flicker-free terminal animations.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure src/ and examples/ are on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
EXAMPLES_DIR = REPO_ROOT / "examples"
OUTPUT_DIR = REPO_ROOT / "assets" / "demos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))

from PIL import Image, ImageDraw, ImageFont
from rich.style import Style
from rich.text import Text
from espresso.crema.width import char_width

FONT_REGULAR_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = 15
CHAR_W = 9
CHAR_H = 18
PAD_X = 24
PAD_TOP = 42
PAD_BOTTOM = 24

FONT_REGULAR = ImageFont.truetype(FONT_REGULAR_PATH, size=FONT_SIZE)
FONT_BOLD = ImageFont.truetype(FONT_BOLD_PATH, size=FONT_SIZE)


def render_ansi_to_image(
    view_text: str,
    title: str = "espresso",
    fixed_cols: int | None = None,
    fixed_rows: int | None = None,
) -> Image.Image:
    """Render a styled ANSI string into a beautiful dark terminal window image."""
    lines = view_text.split("\n")
    if fixed_rows:
        if len(lines) < fixed_rows:
            lines = lines + [""] * (fixed_rows - len(lines))
        else:
            lines = lines[:fixed_rows]

    # Measure max columns
    max_cols = fixed_cols or 0
    if not fixed_cols:
        for l in lines:
            t = Text.from_ansi(l)
            c = sum(char_width(ch) for ch in t.plain)
            if c > max_cols:
                max_cols = c

    # Ensure clean minimum dimensions
    max_cols = max(max_cols, 72)
    row_count = len(lines)

    img_w = int(max_cols * CHAR_W + PAD_X * 2)
    img_h = int(row_count * CHAR_H + PAD_TOP + PAD_BOTTOM)

    # Dark background (Catppuccin Mocha / Dark Slate)
    img = Image.new("RGB", (img_w, img_h), color="#1e1e2e")
    draw = ImageDraw.Draw(img)

    # Window title bar dots
    draw.ellipse([PAD_X, 15, PAD_X + 11, 26], fill="#FF5F56")
    draw.ellipse([PAD_X + 18, 15, PAD_X + 29, 26], fill="#FFBD2E")
    draw.ellipse([PAD_X + 36, 15, PAD_X + 47, 26], fill="#27C93F")

    # Centered title
    title_bbox = FONT_REGULAR.getbbox(title)
    title_w = title_bbox[2] - title_bbox[0]
    title_x = (img_w - title_w) // 2
    draw.text((title_x, 13), title, font=FONT_REGULAR, fill="#6C7086")

    # Render lines
    for row_idx, l in enumerate(lines):
        t = Text.from_ansi(l)
        col_idx = 0
        y = PAD_TOP + row_idx * CHAR_H

        for char_idx, ch in enumerate(t.plain):
            cw = char_width(ch)
            if cw == 0:
                continue

            x = PAD_X + col_idx * CHAR_W
            cell_pixel_w = cw * CHAR_W

            # Look up style from Rich spans
            st = Style.null()
            for span in t.spans:
                if span.start <= char_idx < span.end:
                    st += span.style

            if st.bgcolor:
                bg = st.bgcolor.get_truecolor()
                bg_color = (bg.red, bg.green, bg.blue)
            else:
                bg_color = None

            if st.color:
                fg = st.color.get_truecolor()
                fg_color = (fg.red, fg.green, fg.blue)
            else:
                fg_color = (205, 214, 244)

            use_bold = bool(st.bold)
            f = FONT_BOLD if use_bold else FONT_REGULAR

            # Draw background cell
            if bg_color:
                draw.rectangle(
                    [x, y, x + cell_pixel_w, y + CHAR_H],
                    fill=bg_color,
                )

            # Draw glyph
            if ch != " ":
                draw.text((x, y), ch, font=f, fill=fg_color)

            col_idx += cw

    return img


def save_animation(
    frames: list[Image.Image],
    durations: list[int] | int,
    base_name: str,
) -> tuple[Path, Path]:
    """Save frame sequence as GIF and MP4 with uniform dimensions."""
    gif_path = OUTPUT_DIR / f"{base_name}.gif"
    mp4_path = OUTPUT_DIR / f"{base_name}.mp4"

    # Ensure all frames have identical dimensions
    max_w = max(f.width for f in frames)
    max_h = max(f.height for f in frames)
    uniform_frames: list[Image.Image] = []
    for f in frames:
        if f.size == (max_w, max_h):
            uniform_frames.append(f)
        else:
            new_f = Image.new("RGB", (max_w, max_h), color="#1e1e2e")
            new_f.paste(f, (0, 0))
            uniform_frames.append(new_f)

    if isinstance(durations, int):
        durations = [durations] * len(uniform_frames)

    uniform_frames[0].save(
        gif_path,
        save_all=True,
        append_images=uniform_frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
    )
    print(f"Generated GIF: {gif_path} ({len(uniform_frames)} frames, {os.path.getsize(gif_path):,} bytes)")

    # Convert to MP4 via ffmpeg
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(gif_path),
            "-movflags",
            "faststart",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            str(mp4_path),
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"Generated MP4: {mp4_path} ({os.path.getsize(mp4_path):,} bytes)")
    except Exception as e:
        print(f"MP4 conversion skipped or failed: {e}")

    return gif_path, mp4_path


def generate_steaming_espresso() -> None:
    """Generate animation of Tab 1: Steaming Espresso Cup (.3a)."""
    import importlib
    example16 = importlib.import_module("16_ansi_and_3a_player")
    app = example16.ArtPlayerDemo()
    app._switch_to_tab(0)

    frames: list[Image.Image] = []
    # 4 frames in .3a, cycle 3 times (12 frames total) for smooth loop
    total_frames = 12
    delay_ms = 240

    for _ in range(total_frames):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - steaming cup (.3a)")
        frames.append(img)
        app.player_3a.step_forward()

    save_animation(frames, delay_ms, "demo_steaming_espresso_3a")


def generate_bbs_ansimation() -> None:
    """Generate animation of Tab 2: Classic BBS ANSImation (.ans)."""
    import importlib
    example16 = importlib.import_module("16_ansi_and_3a_player")
    app = example16.ArtPlayerDemo()
    app._switch_to_tab(1)

    frames: list[Image.Image] = []
    # 8 frames in BBS animation, cycle 2 times (16 frames)
    total_frames = 16
    delay_ms = 95

    for _ in range(total_frames):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - bbs demoscene (.ans)")
        frames.append(img)
        app.player_ans.step_forward()

    save_animation(frames, delay_ms, "demo_bbs_demoscene_ans")


def generate_bbs_modem_splash() -> None:
    """Generate animation of Tab 3: Progressive BBS Modem Reveal & Confetti."""
    import importlib
    example16 = importlib.import_module("16_ansi_and_3a_player")
    app = example16.ArtPlayerDemo()
    app._switch_to_tab(2)

    frames: list[Image.Image] = []
    durations: list[int] = []

    # Reveal 10 lines progressively
    for line_step in range(10):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - bbs 14.4k modem reveal")
        frames.append(img)
        durations.append(80)
        app.player_splash.step_forward()

    # Trigger celebration done message
    done_msg = example16.AnimationDoneMsg(title="BBS Modem Connection Stream")
    app.update(done_msg)

    # Animate 24 ticks of confetti explosion
    for tick_step in range(24):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - bbs 14.4k modem reveal")
        frames.append(img)
        durations.append(60)
        app.confetti._step_physics()

    save_animation(frames, durations, "demo_bbs_modem_reveal_confetti")


def generate_physics_confetti() -> None:
    """Generate animation from Example 13: Confetti particle explosion."""
    import importlib
    example13 = importlib.import_module("13_physics_and_tools")
    app = example13.PhysicsAndToolsApp()
    app.width = 82
    app.height = 24
    app._sync_sizes()
    app.active_tab = 1
    app.tabs.set_active(1)

    # Fire celebratory confetti burst
    app.confetti.fire(count=70, mode=example13.ConfettiMode.BURST, origin=(41, 7))

    frames: list[Image.Image] = []
    durations: list[int] = []

    # Animate 30 frames of confetti bursting and floating down
    for tick in range(30):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - particle physics (confetti)")
        frames.append(img)
        durations.append(60)
        app.confetti._step_physics()

    save_animation(frames, durations, "demo_physics_confetti")


def generate_colors_and_gradients() -> None:
    """Generate animation of Example 09: TrueColor Linear Gradients."""
    import importlib
    example09 = importlib.import_module("09_colors_and_gradients")
    app = example09.ColorsAndGradientsDemo()

    frames: list[Image.Image] = []
    durations: list[int] = []

    # Cycle through all 4 color palettes with pauses
    for _ in range(4):
        pal_name = example09.PALETTES[app.palette_idx]["name"]
        view = app.view()
        img = render_ansi_to_image(view, title=f"espresso - crema gradients ({pal_name})")
        # Hold each palette for 3 frames (900ms)
        for _ in range(3):
            frames.append(img)
            durations.append(300)
        # Advance palette
        app.palette_idx = (app.palette_idx + 1) % len(example09.PALETTES)

    save_animation(frames, durations, "demo_colors_and_gradients")


def generate_spring_oscillator() -> None:
    """Generate animation of Example 13 Tab 1: Spring Harmonic Oscillator."""
    import importlib
    example13 = importlib.import_module("13_physics_and_tools")
    app = example13.PhysicsAndToolsApp()
    app.width = 82
    app.height = 24
    app._sync_sizes()
    app.active_tab = 0
    app._apply_spring_preset("Bouncy (ζ=0.35)", 0.35, 120.0)
    app.spring.set_target(85.0)

    frames: list[Image.Image] = []
    durations: list[int] = []

    # Animate 35 frames of harmonic oscillation and trajectory curve plotting
    for _ in range(35):
        view = app.view()
        img = render_ansi_to_image(view, title="espresso - spring physics simulation")
        frames.append(img)
        durations.append(50)
        app.spring.spring.update(0.04)
        app.spring_history.append(app.spring.value)

    save_animation(frames, durations, "demo_spring_oscillator")


def main() -> None:
    print("Generating Espresso demo animations...")
    generate_steaming_espresso()
    generate_bbs_ansimation()
    generate_bbs_modem_splash()
    generate_physics_confetti()
    generate_spring_oscillator()
    generate_colors_and_gradients()
    print("\nAll animations successfully generated in assets/demos/!")


if __name__ == "__main__":
    main()

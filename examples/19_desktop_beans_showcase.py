#!/usr/bin/env python3
"""Example 19: Desktop Application Beans Showcase.

Demonstrates all four new core Beans working seamlessly together with comprehensive mouse controls:
1. MenuBar & DropdownMenu (Top menu with mnemonics, hotkeys, cascading dropdowns, mouse hover & click)
2. MultiSplitter (3-pane resizable layout with draggable dividers, mouse wheel nudging, double-click equalization)
3. CardList (Two-line email list with tree hierarchy, mouse click/drag selection, and wheel scrolling)
4. Wizard (Multi-step guided setup flow with interactive radio selector, mouse-focused inputs, checkboxes, and modal overlay)
5. Interactive Folder Tree & Reading Pane (Clickable folder list, action toolbars, and scrollable message reader)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# Add src/ to sys.path so example runs directly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from espresso import (
    Cmd,
    KeyMsg,
    Model,
    MouseAction,
    MouseButton,
    MouseMsg,
    Msg,
    Program,
    WindowSizeMsg,
    batch,
    quit_app,
)
from espresso.beans import (
    CardActivateMsg,
    CardItem,
    CardList,
    CardSelectMsg,
    MenuBar,
    MenuCategory,
    MenuItem,
    MenuSelectMsg,
    MultiSplitter,
    MultiSplitterResizeMsg,
    SplitterOrientation,
    TextInput,
    Wizard,
    WizardBackMsg,
    WizardCancelMsg,
    WizardCompleteMsg,
    WizardNextMsg,
    WizardStep,
)
from espresso.crema import NORMAL_BORDER, ROUNDED_BORDER, Style, join_vertical, place_overlay
from espresso.crema.width import string_width, truncate_ansi


@dataclass(frozen=True)
class FolderSelectMsg(Msg):
    """Message emitted when a folder is selected from the folder list."""

    folder_id: str
    folder_name: str


@dataclass(frozen=True)
class EmailActionMsg(Msg):
    """Message emitted when an email action button is clicked."""

    action: str  # "star", "unread", "archive", "trash"
    message_id: str


SAMPLE_EMAILS: list[CardItem] = [
    CardItem(
        id="m1",
        title="Linus Torvalds",
        subtitle="[GIT PULL] Linux 6.13 x86 architecture fixes and microcode updates",
        badge_text="10:42 AM",
        glyphs="★",
        is_unread=True,
        data={
            "folder": "inbox",
            "is_starred": True,
            "is_archived": False,
            "is_trashed": False,
            "from": "Linus Torvalds <torvalds@linux-foundation.org>",
            "to": "Linux Kernel Mailing List <linux-kernel@vger.kernel.org>",
            "date": "Today, 10:42 AM",
            "subject": "[GIT PULL] Linux 6.13 x86 architecture fixes",
            "body": (
                "Please pull the latest x86 fixes for 6.13-rc5 from:\n\n"
                "  git://git.kernel.org/pub/scm/linux/kernel/git/tip/tip.git x86-urgent\n\n"
                "Notable changes:\n"
                " - Fix microcode patch loader memory leak in early boot\n"
                " - Correct page table isolation fault on older AMD Zen CPUs\n"
                " - Clean up TSC synchronization warning on hypervisors\n"
                " - Add kernel selftest regression coverage for nested KVM guests\n\n"
                "Diffstat:\n"
                " arch/x86/kernel/cpu/microcode/core.c | 14 ++++++---\n"
                " arch/x86/mm/pti.c                    |  9 +++++-\n"
                " 2 files changed, 18 insertions(+), 5 deletions(-)"
            ),
        },
    ),
    CardItem(
        id="m2",
        title="Greg Kroah-Hartman",
        subtitle="Re: [GIT PULL] Linux 6.13 x86 architecture fixes",
        badge_text="11:15 AM",
        depth=1,
        is_unread=True,
        data={
            "folder": "inbox",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "Greg Kroah-Hartman <gregkh@linuxfoundation.org>",
            "to": "Linus Torvalds <torvalds@linux-foundation.org>",
            "date": "Today, 11:15 AM",
            "subject": "Re: [GIT PULL] Linux 6.13 x86 architecture fixes",
            "body": (
                "Pulled and queued for the stable tree review cycle as well.\n\n"
                "All CI tests in kernel-build farm passed across x86_64 and arm64 targets\n"
                "without any regression."
            ),
        },
    ),
    CardItem(
        id="m3",
        title="Peter Zijlstra",
        subtitle="Re: [GIT PULL] Benchmark numbers on Zen 4",
        badge_text="11:30 AM",
        depth=2,
        data={
            "folder": "inbox",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "Peter Zijlstra <peterz@infradead.org>",
            "to": "Greg Kroah-Hartman <gregkh@linuxfoundation.org>",
            "date": "Today, 11:30 AM",
            "subject": "Re: [GIT PULL] Benchmark numbers on Zen 4",
            "body": (
                "Scheduler benchmark numbers showed 0.4% speedup on hackbench\n"
                "after the microcode loading fix.\n\n"
                "Will send scheduler followups for the next merge window."
            ),
        },
    ),
    CardItem(
        id="m4",
        title="GitHub Notifications",
        subtitle="Pull request #42 merged: 'Crema ANSI sub-slice performance'",
        badge_text="Yesterday",
        glyphs="📎",
        data={
            "folder": "inbox",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "GitHub <notifications@github.com>",
            "to": "Espresso Team <dev@espresso.tui>",
            "date": "Yesterday, 4:18 PM",
            "subject": "Merged: Crema ANSI sub-slice performance",
            "body": (
                "PR #42 by @kimschulz has been merged into main.\n\n"
                "Changes: Optimized slice_ansi grapheme iterations for zero-allocation\n"
                "rendering in 100+ fps terminal redraw cycles."
            ),
        },
    ),
    CardItem(
        id="m5",
        title="Security Alert",
        subtitle="Critical advisory CVE-2026-1029: TLS session ticket reuse",
        badge_text="Oct 26",
        glyphs="🔒",
        data={
            "folder": "inbox",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "Security Team <security@espresso.tui>",
            "to": "All Developers <all@espresso.tui>",
            "date": "Oct 26, 2:00 PM",
            "subject": "Critical advisory CVE-2026-1029",
            "body": (
                "A potential session ticket reuse bug has been mitigated in 1.2.0.\n"
                "Please ensure all production instances are upgraded."
            ),
        },
    ),
    CardItem(
        id="m6",
        title="Fastmail Support",
        subtitle="Your custom domain SSL certificates were renewed",
        badge_text="Oct 24",
        data={
            "folder": "inbox",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "Fastmail Support <support@fastmail.com>",
            "to": "Kim Schulz <kim@example.org>",
            "date": "Oct 24, 9:02 AM",
            "subject": "Custom domain SSL certificates renewed",
            "body": (
                "Your Let's Encrypt certificates for mail.example.org have been\n"
                "automatically renewed for the next 90 days."
            ),
        },
    ),
    CardItem(
        id="m7",
        title="Python Software Foundation",
        subtitle="Receipt for your donation to PyPI Security Fund",
        badge_text="Oct 20",
        glyphs="★",
        data={
            "folder": "sent",
            "is_starred": True,
            "is_archived": False,
            "is_trashed": False,
            "from": "Kim Schulz <kim@example.org>",
            "to": "donations@python.org",
            "date": "Oct 20, 1:45 PM",
            "subject": "PyPI Security Fund Support Donation",
            "body": (
                "Thank you for supporting Python infrastructure and trusted publishing\n"
                "initiatives for the global community."
            ),
        },
    ),
    CardItem(
        id="m8",
        title="Draft: Espresso 1.3 Architecture Proposal",
        subtitle="Proposal for official Beans standardization and Crema 2.0 layout",
        badge_text="Draft",
        data={
            "folder": "drafts",
            "is_starred": False,
            "is_archived": False,
            "is_trashed": False,
            "from": "Kim Schulz <kim@example.org>",
            "to": "architecture-board@espresso.tui",
            "date": "Draft unsent",
            "subject": "Espresso 1.3 Architecture Proposal",
            "body": (
                "Hey team,\n\n"
                "Here are the draft specifications for MenuBar, MultiSplitter, Wizard,\n"
                "and CardList components."
            ),
        },
    ),
]


class FolderTreePane(Model):
    """Left pane: Account & folder tree list with mouse selection, hover, and wheel scrolling."""

    def __init__(self, selected_folder_id: str = "inbox") -> None:
        self.width = 20
        self.height = 20
        self.selected_folder_id = selected_folder_id
        self.hover_idx = -1
        self.folders = [
            {"id": "inbox", "name": "📥 Inbox", "count": 2},
            {"id": "starred", "name": "⭐ Starred", "count": 2},
            {"id": "sent", "name": "📤 Sent", "count": 1},
            {"id": "drafts", "name": "📝 Drafts", "count": 1},
            {"id": "archive", "name": "📦 Archive", "count": 0},
            {"id": "trash", "name": "🗑️ Trash", "count": 0},
        ]

    def set_size(self, width: int, height: int) -> None:
        self.width = max(10, width)
        self.height = max(5, height)

    def set_counts(self, counts: dict[str, int]) -> None:
        for f in self.folders:
            f_id = f["id"]
            if f_id in counts:
                f["count"] = counts[f_id]

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[FolderTreePane, Cmd | None]:
        if isinstance(msg, MouseMsg):
            # 1. Mouse wheel cycles folders
            if msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN):
                step = -1 if msg.button == MouseButton.WHEEL_UP else 1
                curr_idx = next(
                    (i for i, f in enumerate(self.folders) if f["id"] == self.selected_folder_id), 0
                )
                new_idx = max(0, min(len(self.folders) - 1, curr_idx + step))
                f = self.folders[new_idx]
                self.selected_folder_id = f["id"]
                f_id, f_name = f["id"], f["name"]
                return self, lambda: FolderSelectMsg(folder_id=f_id, folder_name=f_name)

            # Header is row 0, divider is row 1, folders start at row 2
            folder_row = msg.y - 2

            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                if msg.button == MouseButton.LEFT and 0 <= folder_row < len(self.folders):
                    f = self.folders[folder_row]
                    self.selected_folder_id = f["id"]
                    f_id, f_name = f["id"], f["name"]
                    return self, lambda: FolderSelectMsg(folder_id=f_id, folder_name=f_name)

            elif msg.action == MouseAction.MOTION:
                self.hover_idx = folder_row if 0 <= folder_row < len(self.folders) else -1

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k in ("up", "k", "down", "j"):
                step = -1 if k in ("up", "k") else 1
                curr_idx = next(
                    (i for i, f in enumerate(self.folders) if f["id"] == self.selected_folder_id), 0
                )
                new_idx = max(0, min(len(self.folders) - 1, curr_idx + step))
                f = self.folders[new_idx]
                self.selected_folder_id = f["id"]
                f_id, f_name = f["id"], f["name"]
                return self, lambda: FolderSelectMsg(folder_id=f_id, folder_name=f_name)

        return self, None

    def view(self) -> str:
        border_s = Style().foreground("#45475A")
        header_s = Style().bold(True).foreground("#89B4FA")
        sel_s = Style().bold(True).background("#313244").foreground("#CDD6F4")
        hover_s = Style().background("#262738").foreground("#CDD6F4")
        item_s = Style().foreground("#A6ADC8")
        unread_s = Style().bold(True).foreground("#F38BA8")

        lines: list[str] = [
            header_s.render(" Folders"),
            border_s.render("─" * max(4, self.width)),
        ]

        for idx, f in enumerate(self.folders):
            is_active = (f["id"] == self.selected_folder_id)
            is_hover = (idx == self.hover_idx and not is_active)
            unread = f["count"]

            tag = f" ({unread})" if unread > 0 else ""
            prefix = "▶ " if is_active else "  "
            raw_text = f"{prefix}{f['name']}{tag}"
            pad = max(0, self.width - len(raw_text))
            content = f"{raw_text}{' ' * pad}"

            if is_active:
                lines.append(sel_s.render(content))
            elif is_hover:
                lines.append(hover_s.render(content))
            else:
                lines.append(item_s.render(content))

        while len(lines) < self.height:
            lines.append(" " * self.width)

        return "\n".join(lines[: self.height])


class MessageDetailPane(Model):
    """Right pane: Email message reader with interactive toolbar buttons and scrollable body."""

    def __init__(self, message: CardItem | None = None) -> None:
        self.width = 40
        self.height = 20
        self.message = message
        self.scroll_y = 0
        self._btn_bounds: list[tuple[str, int, int]] = []  # (action, start_x, end_x)

    def set_size(self, width: int, height: int) -> None:
        self.width = max(10, width)
        self.height = max(5, height)

    def set_message(self, message: CardItem | None) -> None:
        self.message = message
        self.scroll_y = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MessageDetailPane, Cmd | None]:
        if isinstance(msg, MouseMsg):
            # Row 0: Interactive Action Buttons
            if msg.y == 0 and msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                if msg.button == MouseButton.LEFT and self.message:
                    for action, x0, x1 in self._btn_bounds:
                        if x0 <= msg.x < x1:
                            m_id = self.message.id
                            return self, lambda: EmailActionMsg(action=action, message_id=m_id)

            # Wheel anywhere over reading pane scrolls email body
            elif msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN):
                step = 3 if msg.ctrl else 1
                delta = -step if msg.button == MouseButton.WHEEL_UP else step
                self.scroll_y = max(0, self.scroll_y + delta)
                return self, None

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k in ("up", "k"):
                self.scroll_y = max(0, self.scroll_y - 1)
            elif k in ("down", "j"):
                self.scroll_y += 1
            elif k in ("pageup", "ctrl+u"):
                self.scroll_y = max(0, self.scroll_y - 8)
            elif k in ("pagedown", "ctrl+d"):
                self.scroll_y += 8

        return self, None

    def view(self) -> str:
        border_s = Style().foreground("#45475A")
        header_label_s = Style().bold(True).foreground("#89B4FA")
        header_val_s = Style().foreground("#CDD6F4")
        body_s = Style().foreground("#BAC2DE")
        btn_s = Style().background("#313244").foreground("#CDD6F4")
        btn_active_s = Style().bold(True).background("#F9E2AF").foreground("#11111B")

        if not self.message or not self.message.data:
            empty_msg = Style().italic(True).foreground("#6C7086").render("  No message selected")
            lines = [empty_msg]
            while len(lines) < self.height:
                lines.append(" " * self.width)
            return "\n".join(lines[: self.height])

        data = self.message.data

        # --- Row 0: Action Toolbar Buttons ---
        self._btn_bounds = []
        is_starred = self.message.glyphs == "★" or data.get("is_starred", False)
        is_unread = self.message.is_unread

        b_star_txt = " ★ Starred " if is_starred else " ☆ Star "
        b_unread_txt = " ✉ Unread " if not is_unread else " ✉ Mark Read "
        b_arch_txt = " 📦 Archive "
        b_del_txt = " 🗑️ Delete "

        cur_x = 1
        rendered_buttons: list[str] = [" "]

        for action, text, is_hl in [
            ("star", b_star_txt, is_starred),
            ("unread", b_unread_txt, is_unread),
            ("archive", b_arch_txt, False),
            ("trash", b_del_txt, False),
        ]:
            w = len(text)
            self._btn_bounds.append((action, cur_x, cur_x + w))
            cur_x += w + 1
            st = btn_active_s if is_hl else btn_s
            rendered_buttons.append(st.render(text) + " ")

        toolbar_str = "".join(rendered_buttons)
        pad_tb = max(0, self.width - cur_x)
        toolbar_rendered = toolbar_str + (" " * pad_tb)

        lines: list[str] = [
            toolbar_rendered,
            border_s.render("─" * max(4, self.width)),
            f" {header_label_s.render('Subject:')} {header_val_s.render(data.get('subject', ''))}",
            f" {header_label_s.render('From:')}    {header_val_s.render(data.get('from', ''))}",
            f" {header_label_s.render('To:')}      {header_val_s.render(data.get('to', ''))}",
            f" {header_label_s.render('Date:')}    {header_val_s.render(data.get('date', ''))}",
            border_s.render("─" * max(4, self.width)),
        ]

        # Body lines with smooth scroll
        body_raw = data.get("body", "").split("\n")
        visible_body_slots = max(1, self.height - len(lines))

        # Clamp scroll_y
        max_scroll = max(0, len(body_raw) - visible_body_slots)
        self.scroll_y = min(self.scroll_y, max_scroll)

        visible_slice = body_raw[self.scroll_y : self.scroll_y + visible_body_slots]
        for b_line in visible_slice:
            lines.append(f" {body_s.render(b_line)}")

        while len(lines) < self.height:
            lines.append(" " * self.width)

        return "\n".join(lines[: self.height])


class ProviderSelector(Model):
    """Wizard Step 1: Interactive account provider radio selector with full mouse support."""

    def __init__(self, on_change: Callable[[str], None] | None = None) -> None:
        self.selected_idx = 0
        self.on_change = on_change
        self.providers = [
            ("Fastmail", "IMAP SSL (port 993) / SMTP STARTTLS", "imap.fastmail.com"),
            ("Gmail / Google Workspace", "OAuth2 / IMAP (imap.gmail.com)", "imap.gmail.com"),
            ("Self-hosted Mailserver", "Dovecot IMAP / Postfix submission", "mail.example.org"),
            ("Microsoft 365 / Exchange", "Modern Auth / Exchange Web Services", "outlook.office365.com"),
        ]

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[ProviderSelector, Cmd | None]:
        if isinstance(msg, MouseMsg):
            # 1. Mouse wheel cycles provider options
            if msg.button in (MouseButton.WHEEL_UP, MouseButton.WHEEL_DOWN):
                step = -1 if msg.button == MouseButton.WHEEL_UP else 1
                self.selected_idx = max(0, min(len(self.providers) - 1, self.selected_idx + step))
                if self.on_change:
                    self.on_change(self.providers[self.selected_idx][2])
                return self, None

            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                # 2 lines per option (title + description)
                clicked_idx = msg.y // 2
                if 0 <= clicked_idx < len(self.providers):
                    self.selected_idx = clicked_idx
                    if self.on_change:
                        self.on_change(self.providers[self.selected_idx][2])
                    if msg.action == MouseAction.DOUBLE_CLICK:
                        # Double-click selects and advances wizard step
                        return self, lambda: WizardNextMsg(from_step=0, to_step=1)
                    return self, None

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k in ("up", "k"):
                self.selected_idx = max(0, self.selected_idx - 1)
                if self.on_change:
                    self.on_change(self.providers[self.selected_idx][2])
            elif k in ("down", "j"):
                self.selected_idx = min(len(self.providers) - 1, self.selected_idx + 1)
                if self.on_change:
                    self.on_change(self.providers[self.selected_idx][2])
            elif k in ("1", "2", "3", "4"):
                self.selected_idx = int(k) - 1
                if self.on_change:
                    self.on_change(self.providers[self.selected_idx][2])

        return self, None

    def view(self) -> str:
        lines: list[str] = []
        for idx, (name, desc, _) in enumerate(self.providers):
            is_sel = (idx == self.selected_idx)
            radio = "●" if is_sel else "○"
            if is_sel:
                line = Style().bold(True).foreground("#89B4FA").render(f"  ({radio}) {name}")
                sub = Style().foreground("#BAC2DE").render(f"      {desc}")
            else:
                line = Style().foreground("#CDD6F4").render(f"  ({radio}) {name}")
                sub = Style().foreground("#6C7086").render(f"      {desc}")
            lines.extend([line, sub])

        lines.append("")
        lines.append(
            Style()
            .foreground("#6C7086")
            .render("  [Click or Double-click profile  •  Wheel to cycle]")
        )
        return "\n".join(lines)


class CredentialsForm(Model):
    """Wizard Step 2: Form container with click-to-focus inputs and Tab switching."""

    def __init__(self, name_inp: TextInput, email_inp: TextInput, srv_inp: TextInput) -> None:
        self.inputs = [name_inp, email_inp, srv_inp]
        self.focus_idx = 0
        self._sync_focus()

    def _sync_focus(self) -> None:
        for idx, inp in enumerate(self.inputs):
            if idx == self.focus_idx:
                inp.focus()
            else:
                inp.blur()

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[CredentialsForm, Cmd | None]:
        if isinstance(msg, MouseMsg):
            # Row 0: empty
            # Row 1: input 0 (Full Name)
            # Row 2: input 1 (Email Address)
            # Row 3: input 2 (IMAP Server)
            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                clicked_idx = msg.y - 1
                if 0 <= clicked_idx < len(self.inputs):
                    self.focus_idx = clicked_idx
                    self._sync_focus()
                    inp = self.inputs[self.focus_idx]
                    prompt_w = string_width(inp.prompt)
                    if msg.x >= prompt_w:
                        char_pos = msg.x - prompt_w
                        inp.cursor_pos = max(0, min(len(inp.value), char_pos))
                    return self, None

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k == "tab":
                self.focus_idx = (self.focus_idx + 1) % len(self.inputs)
                self._sync_focus()
                return self, None
            if k in ("shift+tab", "backtab"):
                self.focus_idx = (self.focus_idx - 1) % len(self.inputs)
                self._sync_focus()
                return self, None

        cur = self.inputs[self.focus_idx]
        new_inp, cmd = cur.update(msg)
        self.inputs[self.focus_idx] = new_inp
        return self, cmd

    def view(self) -> str:
        return join_vertical(
            "",
            self.inputs[0].view(),
            self.inputs[1].view(),
            self.inputs[2].view(),
            "",
            Style().foreground("#6C7086").render("  [Click field or Tab to switch  •  Enter to advance]"),
        )


class SecurityOptions(Model):
    """Wizard Step 3: Interactive checkboxes toggleable via mouse clicks or Space."""

    def __init__(self) -> None:
        self.options = [
            {"label": "TLS 1.3 enforced (Strict Certificate Pinning)", "checked": True},
            {"label": "Ed25519 OpenPGP encryption key pair generated", "checked": True},
            {"label": "ManageSieve server-side filtering enabled", "checked": True},
            {"label": "Enable offline caching and local message indexing", "checked": True},
        ]
        self.cursor_idx = 0

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[SecurityOptions, Cmd | None]:
        if isinstance(msg, MouseMsg):
            if msg.action in (MouseAction.PRESS, MouseAction.DOUBLE_CLICK):
                if 0 <= msg.y < len(self.options):
                    self.cursor_idx = msg.y
                    self.options[msg.y]["checked"] = not self.options[msg.y]["checked"]
                    return self, None

        elif isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k in ("up", "k"):
                self.cursor_idx = max(0, self.cursor_idx - 1)
            elif k in ("down", "j"):
                self.cursor_idx = min(len(self.options) - 1, self.cursor_idx + 1)
            elif k in (" ", "space", "enter"):
                self.options[self.cursor_idx]["checked"] = not self.options[self.cursor_idx]["checked"]

        return self, None

    def view(self) -> str:
        lines: list[str] = []
        for idx, opt in enumerate(self.options):
            checked = opt["checked"]
            box = "✔" if checked else " "
            is_cur = (idx == self.cursor_idx)
            box_styled = (
                Style().bold(True).foreground("#A6E3A1").render(f"[{box}]")
                if checked
                else Style().foreground("#6C7086").render(f"[{box}]")
            )
            text_style = (
                Style().bold(True).foreground("#CDD6F4") if is_cur else Style().foreground("#BAC2DE")
            )
            arrow = "▶ " if is_cur else "  "
            lines.append(f"{arrow}{box_styled} {text_style.render(opt['label'])}")

        lines.append("")
        lines.append(
            Style()
            .foreground("#6C7086")
            .render("  [Click any checkbox to toggle security policy]")
        )
        return "\n".join(lines)


class DesktopShowcaseApp(Model):
    """Main desktop application coordinating MenuBar, MultiSplitter, CardList, and Wizard."""

    def __init__(self) -> None:
        self.width = 100
        self.height = 28
        self.status_message = "Ready. Click menu, drag dividers, or click messages."
        self.show_wizard = False
        self.active_folder_id = "inbox"

        # 1. MenuBar
        self.menu_bar = MenuBar(
            categories=[
                MenuCategory(
                    id="file",
                    label="File",
                    mnemonic="f",
                    items=[
                        MenuItem(id="new_account", label="New Account Wizard...", shortcut="w"),
                        MenuItem(id="import", label="Import Mbox File...", shortcut="Ctrl+I"),
                        MenuItem(id="sep1", label="", is_separator=True),
                        MenuItem(id="exit", label="Exit Application", shortcut="q"),
                    ],
                ),
                MenuCategory(
                    id="edit",
                    label="Edit",
                    mnemonic="e",
                    items=[
                        MenuItem(id="mark_read", label="Mark Message as Read", shortcut="m"),
                        MenuItem(id="toggle_star", label="Toggle Star (★)", shortcut="s"),
                        MenuItem(id="archive", label="Archive Message", shortcut="e"),
                        MenuItem(id="trash", label="Move to Trash", shortcut="Del"),
                    ],
                ),
                MenuCategory(
                    id="view",
                    label="View",
                    mnemonic="v",
                    items=[
                        MenuItem(id="equalize_split", label="Equalize 3-Pane Split (33%)", shortcut="="),
                        MenuItem(id="cycle_divider", label="Cycle Splitter Divider", shortcut="Tab"),
                        MenuItem(id="sep2", label="", is_separator=True),
                        MenuItem(id="folder_inbox", label="Go to Inbox"),
                        MenuItem(id="folder_starred", label="Go to Starred"),
                        MenuItem(id="folder_sent", label="Go to Sent"),
                    ],
                ),
                MenuCategory(
                    id="help",
                    label="Help",
                    mnemonic="h",
                    items=[
                        MenuItem(id="quick_start", label="Quick Start Guide"),
                        MenuItem(id="about", label="About Espresso Desktop"),
                    ],
                ),
            ],
            width=self.width,
            brand=" ☕ EspressoDesktop ",
            right_status="v1.3.0 ",
        )

        # 2. Left Pane: Folder Tree
        self.folder_pane = FolderTreePane(selected_folder_id="inbox")

        # 3. Middle Pane: CardList
        self.all_emails = list(SAMPLE_EMAILS)
        self.card_list = CardList(
            items=self._get_folder_emails("inbox"),
            selected_index=0,
            width=40,
            height=20,
        )

        # 4. Right Pane: Reading Pane
        self.detail_pane = MessageDetailPane(message=self.card_list.get_selected_item())

        # 5. MultiSplitter (3 Panes: Folders, Message List, Reading Pane)
        self.splitter = MultiSplitter(
            panes=[self.folder_pane, self.card_list, self.detail_pane],
            ratios=[0.20, 0.40, 0.40],
            min_sizes=[16, 28, 28],
            orientation=SplitterOrientation.HORIZONTAL,
            width=self.width,
            height=self.height - 2,
            offset_y=1,
        )

        # 6. Wizard Components
        self.wizard_input_name = TextInput(placeholder="Jane Doe", prompt="Full Name:     ")
        self.wizard_input_email = TextInput(placeholder="jane@example.com", prompt="Email Address: ")
        self.wizard_input_server = TextInput(placeholder="imap.fastmail.com", prompt="IMAP Server:   ")
        self.credentials_form = CredentialsForm(
            self.wizard_input_name, self.wizard_input_email, self.wizard_input_server
        )

        def _on_provider_change(default_srv: str) -> None:
            self.wizard_input_server.value = default_srv

        self.provider_selector = ProviderSelector(on_change=_on_provider_change)
        self.security_options = SecurityOptions()

        def _validate_step2() -> tuple[bool, str]:
            if not self.wizard_input_email.value.strip():
                return False, "Email address cannot be empty!"
            if "@" not in self.wizard_input_email.value:
                return False, "Please enter a valid email address with '@'!"
            return True, ""

        self.wizard = Wizard(
            steps=[
                WizardStep(
                    id="provider",
                    title="Account Type",
                    description="Select an account configuration profile",
                    content=self.provider_selector,
                ),
                WizardStep(
                    id="credentials",
                    title="User Credentials",
                    description="Enter your display name and login email",
                    content=self.credentials_form,
                    validate=_validate_step2,
                ),
                WizardStep(
                    id="security",
                    title="Encryption & TLS",
                    description="Confirm OpenPGP keys and TLS verification",
                    content=self.security_options,
                ),
            ],
            width=74,
            height=16,
            allow_cancel=True,
        )

        self._status_buttons: list[tuple[str, int, int]] = []
        self._update_folder_counts()

    def _get_folder_emails(self, folder_id: str) -> list[CardItem]:
        if folder_id == "inbox":
            return [
                m
                for m in self.all_emails
                if not m.data.get("is_archived") and not m.data.get("is_trashed")
            ]
        elif folder_id == "starred":
            return [
                m
                for m in self.all_emails
                if (m.glyphs == "★" or m.data.get("is_starred")) and not m.data.get("is_trashed")
            ]
        elif folder_id == "sent":
            return [m for m in self.all_emails if m.data.get("folder") == "sent"]
        elif folder_id == "drafts":
            return [m for m in self.all_emails if m.data.get("folder") == "drafts"]
        elif folder_id == "archive":
            return [m for m in self.all_emails if m.data.get("is_archived")]
        elif folder_id == "trash":
            return [m for m in self.all_emails if m.data.get("is_trashed")]
        return list(self.all_emails)

    def _update_folder_counts(self) -> None:
        counts = {
            "inbox": len(self._get_folder_emails("inbox")),
            "starred": len(self._get_folder_emails("starred")),
            "sent": len(self._get_folder_emails("sent")),
            "drafts": len(self._get_folder_emails("drafts")),
            "archive": len(self._get_folder_emails("archive")),
            "trash": len(self._get_folder_emails("trash")),
        }
        self.folder_pane.set_counts(counts)

    def init(self) -> Cmd | None:
        return batch(self.menu_bar.init(), self.splitter.init(), self.wizard.init())

    def update(self, msg: Msg) -> tuple[DesktopShowcaseApp, Cmd | None]:
        cmds: list[Cmd] = []

        # Handle terminal resize
        if isinstance(msg, WindowSizeMsg):
            self.width = max(60, msg.width)
            self.height = max(18, msg.height)
            self.menu_bar.set_size(self.width)
            self.splitter.set_size(self.width, self.height - 2)
            return self, None

        # Modal Wizard active
        if self.show_wizard:
            wiz_x = max(0, (self.width - self.wizard.width) // 2)
            wiz_y = max(0, (self.height - self.wizard.height) // 2)
            self.wizard.set_offset(wiz_x, wiz_y)

            if isinstance(msg, WizardCompleteMsg):
                self.show_wizard = False
                email = self.wizard_input_email.value or "account"
                self.status_message = f"Account '{email}' configured successfully!"
                return self, None

            if isinstance(msg, WizardCancelMsg):
                self.show_wizard = False
                self.status_message = "Account configuration wizard cancelled."
                return self, None

            # Clicking dimmed backdrop outside centered modal cancels wizard
            if (
                isinstance(msg, MouseMsg)
                and msg.action == MouseAction.PRESS
                and self.wizard.allow_cancel
            ):
                if (
                    msg.x < wiz_x
                    or msg.x >= wiz_x + self.wizard.width
                    or msg.y < wiz_y
                    or msg.y >= wiz_y + self.wizard.height
                ):
                    self.show_wizard = False
                    self.status_message = "Account configuration wizard cancelled."
                    return self, None

            self.wizard, w_cmd = self.wizard.update(msg)
            if w_cmd:
                cmds.append(w_cmd)
            return self, batch(*cmds) if cmds else None

        # Check global keyboard shortcuts when wizard is closed
        if isinstance(msg, KeyMsg):
            k = str(msg.key).lower()
            if k == "q" and not self.menu_bar.is_open:
                return self, quit_app()

            if k == "w" and not self.menu_bar.is_open:
                self.show_wizard = True
                self.wizard.current_step = 0
                self.wizard_input_name.focus()
                self.status_message = "Account Setup Wizard opened."
                return self, None

            if k == "=" and not self.menu_bar.is_open:
                cmd = self.splitter.set_ratios([1.0 / 3, 1.0 / 3, 1.0 / 3])
                if cmd:
                    cmds.append(cmd)
                self.status_message = "Layout split ratios equalized to 33% / 33% / 33%."
                return self, batch(*cmds) if cmds else None

        # Process MenuBar selection events
        if isinstance(msg, MenuSelectMsg):
            if msg.item_id == "exit":
                return self, quit_app()
            elif msg.item_id == "new_account":
                self.show_wizard = True
                self.wizard.current_step = 0
                self.status_message = "Account Setup Wizard opened."
            elif msg.item_id == "equalize_split":
                cmd = self.splitter.set_ratios([1.0 / 3, 1.0 / 3, 1.0 / 3])
                if cmd:
                    cmds.append(cmd)
                self.status_message = "Layout split ratios equalized to 33% / 33% / 33%."
            elif msg.item_id == "mark_read":
                sel = self.card_list.get_selected_item()
                if sel:
                    sel.is_unread = False
                    self._update_folder_counts()
                    self.status_message = f"Marked '{sel.title}' as read."
            elif msg.item_id == "toggle_star":
                sel = self.card_list.get_selected_item()
                if sel:
                    is_starred = sel.glyphs == "★"
                    sel.glyphs = "" if is_starred else "★"
                    sel.data["is_starred"] = not is_starred
                    self._update_folder_counts()
                    self.status_message = f"Toggled star for '{sel.title}'."
            elif msg.item_id == "archive":
                sel = self.card_list.get_selected_item()
                if sel:
                    sel.data["is_archived"] = True
                    self.card_list.set_items(self._get_folder_emails(self.active_folder_id))
                    self.detail_pane.set_message(self.card_list.get_selected_item())
                    self._update_folder_counts()
                    self.status_message = f"Archived message '{sel.title}'."
            elif msg.item_id.startswith("folder_"):
                f_target = msg.item_id.replace("folder_", "")
                self.active_folder_id = f_target
                self.folder_pane.selected_folder_id = f_target
                self.card_list.set_items(self._get_folder_emails(f_target))
                self.detail_pane.set_message(self.card_list.get_selected_item())
                self.status_message = f"Switched to folder: {f_target.capitalize()}."
            else:
                self.status_message = f"Menu selected: {msg.category_id} -> {msg.item_id}"
            return self, batch(*cmds) if cmds else None

        # Process Folder selection
        if isinstance(msg, FolderSelectMsg):
            self.active_folder_id = msg.folder_id
            self.card_list.set_items(self._get_folder_emails(msg.folder_id))
            self.detail_pane.set_message(self.card_list.get_selected_item())
            self.status_message = f"Opened folder: {msg.folder_name} ({len(self.card_list.items)} messages)"
            return self, None

        # Process CardList selection events
        if isinstance(msg, CardSelectMsg):
            self.detail_pane.set_message(msg.item)
            self.status_message = f"Selected: {msg.item.title} — {msg.item.subtitle[:35]}..."
            return self, None

        if isinstance(msg, CardActivateMsg):
            msg.item.is_unread = False
            self.detail_pane.set_message(msg.item)
            self._update_folder_counts()
            self.status_message = f"Opened message from {msg.item.title}."
            return self, None

        # Process Email toolbar actions
        if isinstance(msg, EmailActionMsg):
            sel = self.detail_pane.message
            if sel:
                if msg.action == "star":
                    is_starred = sel.glyphs == "★"
                    sel.glyphs = "" if is_starred else "★"
                    sel.data["is_starred"] = not is_starred
                    self.status_message = f"Toggled star for '{sel.title}'."
                elif msg.action == "unread":
                    sel.is_unread = not sel.is_unread
                    st = "unread" if sel.is_unread else "read"
                    self.status_message = f"Marked '{sel.title}' as {st}."
                elif msg.action == "archive":
                    sel.data["is_archived"] = True
                    self.card_list.set_items(self._get_folder_emails(self.active_folder_id))
                    self.detail_pane.set_message(self.card_list.get_selected_item())
                    self.status_message = f"Archived message '{sel.title}'."
                elif msg.action == "trash":
                    sel.data["is_trashed"] = True
                    self.card_list.set_items(self._get_folder_emails(self.active_folder_id))
                    self.detail_pane.set_message(self.card_list.get_selected_item())
                    self.status_message = f"Moved '{sel.title}' to Trash."
                self._update_folder_counts()
            return self, None

        if isinstance(msg, MultiSplitterResizeMsg):
            sizes_str = ", ".join(f"{sz}ch" for sz in msg.sizes)
            self.status_message = f"Splitter resized: [{sizes_str}]"
            return self, None

        # ---------------- MOUSE ROUTING ----------------
        if isinstance(msg, MouseMsg):
            # 1. If splitter divider is being dragged, lock mouse to splitter
            if self.splitter.is_dragging:
                self.splitter, sp_cmd = self.splitter.update(msg)
                if sp_cmd:
                    cmds.append(sp_cmd)
                return self, batch(*cmds) if cmds else None

            # 2. If MenuBar is open, forward all mouse events to it (dropdown or outside click)
            if self.menu_bar.is_open:
                self.menu_bar, m_cmd = self.menu_bar.update(msg)
                if m_cmd:
                    cmds.append(m_cmd)
                return self, batch(*cmds) if cmds else None

            # 3. Top Row (y == 0): MenuBar top click / hover
            if msg.y == 0:
                self.menu_bar, m_cmd = self.menu_bar.update(msg)
                if m_cmd:
                    cmds.append(m_cmd)
                return self, batch(*cmds) if cmds else None

            # 4. Bottom Row (y == self.height - 1): Interactive Status Bar Buttons
            if msg.y == self.height - 1:
                if msg.action == MouseAction.PRESS and msg.button == MouseButton.LEFT:
                    for btn_name, x0, x1 in self._status_buttons:
                        if x0 <= msg.x < x1:
                            if btn_name == "wizard":
                                self.show_wizard = True
                                self.wizard.current_step = 0
                                self.wizard_input_name.focus()
                                self.status_message = "Account Setup Wizard opened."
                                return self, None
                            elif btn_name == "equalize":
                                cmd = self.splitter.set_ratios([1.0 / 3, 1.0 / 3, 1.0 / 3])
                                if cmd:
                                    cmds.append(cmd)
                                self.status_message = "Layout split ratios equalized to 33% / 33% / 33%."
                                return self, batch(*cmds) if cmds else None
                            elif btn_name == "exit":
                                return self, quit_app()
                return self, None

        # Forward key events to MenuBar if menu key triggered
        if self.menu_bar.is_open or (
            isinstance(msg, KeyMsg)
            and (msg.key.alt or str(msg.key).lower() in ("f10", "menu"))
        ):
            self.menu_bar, m_cmd = self.menu_bar.update(msg)
            if m_cmd:
                cmds.append(m_cmd)
            return self, batch(*cmds) if cmds else None

        # Forward remaining events to MultiSplitter (which delegates to child panes)
        self.splitter, sp_cmd = self.splitter.update(msg)
        if sp_cmd:
            cmds.append(sp_cmd)

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        # 1. Top Application Menu Bar
        top_bar = self.menu_bar.view()

        # 2. Main 3-Pane MultiSplitter
        main_view = self.splitter.view()

        # 3. Bottom Status Bar with Clickable Buttons
        status_style = Style().background("#181825").foreground("#A6ADC8")
        btn_s = Style().bold(True).background("#313244").foreground("#CDD6F4")

        left_text = f" {self.status_message}"

        # Interactive status bar buttons on the right
        btn1 = "[ 🧙 New Account ]"
        btn2 = "[ ⚖️ Equalize ]"
        btn3 = "[ ✖ Exit ]"
        right_rendered = f"{btn_s.render(btn1)} {btn_s.render(btn2)} {btn_s.render(btn3)} "

        right_w = len(btn1) + 1 + len(btn2) + 1 + len(btn3) + 1
        pad = max(1, self.width - len(left_text) - right_w)

        # Store button hit bounds
        start_r = len(left_text) + pad
        self._status_buttons = [
            ("wizard", start_r, start_r + len(btn1)),
            ("equalize", start_r + len(btn1) + 1, start_r + len(btn1) + 1 + len(btn2)),
            (
                "exit",
                start_r + len(btn1) + 1 + len(btn2) + 1,
                start_r + len(btn1) + 1 + len(btn2) + 1 + len(btn3),
            ),
        ]

        bottom_bar = status_style.render(f"{left_text}{' ' * pad}") + right_rendered

        screen = join_vertical(top_bar, main_view, bottom_bar)

        # 4. Composite MenuBar Dropdown Overlay (if open)
        if self.menu_bar.is_open:
            screen = self.menu_bar.render_overlay(screen)

        # 5. Composite Wizard Modal Overlay (if open)
        if self.show_wizard:
            wizard_view = self.wizard.view()
            screen = place_overlay(screen, wizard_view, center=True, dim_backdrop=True)

        return screen


def main() -> None:
    app = DesktopShowcaseApp()
    program = Program(app, alt_screen=True, mouse=True)
    program.run()


if __name__ == "__main__":
    main()

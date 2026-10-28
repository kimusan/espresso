#!/usr/bin/env python3
"""Example 19: Desktop Application Beans Showcase.

Demonstrates all four new core Beans working seamlessly together in a desktop client layout:
1. MenuBar & DropdownMenu (Top menu with mnemonics, hotkeys, cascading dropdowns, overlays)
2. MultiSplitter (3-pane resizable layout with draggable dividers and proportional scaling)
3. CardList (Two-line email/commit information list with badges, tree nesting, and smooth scroll)
4. Wizard (Multi-step guided setup flow with validation, progress indicator, and modal overlay)
"""

from __future__ import annotations

import sys
from pathlib import Path

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


SAMPLE_EMAILS = [
    CardItem(
        id="m1",
        title="Linus Torvalds",
        subtitle="[GIT PULL] Linux 6.13 x86 architecture fixes and microcode updates",
        badge_text="10:42 AM",
        glyphs="★",
        is_unread=True,
        data={
            "from": "Linus Torvalds <torvalds@linux-foundation.org>",
            "to": "Linux Kernel Mailing List <linux-kernel@vger.kernel.org>",
            "date": "Today, 10:42 AM",
            "subject": "[GIT PULL] Linux 6.13 x86 architecture fixes",
            "body": (
                "Please pull the latest x86 fixes for 6.13-rc5 from:\n\n"
                "  git://git.kernel.org/pub/scm/linux/kernel/git/tip/tip.git x86-urgent\n\n"
                "Notable changes:\n"
                " - Fix microcode patch loader memory leak\n"
                " - Correct page table isolation fault on older AMD Zen CPUs\n"
                " - Clean up TSC synchronization warning on hypervisors"
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
            "from": "Greg Kroah-Hartman <gregkh@linuxfoundation.org>",
            "to": "Linus Torvalds <torvalds@linux-foundation.org>",
            "date": "Today, 11:15 AM",
            "subject": "Re: [GIT PULL] Linux 6.13 x86 architecture fixes",
            "body": (
                "Pulled and queued for the stable tree review cycle as well.\n"
                "All CI tests in kernel-build farm passed without regression."
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
            "from": "Peter Zijlstra <peterz@infradead.org>",
            "to": "Greg Kroah-Hartman <gregkh@linuxfoundation.org>",
            "date": "Today, 11:30 AM",
            "subject": "Re: [GIT PULL] Benchmark numbers on Zen 4",
            "body": (
                "Scheduler benchmark numbers showed 0.4% speedup on hackbench\n"
                "after the microcode loading fix."
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
]


class FolderTreePane(Model):
    """Left pane: Account & folder tree list."""

    def __init__(self) -> None:
        self.width = 20
        self.height = 20
        self.selected_folder = "Inbox"
        self.folders = [
            ("📥 Inbox", 2),
            ("⭐ Starred", 1),
            ("📤 Sent", 0),
            ("📝 Drafts", 0),
            ("📦 Archive", 0),
            ("🗑️ Trash", 0),
        ]

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[FolderTreePane, Cmd | None]:
        return self, None

    def view(self) -> str:
        border_s = Style().foreground("#45475A")
        header_s = Style().bold(True).foreground("#89B4FA")
        sel_s = Style().bold(True).background("#313244").foreground("#CDD6F4")
        item_s = Style().foreground("#A6ADC8")
        unread_s = Style().bold(True).foreground("#F38BA8")

        lines: list[str] = [
            header_s.render(" Folders"),
            border_s.render("─" * max(4, self.width)),
        ]

        for name, unread in self.folders:
            is_active = self.selected_folder in name
            tag = f" ({unread})" if unread > 0 else ""
            raw_text = f" {name}{tag}"
            pad = max(0, self.width - len(raw_text))

            if is_active:
                row = sel_s.render(f"{raw_text}{' ' * pad}")
            else:
                row = item_s.render(f"{raw_text}{' ' * pad}")
            lines.append(row)

        while len(lines) < self.height:
            lines.append(" " * self.width)

        return "\n".join(lines[: self.height])


class MessageDetailPane(Model):
    """Right pane: Email message reader with headers and body."""

    def __init__(self, message: CardItem | None = None) -> None:
        self.width = 40
        self.height = 20
        self.message = message

    def set_size(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def set_message(self, message: CardItem | None) -> None:
        self.message = message

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[MessageDetailPane, Cmd | None]:
        return self, None

    def view(self) -> str:
        border_s = Style().foreground("#45475A")
        header_label_s = Style().bold(True).foreground("#89B4FA")
        header_val_s = Style().foreground("#CDD6F4")
        body_s = Style().foreground("#BAC2DE")

        if not self.message or not self.message.data:
            empty_msg = Style().italic(True).foreground("#6C7086").render("  No message selected")
            lines = [empty_msg]
            while len(lines) < self.height:
                lines.append(" " * self.width)
            return "\n".join(lines[: self.height])

        data = self.message.data
        lines: list[str] = [
            f" {header_label_s.render('Subject:')} {header_val_s.render(data.get('subject', ''))}",
            f" {header_label_s.render('From:')}    {header_val_s.render(data.get('from', ''))}",
            f" {header_label_s.render('To:')}      {header_val_s.render(data.get('to', ''))}",
            f" {header_label_s.render('Date:')}    {header_val_s.render(data.get('date', ''))}",
            border_s.render("─" * max(4, self.width)),
        ]

        body_raw = data.get("body", "").split("\n")
        for b_line in body_raw:
            lines.append(f" {body_s.render(b_line)}")

        while len(lines) < self.height:
            lines.append(" " * self.width)

        return "\n".join(lines[: self.height])


class CredentialsForm(Model):
    """Wizard step 2 form container managing Tab focus across text fields."""

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
        if isinstance(msg, KeyMsg):
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
            Style().foreground("#6C7086").render("  [Tab] Switch Field   [Enter] Advance Step"),
        )


class DesktopShowcaseApp(Model):
    """Main desktop application coordinating MenuBar, MultiSplitter, CardList, and Wizard."""

    def __init__(self) -> None:
        self.width = 100
        self.height = 28
        self.status_message = "Ready. Press F10 or Alt+F for Menu, 'w' for Wizard, 'q' to Quit."
        self.show_wizard = False

        # 1. MenuBar
        self.menu_bar = MenuBar(
            categories=[
                MenuCategory(
                    id="file",
                    label="File",
                    mnemonic="f",
                    items=[
                        MenuItem(id="new_account", label="New Account Wizard", shortcut="w"),
                        MenuItem(id="import", label="Import Mbox...", shortcut="Ctrl+I"),
                        MenuItem(id="sep1", label="", is_separator=True),
                        MenuItem(id="exit", label="Exit Application", shortcut="q"),
                    ],
                ),
                MenuCategory(
                    id="edit",
                    label="Edit",
                    mnemonic="e",
                    items=[
                        MenuItem(id="mark_read", label="Mark as Read", shortcut="m"),
                        MenuItem(id="toggle_star", label="Toggle Star", shortcut="s"),
                        MenuItem(id="archive", label="Archive Message", shortcut="e"),
                    ],
                ),
                MenuCategory(
                    id="view",
                    label="View",
                    mnemonic="v",
                    items=[
                        MenuItem(id="equalize_split", label="Equalize 3-Pane Split", shortcut="="),
                        MenuItem(id="focus_next_pane", label="Cycle Splitter Divider", shortcut="Tab"),
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
            right_status="v1.2.0 ",
        )

        # 2. Panes
        self.folder_pane = FolderTreePane()
        self.card_list = CardList(
            items=SAMPLE_EMAILS,
            selected_index=0,
            width=40,
            height=20,
        )
        self.detail_pane = MessageDetailPane(message=self.card_list.get_selected_item())

        # 3. MultiSplitter (3 Panes: Folders, Message List, Reading Pane)
        self.splitter = MultiSplitter(
            panes=[self.folder_pane, self.card_list, self.detail_pane],
            ratios=[0.20, 0.40, 0.40],
            min_sizes=[16, 28, 28],
            orientation=SplitterOrientation.HORIZONTAL,
            width=self.width,
            height=self.height - 2,  # reserve top bar and bottom status
            offset_y=1,
        )

        # 4. Wizard (Multi-step account setup flow)
        self.wizard_input_name = TextInput(placeholder="Jane Doe", prompt="Full Name:     ")
        self.wizard_input_email = TextInput(placeholder="jane@example.com", prompt="Email Address: ")
        self.wizard_input_server = TextInput(placeholder="imap.example.com", prompt="IMAP Server:   ")
        self.credentials_form = CredentialsForm(
            self.wizard_input_name, self.wizard_input_email, self.wizard_input_server
        )

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
                    content="1. Fastmail (IMAP SSL / SMTP STARTTLS)\n2. Gmail / Google Workspace\n3. Self-hosted Dovecot / Postfix",
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
                    content="✔ TLS 1.3 enforced (Strict Certificate Pinning)\n✔ Ed25519 OpenPGP encryption key pair generated\n✔ ManageSieve server-side filtering enabled",
                ),
            ],
            width=72,
            height=16,
            allow_cancel=True,
        )

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
            if isinstance(msg, MouseMsg) and msg.action == MouseAction.PRESS and self.wizard.allow_cancel:
                if msg.x < wiz_x or msg.x >= wiz_x + self.wizard.width or msg.y < wiz_y or msg.y >= wiz_y + self.wizard.height:
                    self.show_wizard = False
                    self.status_message = "Account configuration wizard cancelled."
                    return self, None

            self.wizard, w_cmd = self.wizard.update(msg)
            if w_cmd:
                cmds.append(w_cmd)
            return self, batch(*cmds) if cmds else None

        # MenuBar active or shortcuts
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

        # Process MenuBar events
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
                    self.status_message = f"Marked '{sel.title}' as read."
            elif msg.item_id == "toggle_star":
                sel = self.card_list.get_selected_item()
                if sel:
                    sel.glyphs = "" if sel.glyphs == "★" else "★"
                    self.status_message = f"Toggled star for '{sel.title}'."
            else:
                self.status_message = f"Menu selected: {msg.category_id} -> {msg.item_id}"
            return self, batch(*cmds) if cmds else None

        # Process CardList selection events
        if isinstance(msg, CardSelectMsg):
            self.detail_pane.set_message(msg.item)
            self.status_message = f"Selected: {msg.item.title} — {msg.item.subtitle[:40]}..."
            return self, None

        if isinstance(msg, CardActivateMsg):
            self.status_message = f"Activated message from {msg.item.title}!"
            return self, None

        if isinstance(msg, MultiSplitterResizeMsg):
            sizes_str = ", ".join(f"{sz}ch" for sz in msg.sizes)
            self.status_message = f"Splitter resized: [{sizes_str}]"
            return self, None

        # Forward to MenuBar if menu is open or key is menu-related
        if self.menu_bar.is_open or (isinstance(msg, KeyMsg) and (msg.key.alt or str(msg.key).lower() in ("f10", "menu"))):
            self.menu_bar, m_cmd = self.menu_bar.update(msg)
            if m_cmd:
                cmds.append(m_cmd)
            return self, batch(*cmds) if cmds else None

        # Forward mouse events: menu bar top click vs splitter panes
        if isinstance(msg, MouseMsg) and msg.y == 0:
            self.menu_bar, m_cmd = self.menu_bar.update(msg)
            if m_cmd:
                cmds.append(m_cmd)
            return self, batch(*cmds) if cmds else None

        # Forward remaining events to MultiSplitter
        self.splitter, sp_cmd = self.splitter.update(msg)
        if sp_cmd:
            cmds.append(sp_cmd)

        return self, batch(*cmds) if cmds else None

    def view(self) -> str:
        # 1. Top Application Menu Bar
        top_bar = self.menu_bar.view()

        # 2. Main 3-Pane MultiSplitter
        main_view = self.splitter.view()

        # 3. Bottom Status Bar
        status_style = Style().background("#181825").foreground("#A6ADC8")
        status_text = f" {self.status_message}"
        pad = max(0, self.width - len(status_text))
        bottom_bar = status_style.render(f"{status_text}{' ' * pad}")

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
    program = Program(app)
    program.run()


if __name__ == "__main__":
    main()

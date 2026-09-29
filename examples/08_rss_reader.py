#!/usr/bin/env python3
"""Example 8: Fullscreen Multi-Panel RSS Reader (schulz.dk).

Showcases an interactive, responsive 3-panel terminal application:
- Left Panel: Article Feed list with date and title, navigable via Up/Down or j/k.
- Center Panel: Story Reader Viewport with styled headers, tags, and word-wrapped body.
- Right Panel: Inspector with post metadata, reading time, tags, and keybinding guide.
- Asynchronous feed fetching from https://schulz.dk/feed/ with animated loading spinner.
- Offline fallback items ensuring reliable display even without network access.
- Active panel focus switching (Tab) with vibrant TrueColor border highlighting.
"""

from __future__ import annotations

import email.utils
import html
import re
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
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
from espresso.beans import DOTS, Spinner, SpinnerTickMsg, Viewport
from espresso.crema import (
    Align,
    ROUNDED_BORDER,
    Style,
    join_horizontal,
    join_vertical,
    string_width,
    truncate_ansi,
    wrap_ansi,
)

FEED_URL = "https://schulz.dk/feed/"


# ---------------------------------------------------------------------------
# Data Models & Fallback Content
# ---------------------------------------------------------------------------


@dataclass
class RSSItem:
    """Parsed RSS article item."""

    title: str
    link: str
    pub_date_raw: str
    pub_date_short: str
    pub_date_full: str
    author: str
    categories: list[str]
    description: str
    word_count: int
    read_time_min: int


# Pre-cached fallback articles from schulz.dk ensuring the demo works offline
FALLBACK_ARTICLES: list[RSSItem] = [
    RSSItem(
        title="Linux Snippets #14: Find the Firewall Rule That Ate Your Packet",
        link="https://schulz.dk/2026/09/16/linux-snippets-14-find-the-firewall-rule-that-ate-your-packet/",
        pub_date_raw="Wed, 16 Sep 2026 21:45:47 +0000",
        pub_date_short="16 Sep",
        pub_date_full="September 16, 2026 (21:45 UTC)",
        author="Kim Schulz",
        categories=["Linux", "Misc", "Technical", "Iptables", "Nftables"],
        description=(
            "Somewhere inside the firewall, your packet entered a chain, followed three jumps, "
            "and was quietly sentenced to death by a rule written during an emergency in 2022. "
            "nft monitor trace lets you follow one carefully selected packet through the bureaucracy "
            "and discover exactly where policy became homicide.\n\n"
            "By setting up an nftables trace rule for specific source/destination IPs or ports, "
            "the kernel outputs trace events directly to user space. You can watch rule evaluation "
            "step by step in real time, inspect verdicts, and pinpoint drop actions instantly."
        ),
        word_count=82,
        read_time_min=1,
    ),
    RSSItem(
        title="NginXplorer: Because Spinning Up a 2GB Grafana Stack Just to Watch Nginx Logs is Madness",
        link="https://schulz.dk/2026/09/14/nginxplorer-because-spinning-up-a-2gb-grafana-stack-just-to-watch-nginx-logs-is-madness/",
        pub_date_raw="Mon, 14 Sep 2026 14:31:42 +0000",
        pub_date_short="14 Sep",
        pub_date_full="September 14, 2026 (14:31 UTC)",
        author="Kim Schulz",
        categories=["Code", "Linux", "News", "Projects", "Nginx"],
        description=(
            "It usually starts with an innocent thought on a Friday evening. You’re logged into a "
            "low-powered VPS hosting a handful of sites, you notice traffic is higher than usual, "
            "and you want to know what’s hitting your server. You open the Nginx access log with tail -f.\n\n"
            "Rows of text fly past at high speed. You try grep, awk, and sort pipelines, but it’s "
            "fragmented. You don’t need Prometheus, Loki, and Grafana eating 2GB of RAM. "
            "You just want a fast, lightweight terminal tool that turns the stream into clarity."
        ),
        word_count=94,
        read_time_min=1,
    ),
    RSSItem(
        title="Linux Snippets #13: Ask the Machine What Killed It",
        link="https://schulz.dk/2026/09/13/linux-snippets-13-ask-the-machine-what-killed-it/",
        pub_date_raw="Sun, 13 Sep 2026 12:31:00 +0000",
        pub_date_short="13 Sep",
        pub_date_full="September 13, 2026 (12:31 UTC)",
        author="Kim Schulz",
        categories=["Linux", "Misc", "Technical", "Kernel", "Systemd"],
        description=(
            "When a Linux server reboots unexpectedly in the middle of the night, standard log files "
            "often go silent right before the crash. Using systemd-pstore, kernel panic logs, and "
            "kexec/kdump, you can capture RAM artifacts and hardware error records across reboots.\n\n"
            "This guide walks through configuring persistent storage for oops reports so the machine "
            "tells you its final dying words upon coming back online."
        ),
        word_count=74,
        read_time_min=1,
    ),
    RSSItem(
        title="Linux Snippets #12: Network Namespaces Without the Headaches",
        link="https://schulz.dk/2026/09/08/linux-snippets-12-network-namespaces/",
        pub_date_raw="Tue, 08 Sep 2026 10:15:00 +0000",
        pub_date_short="08 Sep",
        pub_date_full="September 08, 2026 (10:15 UTC)",
        author="Kim Schulz",
        categories=["Linux", "Networking", "Containers", "DevOps"],
        description=(
            "Network namespaces are the fundamental isolation primitive powering Docker, Kubernetes, "
            "and WireGuard tunnels. Creating isolated routing tables, virtual ethernet (veth) pairs, "
            "and private firewall domains takes only a few ip netns commands when understood properly.\n\n"
            "Learn how to test complex network topologies and run isolated VPN clients locally without "
            "affecting your main host routing."
        ),
        word_count=68,
        read_time_min=1,
    ),
    RSSItem(
        title="Mastering Modern Terminal Productivity: The Vim and CLI Mindset",
        link="https://schulz.dk/2026/08/28/mastering-modern-terminal-productivity/",
        pub_date_raw="Fri, 28 Aug 2026 16:20:00 +0000",
        pub_date_short="28 Aug",
        pub_date_full="August 28, 2026 (16:20 UTC)",
        author="Kim Schulz",
        categories=["Vim", "Tools", "Terminal", "Productivity"],
        description=(
            "A deep dive into keyboard-first development, Unix composability, and streamlining editor "
            "workflows. Minimizing context switches between GUI windows and terminal shells creates "
            "a focused coding environment that stands the test of time.\n\n"
            "Features tips on modal editing, tmux session managers, and custom CLI automation scripts."
        ),
        word_count=58,
        read_time_min=1,
    ),
]


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FeedLoadedMsg(Msg):
    """Emitted when RSS feed fetch completes successfully."""

    items: list[RSSItem]
    feed_title: str
    duration_sec: float


@dataclass(frozen=True)
class FeedErrorMsg(Msg):
    """Emitted when RSS feed fetch encounters an error."""

    error: str
    items: list[RSSItem]


# ---------------------------------------------------------------------------
# XML / RSS Parser & Fetcher
# ---------------------------------------------------------------------------


def clean_html_text(raw_html: str) -> str:
    """Convert HTML snippet to clean terminal-friendly text."""
    if not raw_html:
        return ""
    # Replace line breaks and paragraphs with newlines
    text = re.sub(r"(?i)<br\s*/?>", "\n", raw_html)
    text = re.sub(r"(?i)</?p[^>]*>", "\n\n", text)
    text = re.sub(r"(?i)</?div[^>]*>", "\n", text)
    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Unescape HTML entities (&amp;, &quot;, &#8217;, etc.)
    text = html.unescape(text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def parse_rss_payload(xml_bytes: bytes) -> tuple[str, list[RSSItem]]:
    """Parse RSS XML into channel title and RSSItem list."""
    root = ET.fromstring(xml_bytes)
    channel_title = root.findtext("./channel/title") or "schulz.dk"

    items: list[RSSItem] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "Untitled").strip()
        link = (item.findtext("link") or "").strip()
        raw_date = (item.findtext("pubDate") or "").strip()

        # Parse date
        short_date = "Recent"
        full_date = raw_date
        try:
            dt = email.utils.parsedate_to_datetime(raw_date)
            short_date = dt.strftime("%d %b")
            full_date = dt.strftime("%B %d, %Y (%H:%M UTC)")
        except Exception:
            pass

        author = (item.findtext("{http://purl.org/dc/elements/1.1/}creator") or "Kim Schulz").strip()
        categories = [elem.text.strip() for elem in item.findall("category") if elem.text]
        if not categories:
            categories = ["Linux", "Tech"]

        desc_raw = item.findtext("description") or ""
        clean_desc = clean_html_text(desc_raw)
        words = len(clean_desc.split())
        read_time = max(1, round(words / 150))

        items.append(
            RSSItem(
                title=title,
                link=link,
                pub_date_raw=raw_date,
                pub_date_short=short_date,
                pub_date_full=full_date,
                author=author,
                categories=categories,
                description=clean_desc,
                word_count=words,
                read_time_min=read_time,
            )
        )

    return channel_title, items


def fetch_feed_cmd() -> Cmd:
    """Asynchronously fetch RSS feed in executor thread."""

    def _fetch() -> Msg:
        start_t = time.monotonic()
        try:
            req = urllib.request.Request(
                FEED_URL,
                headers={"User-Agent": "EspressoRSS/1.0 (Terminal Elm Architecture)"},
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                xml_data = resp.read()
            feed_title, items = parse_rss_payload(xml_data)
            duration = time.monotonic() - start_t
            if not items:
                return FeedErrorMsg(error="No articles found in feed", items=FALLBACK_ARTICLES)
            return FeedLoadedMsg(items=items, feed_title=feed_title, duration_sec=duration)
        except Exception as e:
            return FeedErrorMsg(error=f"Network: {e} (using offline cache)", items=FALLBACK_ARTICLES)

    return _fetch


# ---------------------------------------------------------------------------
# Application Model
# ---------------------------------------------------------------------------


class RSSReaderApp(Model):
    """Full-screen, 3-panel RSS reader TUI."""

    def __init__(self) -> None:
        self.width = 100
        self.height = 30
        self.items: list[RSSItem] = list(FALLBACK_ARTICLES)
        self.selected_idx = 0
        self.scroll_top = 0
        self.focus = "list"  # "list" or "story"
        self.loading = True
        self.status_msg = "Fetching live feed from schulz.dk..."
        self.feed_title = "schulz.dk — Linux & Systems Journal"
        self.is_offline = False

        # Beans components
        self.spinner = Spinner(DOTS, fps=12.0)
        self.viewport = Viewport(width=50, height=20)

        # Crema Styles
        self.style_badge = Style().bold(True).foreground("#FFFFFF").background("#7D56F4").padding(0, 1)
        self.style_title = Style().bold(True).foreground("#00D7D7")
        self.style_status_bar = Style().background("#222222").foreground("#CCCCCC")
        self.style_help_key = Style().bold(True).foreground("#FFA726")
        self.style_help_desc = Style().foreground("#888888")

        self._refresh_viewport()

    def init(self) -> Cmd | None:
        """Start spinner animation and initiate background feed fetch."""
        return batch(self.spinner.init(), fetch_feed_cmd())

    def _selected_item(self) -> RSSItem | None:
        if 0 <= self.selected_idx < len(self.items):
            return self.items[self.selected_idx]
        return None

    def _refresh_viewport(self) -> None:
        """Render the selected article into the center Viewport with Crema formatting."""
        item = self._selected_item()
        if not item:
            self.viewport.set_content("\033[38;2;136;136;136mNo article selected.\033[0m")
            return

        w = max(20, self.viewport.width or 48)
        content_lines: list[str] = []

        # Article Title (Bold vibrant TrueColor)
        title_styled = f"\033[1;38;2;255;121;198m{item.title}\033[0m"
        for t_line in wrap_ansi(title_styled, w).splitlines():
            content_lines.append(t_line)

        content_lines.append("")

        # Author and Publication Date
        author_part = f"\033[38;2;0;215;215m✍  {item.author}\033[0m"
        date_part = f"\033[38;2;255;170;0m📅 {item.pub_date_full}\033[0m"
        meta_line = f"{author_part}   {date_part}"
        content_lines.append(meta_line)

        # Category pills
        pill_strs = []
        for cat in item.categories:
            pill_strs.append(f"\033[48;2;40;42;54m\033[38;2;139;233;253m {cat} \033[0m")
        content_lines.append(" ".join(pill_strs))

        # Horizontal Divider
        content_lines.append("\033[38;2;68;71;90m" + ("─" * min(w, 70)) + "\033[0m")
        content_lines.append("")

        # Article Body paragraphs wrapped cleanly to viewport width
        paragraphs = item.description.split("\n\n")
        for para in paragraphs:
            wrapped = wrap_ansi(para.strip(), w)
            for w_line in wrapped.splitlines():
                content_lines.append(w_line)
            content_lines.append("")

        # Footer Source Link
        content_lines.append("\033[38;2;98;114;164m" + ("┄" * min(w, 50)) + "\033[0m")
        content_lines.append(f"\033[38;2;136;136;136mLink:\033[0m \033[4;38;2;80;250;123m{item.link}\033[0m")

        self.viewport.set_content("\n".join(content_lines))
        self.viewport.y_offset = 0

    def _calc_panel_dimensions(self) -> tuple[int, int, int, int]:
        """Calculate (w_left, w_center, w_right, content_h) based on terminal size."""
        content_h = max(8, self.height - 3)  # Reserve 1 row header, 1 row footer, 1 padding

        # Width proportions: ~28% left, ~46% center, ~26% right
        w_left = max(24, int(self.width * 0.28))
        w_right = max(22, int(self.width * 0.24))
        w_center = max(30, self.width - w_left - w_right)

        return w_left, w_center, w_right, content_h

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        match msg:
            case WindowSizeMsg(width=w, height=h):
                self.width = w
                self.height = h
                w_left, w_center, w_right, content_h = self._calc_panel_dimensions()
                self.viewport.width = max(10, w_center - 4)
                self.viewport.height = max(4, content_h - 2)
                self._refresh_viewport()
                return self, None

            case FeedLoadedMsg(items=items, feed_title=title, duration_sec=dur):
                self.items = items
                self.feed_title = title
                self.loading = False
                self.is_offline = False
                self.status_msg = f"Live Feed Updated in {dur:.2f}s ({len(items)} posts)"
                self.selected_idx = min(self.selected_idx, len(items) - 1)
                self._refresh_viewport()
                return self, None

            case FeedErrorMsg(error=err, items=items):
                self.items = items
                self.loading = False
                self.is_offline = True
                self.status_msg = f"Offline Mode: {err}"
                self._refresh_viewport()
                return self, None

            case SpinnerTickMsg() if self.loading:
                self.spinner, cmd = self.spinner.update(msg)
                return self, cmd

            case KeyMsg(key="q" | "ctrl+c"):
                return self, quit_app

            case KeyMsg(key="tab" | "shift+tab"):
                self.focus = "story" if self.focus == "list" else "list"
                return self, None

            case KeyMsg(key="r"):
                self.loading = True
                self.status_msg = "Refreshing feed from schulz.dk..."
                return self, batch(self.spinner.init(), fetch_feed_cmd())

            case MouseMsg(button=MouseButton.WHEEL_UP):
                self.viewport, _ = self.viewport.update(KeyMsg("up"))
                return self, None

            case MouseMsg(button=MouseButton.WHEEL_DOWN):
                self.viewport, _ = self.viewport.update(KeyMsg("down"))
                return self, None

            case KeyMsg():
                # Focus: Feed List Navigation
                if self.focus == "list":
                    match msg.key.name:
                        case "up" | "k":
                            if self.selected_idx > 0:
                                self.selected_idx -= 1
                                self._adjust_list_scroll()
                                self._refresh_viewport()
                            return self, None

                        case "down" | "j":
                            if self.selected_idx < len(self.items) - 1:
                                self.selected_idx += 1
                                self._adjust_list_scroll()
                                self._refresh_viewport()
                            return self, None

                        case "home" | "g":
                            self.selected_idx = 0
                            self._adjust_list_scroll()
                            self._refresh_viewport()
                            return self, None

                        case "end" | "G":
                            self.selected_idx = max(0, len(self.items) - 1)
                            self._adjust_list_scroll()
                            self._refresh_viewport()
                            return self, None

                        case "enter" | "right" | "l":
                            self.focus = "story"
                            return self, None

                # Focus: Story Viewport Scrolling
                elif self.focus == "story":
                    match msg.key.name:
                        case "left" | "h" | "esc":
                            self.focus = "list"
                            return self, None
                        case _:
                            self.viewport, cmd = self.viewport.update(msg)
                            return self, cmd

        return self, None

    def _adjust_list_scroll(self) -> None:
        """Ensure selected article row remains visible inside the left panel."""
        _, _, _, content_h = self._calc_panel_dimensions()
        visible_rows = max(1, content_h - 2)

        if self.selected_idx < self.scroll_top:
            self.scroll_top = self.selected_idx
        elif self.selected_idx >= self.scroll_top + visible_rows:
            self.scroll_top = self.selected_idx - visible_rows + 1

    # -----------------------------------------------------------------------
    # View Rendering
    # -----------------------------------------------------------------------

    def _render_header(self) -> str:
        badge = self.style_badge.render("☕ ESPRESSO RSS")
        title = self.style_title.render(f" {self.feed_title}")

        if self.loading:
            status = f"\033[38;2;255;170;0m{self.spinner.view()}\033[0m"
        elif self.is_offline:
            status = "\033[38;2;255;85;85m● Offline Cache (schulz.dk)\033[0m"
        else:
            status = "\033[38;2;80;250;123m● Live Feed (schulz.dk)\033[0m"

        left_part = f"{badge}{title}"
        bar_w = self.width
        spacing = max(1, bar_w - string_width(left_part) - string_width(status) - 2)
        return f" {left_part}{' ' * spacing}{status} "

    def _render_left_panel(self, width: int, height: int) -> str:
        """Render Left Panel: Article Feed List."""
        inner_w = max(10, width - 2)
        visible_rows = max(1, height - 2)

        lines: list[str] = []
        date_col_w = 7
        title_col_w = max(6, inner_w - date_col_w - 4)

        end_idx = min(len(self.items), self.scroll_top + visible_rows)
        for i in range(self.scroll_top, end_idx):
            item = self.items[i]
            is_selected = i == self.selected_idx

            cursor = "▸" if is_selected else " "
            d_str = item.pub_date_short.ljust(date_col_w)
            t_str = truncate_ansi(item.title, title_col_w, tail="…")
            t_padded = t_str + (" " * max(0, title_col_w - string_width(t_str)))

            if is_selected:
                if self.focus == "list":
                    row_content = f"{cursor} \033[1;38;2;255;255;255m\033[48;2;125;86;244m{d_str} │ {t_padded}\033[0m"
                else:
                    row_content = f"{cursor} \033[1;38;2;0;230;118m\033[48;2;40;42;54m{d_str} │ {t_padded}\033[0m"
            else:
                row_content = f"  \033[38;2;136;136;136m{d_str}\033[0m \033[38;2;68;71;90m│\033[0m {t_padded}"

            lines.append(truncate_ansi(row_content, inner_w))

        # Fill remaining blank rows if feed is short
        while len(lines) < visible_rows:
            lines.append(" " * inner_w)

        is_active = self.focus == "list"
        border_col = "#7D56F4" if is_active else "#444444"
        title_tag = f" 📰 Articles ({len(self.items)}) " + ("\033[1;38;2;125;86;244m[ACTIVE]\033[0m " if is_active else "")

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(border_col)
            .border_title(title_tag)
            .width(inner_w)
            .render("\n".join(lines))
        )

    def _render_center_panel(self, width: int, height: int) -> str:
        """Render Center Panel: Story Viewport."""
        inner_w = max(10, width - 2)
        inner_h = max(2, height - 2)

        is_active = self.focus == "story"
        border_col = "#00E676" if is_active else "#444444"

        # Percentage indicator
        scroll_pct = self.viewport.scroll_percent
        pct_tag = f"{int(scroll_pct * 100)}%" if scroll_pct is not None else "Top"
        title_tag = f" 📖 Story Reader [{pct_tag}] " + ("\033[1;38;2;0;230;118m[ACTIVE]\033[0m " if is_active else "")

        # Render viewport content
        viewport_lines = self.viewport.view().splitlines()
        # Ensure exact height matching
        padded_vp_lines = list(viewport_lines[:inner_h])
        while len(padded_vp_lines) < inner_h:
            padded_vp_lines.append(" " * inner_w)

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground(border_col)
            .border_title(title_tag)
            .width(inner_w)
            .render("\n".join(padded_vp_lines))
        )

    def _render_right_panel(self, width: int, height: int) -> str:
        """Render Right Panel: Post Details, Tags & Keybindings Help."""
        inner_w = max(10, width - 2)
        inner_h = max(2, height - 2)

        lines: list[str] = []
        item = self._selected_item()

        def add_line(text: str) -> None:
            lines.append(truncate_ansi(text, inner_w))

        # --- SECTION: POST INSPECTOR ---
        add_line("\033[1;38;2;255;184;108mARTICLE DETAILS\033[0m")
        if item:
            add_line(f"• \033[1mAuthor:\033[0m   {item.author}")
            add_line(f"• \033[1mPublished:\033[0m{item.pub_date_short}")
            add_line(f"• \033[1mLength:\033[0m   ~{item.word_count} words ({item.read_time_min}m read)")
            add_line(f"• \033[1mSource:\033[0m   schulz.dk")
        else:
            add_line("• No article selected")

        add_line("")

        # --- SECTION: CATEGORIES / TAGS ---
        add_line("\033[1;38;2;255;184;108mCATEGORIES\033[0m")
        if item and item.categories:
            for cat in item.categories[:4]:
                add_line(f"  \033[38;2;0;215;215m#\033[0m {cat}")
        else:
            add_line("  (none)")

        add_line("")

        # --- SECTION: NAVIGATION CHEAT SHEET ---
        add_line("\033[1;38;2;255;184;108mKEYBOARD SHORTCUTS\033[0m")
        shortcuts = [
            ("Tab", "Switch focus"),
            ("↑/↓, j/k", "Select / Scroll"),
            ("PgUp/Dn", "Page scroll"),
            ("r", "Reload feed"),
            ("q, Esc", "Quit app"),
        ]
        for key, desc in shortcuts:
            add_line(f" \033[1;38;2;255;121;198m{key:<8}\033[0m \033[38;2;136;136;136m{desc}\033[0m")

        # Fill remaining rows
        while len(lines) < inner_h:
            lines.append(" " * inner_w)

        return (
            Style()
            .border(ROUNDED_BORDER)
            .border_foreground("#FFA726")
            .border_title(" ℹ️ Info & Help ")
            .width(inner_w)
            .render("\n".join(lines[:inner_h]))
        )

    def _render_footer(self) -> str:
        """Render bottom status bar."""
        focus_badge = (
            "\033[1;48;2;125;86;244m\033[38;2;255;255;255m FOCUS: FEED LIST \033[0m"
            if self.focus == "list"
            else "\033[1;48;2;0;230;118m\033[38;2;0;0;0m FOCUS: STORY READER \033[0m"
        )
        msg_text = f" {self.status_msg}"
        hints = "\033[38;2;136;136;136m[Tab] Focus  [↑/↓,j/k] Navigate  [r] Refresh  [q] Quit\033[0m "

        bar_w = self.width
        left = f"{focus_badge} {msg_text}"
        spacing = max(1, bar_w - string_width(left) - string_width(hints))
        content = f"{left}{' ' * spacing}{hints}"

        return self.style_status_bar.render(truncate_ansi(content, bar_w))

    def view(self) -> str:
        w_left, w_center, w_right, content_h = self._calc_panel_dimensions()

        header = self._render_header()
        p_left = self._render_left_panel(w_left, content_h)
        p_center = self._render_center_panel(w_center, content_h)
        p_right = self._render_right_panel(w_right, content_h)
        footer = self._render_footer()

        panels_row = join_horizontal(Align.TOP, p_left, p_center, p_right)
        return join_vertical(Align.LEFT, header, panels_row, footer)


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = RSSReaderApp()
    p = Program(app, alt_screen=True, mouse=True)
    p.run()

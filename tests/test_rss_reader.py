"""Unit tests for Example 08 RSS Reader data models, parsing, and interaction."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add src/ and examples/ to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

import importlib
rss_mod = importlib.import_module("08_rss_reader")

from espresso import KeyMsg, WindowSizeMsg, quit_app
from espresso.crema.width import string_width


SAMPLE_RSS_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>schulz.dk</title>
    <link>https://schulz.dk</link>
    <description>Kim Schulz personal site</description>
    <item>
      <title>Linux Snippets #14: Find the Firewall Rule That Ate Your Packet</title>
      <link>https://schulz.dk/article-14</link>
      <pubDate>Wed, 16 Sep 2026 21:45:47 +0000</pubDate>
      <dc:creator>Kim Schulz</dc:creator>
      <category>Linux</category>
      <category>Iptables</category>
      <description>&lt;p&gt;Somewhere inside the firewall, your packet entered a chain... &amp;amp; died.&lt;/p&gt;</description>
    </item>
    <item>
      <title>NginXplorer: Watch Nginx Logs</title>
      <link>https://schulz.dk/article-nginx</link>
      <pubDate>Mon, 14 Sep 2026 14:31:42 +0000</pubDate>
      <dc:creator>Kim Schulz</dc:creator>
      <category>Code</category>
      <description>&lt;p&gt;You open the Nginx access log with tail -f.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>
"""


class TestRSSReader(unittest.TestCase):
    """Test suite for RSS Reader data parsing and application logic."""

    def test_clean_html_text(self) -> None:
        raw = "<p>First paragraph.</p><br/><p>Second &amp; final &quot;paragraph&quot;.</p>"
        cleaned = rss_mod.clean_html_text(raw)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("</p>", cleaned)
        self.assertIn("First paragraph.", cleaned)
        self.assertIn('Second & final "paragraph".', cleaned)

    def test_parse_rss_payload(self) -> None:
        title, items = rss_mod.parse_rss_payload(SAMPLE_RSS_XML)
        self.assertEqual(title, "schulz.dk")
        self.assertEqual(len(items), 2)

        first = items[0]
        self.assertEqual(first.title, "Linux Snippets #14: Find the Firewall Rule That Ate Your Packet")
        self.assertEqual(first.author, "Kim Schulz")
        self.assertEqual(first.pub_date_short, "16 Sep")
        self.assertEqual(first.categories, ["Linux", "Iptables"])
        self.assertIn("Somewhere inside the firewall", first.description)
        self.assertIn("& died.", first.description)

        second = items[1]
        self.assertEqual(second.pub_date_short, "14 Sep")
        self.assertEqual(second.categories, ["Code"])

    def test_app_initialization_and_fallback(self) -> None:
        app = rss_mod.RSSReaderApp()
        self.assertGreaterEqual(len(app.items), 5)
        self.assertEqual(app.selected_idx, 0)
        self.assertEqual(app.focus, "list")
        self.assertTrue(app.loading)

    def test_app_window_resize(self) -> None:
        app = rss_mod.RSSReaderApp()
        app, _ = app.update(WindowSizeMsg(110, 32))
        self.assertEqual(app.width, 110)
        self.assertEqual(app.height, 32)

        view = app.view()
        lines = view.splitlines()
        self.assertLessEqual(len(lines), 32)
        for l in lines:
            self.assertLessEqual(string_width(l), 111)

    def test_feed_loaded_message(self) -> None:
        app = rss_mod.RSSReaderApp()
        title, items = rss_mod.parse_rss_payload(SAMPLE_RSS_XML)
        app, _ = app.update(rss_mod.FeedLoadedMsg(items=items, feed_title=title, duration_sec=0.42))

        self.assertFalse(app.loading)
        self.assertFalse(app.is_offline)
        self.assertEqual(len(app.items), 2)
        self.assertEqual(app.feed_title, "schulz.dk")
        self.assertIn("0.42s", app.status_msg)

    def test_feed_error_message_uses_fallback(self) -> None:
        app = rss_mod.RSSReaderApp()
        app, _ = app.update(rss_mod.FeedErrorMsg(error="Connection refused", items=rss_mod.FALLBACK_ARTICLES))

        self.assertFalse(app.loading)
        self.assertTrue(app.is_offline)
        self.assertIn("Offline Mode", app.status_msg)
        self.assertGreaterEqual(len(app.items), 5)

    def test_focus_toggle_and_navigation(self) -> None:
        app = rss_mod.RSSReaderApp()
        self.assertEqual(app.focus, "list")

        # Toggle to story
        app, _ = app.update(KeyMsg("tab"))
        self.assertEqual(app.focus, "story")

        # Toggle back to list
        app, _ = app.update(KeyMsg("tab"))
        self.assertEqual(app.focus, "list")

        # Navigate down/up in list
        self.assertEqual(app.selected_idx, 0)
        app, _ = app.update(KeyMsg("down"))
        self.assertEqual(app.selected_idx, 1)

        app, _ = app.update(KeyMsg("up"))
        self.assertEqual(app.selected_idx, 0)

        # Clamping at top
        app, _ = app.update(KeyMsg("up"))
        self.assertEqual(app.selected_idx, 0)

    def test_quit_key(self) -> None:
        app = rss_mod.RSSReaderApp()
        _, cmd = app.update(KeyMsg("q"))
        self.assertEqual(cmd, quit_app)


if __name__ == "__main__":
    unittest.main()

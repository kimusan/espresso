"""Unit tests for StatusBar, Metric, and NavStack components."""

from __future__ import annotations

import unittest

from espresso import Cmd, KeyMsg, Model, Msg
from espresso.beans import (
    LayoutDirection,
    Metric,
    MetricGroup,
    MetricLayout,
    MetricTrend,
    NavEntry,
    NavPopMsg,
    NavPushMsg,
    NavStack,
    StatusBar,
    StatusSection,
)
from espresso.crema import string_width, strip_ansi


class TestStatusBar(unittest.TestCase):
    def test_statusbar_full_layout_dimensions(self) -> None:
        sb = StatusBar(
            left=["NORMAL", "git:main"],
            center=["doc.md"],
            right=["utf-8", "Ln 12, Col 4"],
            width=80,
        )
        rendered = sb.view()
        self.assertEqual(string_width(rendered), 80)
        self.assertIn("NORMAL", rendered)
        self.assertIn("git:main", rendered)
        self.assertIn("doc.md", rendered)
        self.assertIn("Ln 12, Col 4", rendered)

    def test_statusbar_narrow_truncation(self) -> None:
        sb = StatusBar(
            left=[StatusSection("CRITICAL", priority=5), StatusSection("extra", priority=1)],
            center=["huge centered title"],
            right=[StatusSection("OK", priority=4)],
            width=25,
        )
        rendered = sb.view()
        self.assertEqual(string_width(rendered), 25)
        self.assertIn("CRITICAL", rendered)


class TestMetric(unittest.TestCase):
    def test_metric_card_render(self) -> None:
        m = Metric(
            label="Total Requests",
            value="14,290",
            unit="req/s",
            delta="+12%",
            trend=MetricTrend.UP,
            width=28,
        )
        card = m.render_card()
        self.assertIn("TOTAL REQUESTS", card)
        self.assertIn("14,290", card)
        self.assertIn("+12%", card)
        self.assertIn("▲", card)

    def test_metric_group_layouts(self) -> None:
        m1 = Metric("CPU", "42%", delta="+2%", trend=MetricTrend.UP)
        m2 = Metric("MEM", "1.8 GB", delta="-5%", trend=MetricTrend.DOWN)
        group = MetricGroup([m1, m2], layout=MetricLayout.LIST, width=40)
        list_str = group.view()
        self.assertIn("CPU", list_str)
        self.assertIn("MEM", list_str)

        group_tags = MetricGroup([m1, m2], layout=MetricLayout.TAG)
        tags_str = group_tags.view()
        self.assertIn("CPU: 42%", tags_str)
        self.assertIn("MEM: 1.8 GB", tags_str)


class DummyViewModel(Model):
    def __init__(self, name: str) -> None:
        self.name = name
        self.key_received = ""

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[Model, Cmd | None]:
        if isinstance(msg, KeyMsg):
            self.key_received = str(msg.key)
        return self, None

    def view(self) -> str:
        return f"View: {self.name} (last key: {self.key_received})"


class TestNavStack(unittest.TestCase):
    def test_navstack_push_pop_and_routing(self) -> None:
        home = DummyViewModel("Home")
        nav = NavStack(initial_title="Dashboard", initial_model=home)

        self.assertEqual(nav.depth, 1)
        self.assertEqual(strip_ansi(nav.breadcrumbs_view()), "Dashboard")

        # Push Category
        cat = DummyViewModel("Catalog")
        push_cmd = nav.push("Catalog", cat)
        self.assertIsNotNone(push_cmd)
        msg = push_cmd()
        self.assertIsInstance(msg, NavPushMsg)
        self.assertEqual(msg.title, "Catalog")
        self.assertEqual(nav.depth, 2)
        self.assertIn("Dashboard", nav.breadcrumbs_view())
        self.assertIn("Catalog", nav.breadcrumbs_view())

        # Delegate update to top model
        nav, _ = nav.update(KeyMsg("x"))
        self.assertEqual(cat.key_received, "x")
        self.assertEqual(home.key_received, "")  # Unmodified

        # Pop
        popped_model, pop_cmd = nav.pop()
        self.assertIs(popped_model, cat)
        self.assertEqual(nav.depth, 1)
        self.assertEqual(strip_ansi(nav.breadcrumbs_view()), "Dashboard")

    def test_navstack_auto_pop_on_back(self) -> None:
        v1 = DummyViewModel("V1")
        v2 = DummyViewModel("V2")
        nav = NavStack("V1", v1)
        nav.push("V2", v2)
        self.assertEqual(nav.depth, 2)

        # Send Esc -> auto pop
        nav, pop_cmd = nav.update(KeyMsg("esc"))
        self.assertEqual(nav.depth, 1)
        self.assertIs(nav.current_model, v1)


if __name__ == "__main__":
    unittest.main()

"""Navigation stack and breadcrumbs trail component.

Modeled after KevM/bubbleo.
Provides hierarchical view stack routing, push/pop management, TEA message
delegation to the active top model, and breadcrumbs trail rendering.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.layout import join_vertical
from espresso.crema.style import Align, Style
from espresso.crema.width import string_width


@dataclass
class NavEntry:
    """An entry on the navigation stack."""

    title: str
    model: Model
    tag: str = ""


@dataclass(frozen=True)
class NavPushMsg(Msg):
    """Message emitted when a view is pushed onto the NavStack."""

    title: str
    depth: int


@dataclass(frozen=True)
class NavPopMsg(Msg):
    """Message emitted when a view is popped from the NavStack."""

    popped_title: str
    current_title: str
    depth: int


class NavStack(Model):
    """A TEA component managing a stack of sub-models with breadcrumbs navigation."""

    def __init__(
        self,
        initial_title: str = "Home",
        initial_model: Model | None = None,
        auto_pop_on_back: bool = True,
        show_breadcrumbs: bool = True,
        separator: str = " › ",
    ) -> None:
        self.stack: list[NavEntry] = []
        self.auto_pop_on_back = auto_pop_on_back
        self.show_breadcrumbs = show_breadcrumbs
        self.separator = separator

        if initial_model is not None:
            self.stack.append(NavEntry(title=initial_title, model=initial_model))

    @property
    def depth(self) -> int:
        return len(self.stack)

    @property
    def current_entry(self) -> NavEntry | None:
        return self.stack[-1] if self.stack else None

    @property
    def current_model(self) -> Model | None:
        return self.stack[-1].model if self.stack else None

    def push(self, title: str, model: Model, tag: str = "") -> Cmd | None:
        """Push a new model onto the navigation stack."""
        self.stack.append(NavEntry(title=title, model=model, tag=tag))
        depth = len(self.stack)

        def _emit_push() -> Msg:
            return NavPushMsg(title=title, depth=depth)

        # Also trigger model.init() if present
        init_cmd = model.init()
        if init_cmd is not None:
            from espresso.core.tea import batch
            return batch(_emit_push, init_cmd)
        return _emit_push

    def pop(self) -> tuple[Model | None, Cmd | None]:
        """Pop the current model from the stack if depth > 1."""
        if len(self.stack) <= 1:
            return None, None

        popped = self.stack.pop()
        current = self.stack[-1]
        depth = len(self.stack)

        def _emit_pop() -> Msg:
            return NavPopMsg(
                popped_title=popped.title,
                current_title=current.title,
                depth=depth,
            )

        return popped.model, _emit_pop

    def breadcrumbs_view(self) -> str:
        """Render the breadcrumbs trail (e.g. Home › Category › Detail)."""
        if not self.stack:
            return ""

        parts: list[str] = []
        n = len(self.stack)

        for i, entry in enumerate(self.stack):
            is_active = (i == n - 1)
            if is_active:
                part = Style().bold(True).foreground("#00E5FF").render(entry.title)
            else:
                part = Style().foreground("#8888AA").render(entry.title)
            parts.append(part)

        sep = Style().foreground("#555577").render(self.separator)
        return sep.join(parts)

    def init(self) -> Cmd | None:
        if self.current_model is not None:
            return self.current_model.init()
        return None

    def update(self, msg: Msg) -> tuple[NavStack, Cmd | None]:
        """Delegate message to current top model or handle back navigation."""
        if not self.stack:
            return self, None

        # Check for auto back navigation
        if self.auto_pop_on_back and isinstance(msg, KeyMsg) and msg.key in ("esc", "backspace"):
            if len(self.stack) > 1:
                _, pop_cmd = self.pop()
                return self, pop_cmd

        # Delegate to active model
        active_model = self.stack[-1].model
        updated_model, cmd = active_model.update(msg)
        self.stack[-1].model = updated_model

        return self, cmd

    def view(self) -> str:
        """Render the active model, optionally prepended with breadcrumbs."""
        if not self.stack:
            return ""

        model_view = self.stack[-1].model.view()
        if self.show_breadcrumbs and len(self.stack) > 1:
            bc = self.breadcrumbs_view()
            return join_vertical(Align.LEFT, bc, "", model_view)
        return model_view

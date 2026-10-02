"""Modal stack manager for layering dialogs, popups, and screens over a base model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg
from espresso.crema.overlay import place_overlay


@dataclass(frozen=True)
class ModalCloseMsg(Msg):
    """Message instructing ModalStack to dismiss the topmost modal."""

    pass


@dataclass(frozen=True)
class ModalResultMsg(Msg):
    """Message dismissing topmost modal and returning a result payload."""

    result: Any


class ModalStack(Model):
    """A TEA controller managing layered modal models composited over a root base view."""

    def __init__(
        self,
        base_model: Model,
        auto_dismiss_on_esc: bool = True,
        dim_backdrop: bool = True,
    ) -> None:
        self.base_model = base_model
        self.modals: list[Model] = []
        self.auto_dismiss_on_esc = auto_dismiss_on_esc
        self.dim_backdrop = dim_backdrop

    @property
    def has_modals(self) -> bool:
        """True if one or more modal dialogs are currently active."""
        return len(self.modals) > 0

    @property
    def top_modal(self) -> Model | None:
        """Return the active topmost modal, or None if the stack is empty."""
        return self.modals[-1] if self.modals else None

    def push(self, modal: Model) -> None:
        """Push a new modal view onto the top of the stack."""
        self.modals.append(modal)

    def pop(self) -> Model | None:
        """Remove and return the topmost modal."""
        if self.modals:
            return self.modals.pop()
        return None

    def clear(self) -> None:
        """Dismiss all active modals."""
        self.modals.clear()

    def init(self) -> Cmd | None:
        """Initialize the base model."""
        return self.base_model.init()

    def update(self, msg: Msg) -> tuple[ModalStack, Cmd | None]:
        """Route input events to the active top modal or base model."""
        if not self.has_modals:
            self.base_model, cmd = self.base_model.update(msg)
            return self, cmd

        # Handling explicit modal dismissal
        if isinstance(msg, ModalCloseMsg):
            self.pop()
            return self, None

        if isinstance(msg, ModalResultMsg):
            self.pop()
            # Forward the result to the newly exposed active model (or base)
            target = self.top_modal if self.has_modals else self.base_model
            updated_target, cmd = target.update(msg)
            if self.has_modals:
                self.modals[-1] = updated_target
            else:
                self.base_model = updated_target
            return self, cmd

        # Quick escape dismissal
        if self.auto_dismiss_on_esc and isinstance(msg, KeyMsg) and msg.key == "esc":
            self.pop()
            return self, None

        # Delegate message to the topmost modal
        top = self.modals[-1]
        updated_top, cmd = top.update(msg)
        self.modals[-1] = updated_top
        return self, cmd

    def view(self) -> str:
        """Render the base view and composite all active modals on top."""
        content = self.base_model.view()
        for idx, modal in enumerate(self.modals):
            is_top = (idx == len(self.modals) - 1)
            content = place_overlay(
                content,
                modal.view(),
                center=True,
                dim_backdrop=self.dim_backdrop if is_top else False,
            )
        return content

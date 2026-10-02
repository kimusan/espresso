from __future__ import annotations

import unittest
from espresso.beans.modal_stack import ModalCloseMsg, ModalResultMsg, ModalStack
from espresso.core.keys import KeyMsg
from espresso.core.tea import Cmd, Model, Msg


class DummyModel(Model):
    def __init__(self, name: str):
        self.name = name
        self.last_key = ""
        self.result = None

    def init(self) -> Cmd | None:
        return None

    def update(self, msg: Msg) -> tuple[DummyModel, Cmd | None]:
        if isinstance(msg, KeyMsg):
            self.last_key = msg.key
        if isinstance(msg, ModalResultMsg):
            self.result = msg.result
        return self, None

    def view(self) -> str:
        return f"[{self.name} view]"


class TestModalStack(unittest.TestCase):
    def test_empty_stack_delegation(self):
        base = DummyModel("Base")
        stack = ModalStack(base_model=base)
        self.assertFalse(stack.has_modals)
        self.assertIsNone(stack.top_modal)
        self.assertEqual(stack.view(), "[Base view]")

        # Message routes to base model
        stack, _ = stack.update(KeyMsg(key="a"))
        self.assertEqual(base.last_key, "a")

    def test_push_and_pop(self):
        base = DummyModel("Base")
        stack = ModalStack(base_model=base)
        modal1 = DummyModel("Modal1")
        modal2 = DummyModel("Modal2")

        stack.push(modal1)
        self.assertTrue(stack.has_modals)
        self.assertEqual(stack.top_modal, modal1)

        # Message routes to top modal
        stack, _ = stack.update(KeyMsg(key="x"))
        self.assertEqual(modal1.last_key, "x")
        self.assertEqual(base.last_key, "")

        # Push second modal
        stack.push(modal2)
        self.assertEqual(stack.top_modal, modal2)
        stack, _ = stack.update(KeyMsg(key="y"))
        self.assertEqual(modal2.last_key, "y")
        self.assertEqual(modal1.last_key, "x")

        # Pop second modal
        popped = stack.pop()
        self.assertEqual(popped, modal2)
        self.assertEqual(stack.top_modal, modal1)

    def test_auto_dismiss_on_esc(self):
        base = DummyModel("Base")
        stack = ModalStack(base_model=base, auto_dismiss_on_esc=True)
        modal = DummyModel("Modal")
        stack.push(modal)
        self.assertTrue(stack.has_modals)

        stack, _ = stack.update(KeyMsg(key="esc"))
        self.assertFalse(stack.has_modals)

    def test_modal_close_msg(self):
        base = DummyModel("Base")
        stack = ModalStack(base_model=base)
        stack.push(DummyModel("Modal"))
        self.assertTrue(stack.has_modals)

        stack, _ = stack.update(ModalCloseMsg())
        self.assertFalse(stack.has_modals)

    def test_modal_result_msg_dispatch(self):
        base = DummyModel("Base")
        stack = ModalStack(base_model=base)
        modal = DummyModel("Modal")
        stack.push(modal)

        # Dispatching ModalResultMsg dismisses modal and delivers result to base
        stack, _ = stack.update(ModalResultMsg(result={"chosen": 42}))
        self.assertFalse(stack.has_modals)
        self.assertEqual(base.result, {"chosen": 42})


if __name__ == "__main__":
    unittest.main()

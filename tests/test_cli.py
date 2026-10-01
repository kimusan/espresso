"""Unit tests for Espresso CLI tool."""

from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from espresso.cli import main


class TestCLI(unittest.TestCase):
    def test_version(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            with self.assertRaises(SystemExit) as cm:
                main(["--version"])
            self.assertEqual(cm.exception.code, 0)
            self.assertIn("0.2.0", mock_out.getvalue())

    def test_list(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["list"])
            self.assertEqual(code, 0)
            val = mock_out.getvalue()
            self.assertIn("01", val)
            self.assertIn("01_counter.py", val)
            self.assertIn("14_developer_workspace.py", val)

    def test_new_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_app = Path(tmpdir) / "test_app.py"
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
                code = main(["new", str(target_app)])
                self.assertEqual(code, 0)
                self.assertTrue(target_app.exists())
                content = target_app.read_text(encoding="utf-8")
                self.assertIn("class AppModel(Model):", content)
                self.assertIn("Program(AppModel()", content)

            # Test duplicate file refuses to overwrite
            with patch("sys.stdout", new_callable=io.StringIO) as mock_out2:
                code2 = main(["new", str(target_app)])
                self.assertEqual(code2, 1)
                self.assertIn("already exists", mock_out2.getvalue())

    def test_run_invalid_target(self) -> None:
        with patch("sys.stdout", new_callable=io.StringIO) as mock_out:
            code = main(["run", "non_existent_demo_999"])
            self.assertEqual(code, 1)
            self.assertIn("Could not find example", mock_out.getvalue())

    @patch("subprocess.run")
    def test_run_valid_id(self, mock_subproc: unittest.mock.MagicMock) -> None:
        mock_subproc.return_value.returncode = 0
        code = main(["run", "01"])
        self.assertEqual(code, 0)
        self.assertTrue(mock_subproc.called)
        args, _ = mock_subproc.call_args
        self.assertIn("01_counter.py", str(args[0][1]))

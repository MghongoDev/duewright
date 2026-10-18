"""Tests for the menu, run as a process so the real entry point is exercised."""

import os
import subprocess
import sys


def run_menu(answers, data_dir, cwd):
    """Run the menu as a process, with the data folder pointed somewhere temporary."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(data_dir))
    return subprocess.run(
        [sys.executable, "-m", "duewright"],
        input=answers,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        cwd=str(cwd),
    )


def test_the_menu_writes_its_tasks_to_the_data_folder(tmp_path):
    """The tasks go where the data folder points, not beside the code or the working folder."""
    result = run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    stored = tmp_path / "tasks.json"
    assert stored.exists()
    assert "Buy milk" in stored.read_text(encoding="utf-8")

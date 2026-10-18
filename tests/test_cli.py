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


def test_the_menu_keeps_the_tasks_between_runs(tmp_path):
    """A second run reads what the first one wrote."""
    run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert "Buy milk" in result.stdout
    assert "1 pending, 0 overdue, 0 done" in result.stdout


def test_the_menu_reports_a_file_it_cannot_read(tmp_path):
    """A damaged file is kept aside, reported, and the menu still starts."""
    (tmp_path / "tasks.json").write_text('{"version": 2, "tasks": [', encoding="utf-8")
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert "could not be read" in result.stdout
    assert "No tasks yet." in result.stdout
    kept = [entry.name for entry in tmp_path.iterdir() if ".corrupt-" in entry.name]
    assert len(kept) == 1


def test_the_menu_refuses_a_file_from_a_newer_version(tmp_path):
    """A file from a newer version stops the program instead of being overwritten."""
    newer = '{"version": 99, "next_id": 1, "tasks": []}'
    (tmp_path / "tasks.json").write_text(newer, encoding="utf-8")
    result = run_menu("0\n", tmp_path, tmp_path)
    assert "Cannot start" in result.stdout
    assert "Goodbye" not in result.stdout
    assert (tmp_path / "tasks.json").read_text(encoding="utf-8") == newer

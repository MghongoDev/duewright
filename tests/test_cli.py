"""Tests for the menu, run as a process so the real entry point is exercised."""

import os
import subprocess
import sys


def run_menu(answers, data_dir, cwd, backend=None):
    """Run the menu as a process, with the data folder pointed somewhere temporary."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(data_dir))
    if backend is None:
        environment.pop("DUEWRIGHT_BACKEND", None)
    else:
        environment["DUEWRIGHT_BACKEND"] = backend
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
    """The default store is the database, and it lands in the configured folder."""
    result = run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "tasks.db").exists()


def test_the_menu_can_use_the_json_file_instead(tmp_path):
    """The setting picks the other store, and the database is left alone."""
    result = run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path, backend="json")
    assert result.returncode == 0
    assert (tmp_path / "tasks.json").exists()
    assert not (tmp_path / "tasks.db").exists()


def test_the_menu_keeps_the_tasks_between_runs(tmp_path):
    """A second run reads what the first one wrote, whatever the store is."""
    run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert "Buy milk" in result.stdout
    assert "1 pending, 0 overdue, 0 done" in result.stdout


def test_the_menu_reports_a_json_file_it_cannot_read(tmp_path):
    """A damaged file is kept aside, reported, and the menu still starts."""
    (tmp_path / "tasks.json").write_text('{"version": 2, "tasks": [', encoding="utf-8")
    result = run_menu("2\n0\n", tmp_path, tmp_path, backend="json")
    assert result.returncode == 0
    assert "could not be read" in result.stdout
    assert "No tasks yet." in result.stdout
    kept = [entry.name for entry in tmp_path.iterdir() if ".corrupt-" in entry.name]
    assert len(kept) == 1


def test_the_menu_reports_a_database_it_cannot_read(tmp_path):
    """A file that is not a database is reported rather than crashing the menu."""
    (tmp_path / "tasks.db").write_text("this is not a database", encoding="utf-8")
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert "could not be read" in result.stdout


def test_the_menu_refuses_a_json_file_from_a_newer_version(tmp_path):
    """A store from a newer version stops the program instead of being overwritten."""
    newer = '{"version": 99, "next_id": 1, "tasks": []}'
    (tmp_path / "tasks.json").write_text(newer, encoding="utf-8")
    result = run_menu("0\n", tmp_path, tmp_path, backend="json")
    assert "Cannot start" in result.stdout
    assert "Goodbye" not in result.stdout
    assert (tmp_path / "tasks.json").read_text(encoding="utf-8") == newer


def test_the_menu_refuses_a_backend_it_does_not_have(tmp_path):
    """A typo in the setting stops the program rather than quietly ignoring it."""
    result = run_menu("0\n", tmp_path, tmp_path, backend="postgres")
    assert "Cannot start" in result.stdout
    assert "Goodbye" not in result.stdout

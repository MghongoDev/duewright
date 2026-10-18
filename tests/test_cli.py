"""Tests for the menu, run as a process so the real entry point is exercised."""

import json
import os
import subprocess
import sys

CREATED = "2026-10-18T17:52:04+00:00"


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


def run_command(arguments, data_dir, cwd):
    """Run one of the operational commands as a process."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(data_dir))
    environment.pop("DUEWRIGHT_BACKEND", None)
    return subprocess.run(
        [sys.executable, "-m", "duewright", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        cwd=str(cwd),
    )


def write_a_file(path):
    """A task file holding one task."""
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [
                    {
                        "id": 1,
                        "title": "Buy milk",
                        "done": False,
                        "created_at": CREATED,
                        "priority": "high",
                        "due_date": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
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


def test_the_migration_command_moves_the_tasks(tmp_path):
    """The command moves the file's tasks into the database the menu then reads."""
    source = tmp_path / "tasks.json"
    write_a_file(source)
    result = run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    assert result.returncode == 0
    assert "Moved 1 tasks" in result.stdout
    listing = run_menu("2\n0\n", tmp_path, tmp_path)
    assert "Buy milk" in listing.stdout
    assert "1 pending, 0 overdue, 0 done" in listing.stdout


def test_the_migration_command_dry_run_writes_nothing(tmp_path):
    source = tmp_path / "tasks.json"
    write_a_file(source)
    result = run_command(["migrate-json", str(source), "--dry-run"], tmp_path, tmp_path)
    assert result.returncode == 0
    assert "dry run" in result.stdout
    assert not (tmp_path / "tasks.db").exists()


def test_the_migration_command_refuses_a_database_that_holds_tasks(tmp_path):
    source = tmp_path / "tasks.json"
    write_a_file(source)
    run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    again = run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    assert again.returncode == 1
    assert "already holds" in again.stdout


def test_an_unknown_command_says_so(tmp_path):
    result = run_command(["sing"], tmp_path, tmp_path)
    assert result.returncode == 2
    assert "is not a command" in result.stdout

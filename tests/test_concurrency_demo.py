"""The script that measures what several processes writing at once costs.

The numbers are small here so the suite stays quick. The README records the
full run of four processes adding fifty tasks each, on Windows and on Linux.
"""

import os
import subprocess
import sys
from pathlib import Path

from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "concurrency_demo.py"


def run_demo(*arguments):
    """Run the demonstration script as a process."""
    environment = dict(os.environ)
    environment.pop("DUEWRIGHT_BACKEND", None)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def reported(result, label):
    """The number the script printed for one of its lines."""
    for line in result.stdout.splitlines():
        if line.startswith(f"{label}:"):
            return int(line.split(":")[1])
    raise AssertionError(f"the script did not print {label!r}:\n{result.stdout}")


def test_the_database_loses_nothing_when_processes_write_at_once(tmp_path):
    result = run_demo(
        "--backend", "sqlite", "--workers", "2", "--tasks", "10", "--data-dir", str(tmp_path)
    )
    assert result.returncode == 0
    assert reported(result, "tasks the workers were asked to add") == 20
    assert reported(result, "tasks the workers reported adding") == 20
    assert reported(result, "tasks in the store afterwards") == 20
    assert reported(result, "tasks a worker failed to add") == 0
    assert reported(result, "tasks overwritten by another process") == 0
    assert "Nothing was lost." in result.stdout


def test_the_file_backend_reports_what_happened(tmp_path):
    """The file may lose tasks, or a worker may fail. Either way it is reported."""
    result = run_demo(
        "--backend", "json", "--workers", "2", "--tasks", "10", "--data-dir", str(tmp_path)
    )
    assert result.returncode == 0
    assert "Nothing was lost." in result.stdout or "Not everything arrived" in result.stdout


def test_the_file_backend_accounts_for_every_task_it_was_given(tmp_path):
    """Every task is either stored, or counted as failed, or counted as overwritten."""
    result = run_demo(
        "--backend", "json", "--workers", "2", "--tasks", "10", "--data-dir", str(tmp_path)
    )
    asked = reported(result, "tasks the workers were asked to add")
    stored = reported(result, "tasks in the store afterwards")
    failed = reported(result, "tasks a worker failed to add")
    overwritten = reported(result, "tasks overwritten by another process")
    assert asked == 20
    assert stored == asked - failed - overwritten
    assert stored <= asked


def test_the_reported_count_matches_the_store_on_disk(tmp_path):
    """The script's number is the store's number, not an assumption."""
    result = run_demo(
        "--backend", "sqlite", "--workers", "2", "--tasks", "10", "--data-dir", str(tmp_path)
    )
    stored, _ = SqliteTaskRepository(tmp_path / "tasks.db").list_tasks()
    assert reported(result, "tasks in the store afterwards") == len(stored)
    assert len({task.title for task in stored}) == 20


def test_the_file_run_reports_the_file_it_used(tmp_path):
    """The count comes from the file backend, not from a database beside it."""
    result = run_demo(
        "--backend", "json", "--workers", "2", "--tasks", "10", "--data-dir", str(tmp_path)
    )
    stored, _ = JsonTaskRepository(tmp_path / "tasks.json").list_tasks()
    assert reported(result, "tasks in the store afterwards") == len(stored)
    assert not (tmp_path / "tasks.db").exists()


def test_the_default_folder_is_temporary(tmp_path):
    """Without a folder named, nothing is written near the real tasks."""
    result = run_demo("--backend", "sqlite", "--workers", "1", "--tasks", "2")
    assert result.returncode == 0
    assert "duewright-demo-" in result.stdout
    assert reported(result, "tasks in the store afterwards") == 2

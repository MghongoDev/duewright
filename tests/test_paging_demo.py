"""The script that measures what a page costs against fetching everything.

The numbers are small here so the suite stays quick. The README records the
run at a hundred thousand Tasks.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "paging_demo.py"


def run_demo(*arguments):
    """Run the demonstration script as a process."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_the_demo_reports_what_each_way_moved():
    """The row count is the claim that does not depend on the machine."""
    result = run_demo("--tasks", "500", "--page", "20")
    assert result.returncode == 0
    assert "every Task, then ordered and sliced in Python:" in result.stdout
    assert "one page asked of the store:" in result.stdout
    assert "500 rows moved" in result.stdout
    assert "20 rows moved" in result.stdout


def test_the_demo_builds_the_number_of_tasks_it_was_asked_for():
    result = run_demo("--tasks", "300", "--page", "10")
    assert "building 300 Tasks" in result.stdout
    assert "300 rows moved" in result.stdout
    assert "10 rows moved" in result.stdout

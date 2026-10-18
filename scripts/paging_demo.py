"""What a page costs, measured against fetching everything and ordering it here.

Before a store could be asked for a page, every list fetched all the Tasks and
the ordering and the slicing happened in Python. That work is reproduced here
beside the query that replaced it, so the difference is measured rather than
claimed.

The row count is the number to trust, because the timing depends on the
machine and the count does not.

    python scripts/paging_demo.py
    python scripts/paging_demo.py --tasks 100000 --page 20
"""

import argparse
import sqlite3
import tempfile
import time
from pathlib import Path

from duewright.repositories.base import sort_key
from duewright.repositories.sqlite_repo import SqliteTaskRepository

CREATED = "2026-10-18T00:00:00+00:00"


def build(path: Path, tasks: int) -> None:
    """Fill a fresh database with the number of Tasks asked for, in one transaction."""
    SqliteTaskRepository(path).list_tasks()
    with sqlite3.connect(path) as conn:
        conn.executemany(
            "INSERT INTO tasks (title, done, priority, due_date, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            [(f"Task number {number}", 0, "medium", None, CREATED) for number in range(tasks)],
        )


def everything_then_order(path: Path, page: int) -> tuple[float, int, int]:
    """Fetch every Task, order them in Python, and take the first page.

    This is the work a list used to do, kept here so the two can be measured
    side by side.
    """
    started = time.perf_counter()
    tasks, _ = SqliteTaskRepository(path).list_tasks()
    first_page = sorted(tasks, key=sort_key)[:page]
    return time.perf_counter() - started, len(tasks), len(first_page)


def one_page(path: Path, page: int) -> tuple[float, int, int]:
    """Ask the store for the page itself."""
    started = time.perf_counter()
    asked_for, _ = SqliteTaskRepository(path).list_tasks(limit=page)
    return time.perf_counter() - started, len(asked_for), len(asked_for)


def main() -> None:
    """Build a store, measure both ways, and report what each one moved."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=int, default=20000, help="how many Tasks to build")
    parser.add_argument("--page", type=int, default=20, help="how many the page holds")
    arguments = parser.parse_args()

    path = Path(tempfile.mkdtemp(prefix="duewright-paging-")) / "tasks.db"
    print(f"building {arguments.tasks} Tasks in {path}")
    started = time.perf_counter()
    build(path, arguments.tasks)
    print(f"built in {time.perf_counter() - started:.1f} s")
    print(f"page size: {arguments.page}")

    slow, everything, slow_page = everything_then_order(path, arguments.page)
    fast, fetched, fast_page = one_page(path, arguments.page)

    print(
        "every Task, then ordered and sliced in Python:"
        f" {slow * 1000:8.1f} ms, {everything} rows moved, {slow_page} on the page"
    )
    print(
        "one page asked of the store:"
        f" {fast * 1000:8.1f} ms, {fetched} rows moved, {fast_page} on the page"
    )
    print(
        f"the page moves {everything / fetched:.0f} times fewer rows"
        f" and takes {slow / fast:.0f} times less time"
    )


if __name__ == "__main__":
    main()

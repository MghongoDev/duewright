"""What happens when several processes write at once.

The database serialises its writers, so nothing is lost. A JSON file does not,
so processes overwrite each other's work, and on Windows a process can fail
outright while another one is replacing the file.

    python scripts/concurrency_demo.py
    python scripts/concurrency_demo.py --backend json --workers 4 --tasks 50

The numbers are printed rather than asserted, because this measures a
behaviour rather than checking one. The suite runs the same script with small
numbers; the README records the full run.
"""

import argparse
import multiprocessing
import tempfile
from pathlib import Path

from duewright import config
from duewright.models import Task
from duewright.repositories.base import TaskRepository
from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository


def build(backend: str, folder: Path) -> TaskRepository:
    """Build the repository for one backend, pointed at one folder."""
    if backend == "sqlite":
        return SqliteTaskRepository(folder / config.DATABASE_FILE_NAME)
    return JsonTaskRepository(folder / config.JSON_FILE_NAME)


def count(backend: str, folder: Path) -> int:
    """How many tasks the store holds now."""
    return len(build(backend, folder).list_tasks())


def add_tasks(job: tuple[str, str, int, int]) -> tuple[int, int, str]:
    """Add the tasks one process is responsible for.

    Returns the worker's number, how many it added, and the error it hit if it
    hit one. A process failing outright is one of the results being measured,
    so the error comes back as a value rather than stopping the run.
    """
    backend, folder, worker, tasks = job
    added = 0
    try:
        repository = build(backend, Path(folder))
        for index in range(tasks):
            repository.add(Task(title=f"worker {worker}, task {index}"))
            added += 1
    except Exception as error:  # noqa: BLE001 - the failure is the measurement
        return worker, added, f"{type(error).__name__}: {error}"
    return worker, added, ""


def run(backend: str, workers: int, tasks: int, folder: Path) -> None:
    """Start the writers, then report what survived."""
    folder.mkdir(parents=True, exist_ok=True)
    print(f"backend: {backend}")
    print(f"workers: {workers}, tasks each: {tasks}")
    print(f"folder: {folder}")
    print(f"tasks in the store before: {count(backend, folder)}")
    jobs = [(backend, str(folder), worker, tasks) for worker in range(workers)]
    with multiprocessing.Pool(processes=workers) as pool:
        results = pool.map(add_tasks, jobs)
    reported = sum(added for _, added, _ in results)
    stored = count(backend, folder)
    print(f"tasks the workers reported adding: {reported}")
    print(f"tasks in the store afterwards: {stored}")
    print(f"tasks lost: {reported - stored}")
    for worker, _, message in results:
        if message:
            print(f"worker {worker} failed: {message}")
    if reported == stored:
        print("Nothing was lost.")
    else:
        print("Tasks were lost, or a worker failed outright.")


def main() -> None:
    """Read the options and run the demonstration."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=config.BACKENDS, default=config.DEFAULT_BACKEND)
    parser.add_argument("--workers", type=int, default=4, help="how many processes write at once")
    parser.add_argument("--tasks", type=int, default=50, help="how many tasks each process adds")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=None,
        help="where to write (default: a fresh temporary folder, so real tasks are never touched)",
    )
    arguments = parser.parse_args()
    folder = arguments.data_dir or Path(tempfile.mkdtemp(prefix="duewright-demo-"))
    run(arguments.backend, arguments.workers, arguments.tasks, folder)


if __name__ == "__main__":
    main()

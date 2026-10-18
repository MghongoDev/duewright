"""The menu.

This is the only module that reads input or prints, which is what keeps the
rest of the package testable and reusable.
"""

from pathlib import Path
from typing import Any, Callable, Optional

from duewright.manager import TaskManager, TaskNotFoundError
from duewright.storage import CorruptStorageError, load_tasks, save_tasks
from duewright.validators import clean_title, parse_task_id, parse_yes_no

MENU = """
1) Add a task
2) List tasks
3) Edit a task title
4) Mark a task done / undone
5) Delete a task
0) Quit
"""

# Anchored to the project folder rather than to the directory you happen to
# launch from, so there is one tasks.json instead of one per working folder.
TASKS_FILE = Path(__file__).resolve().parent.parent / "tasks.json"


def show_menu() -> None:
    """Print the menu."""
    print(MENU)


def print_tasks(manager: TaskManager) -> None:
    """Print every task, or a message when the list is empty."""
    tasks = manager.all()
    if not tasks:
        print("No tasks yet.")
        return
    for task in tasks:
        mark = "x" if task.done else " "
        print(f"[{mark}]  {task.id}  {task.title}")


def prompt(question: str, parser: Callable[[str], Any]) -> Any:
    """Ask until the parser accepts an answer, and let a blank answer cancel.

    The parser is one of the validators, so the rule for what counts as a good
    answer lives there and this loop only has to keep asking.
    """
    while True:
        answer = input(question)
        if not answer.strip():
            return None
        try:
            return parser(answer)
        except ValueError as error:
            print(error)


def ask_confirm(question: str) -> bool:
    """Ask a yes or no question. A blank answer means no."""
    while True:
        answer = input(question).strip()
        if not answer:
            return False
        try:
            return parse_yes_no(answer)
        except ValueError as error:
            print(error)


def commit(manager: TaskManager) -> None:
    """Write the current tasks to disk, reporting a write that fails."""
    try:
        save_tasks(TASKS_FILE, manager.all(), manager.next_id)
    except OSError as error:
        print(f"Your change was not saved: {error}")
        print("It will be lost when you quit.")


def handle_add(manager: TaskManager) -> None:
    """Ask for a title, add the task, then show the list."""
    title = prompt("Title: ", clean_title)
    if title is None:
        print("Cancelled.")
        return
    manager.add(title)
    commit(manager)
    print_tasks(manager)


def handle_update(manager: TaskManager) -> None:
    """Ask for an id and a new title, then show the list."""
    task_id = prompt("Task id to edit: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        manager.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    title = prompt("New title: ", clean_title)
    if title is None:
        print("Cancelled.")
        return
    manager.update_title(task_id, title)
    commit(manager)
    print_tasks(manager)


def handle_toggle(manager: TaskManager) -> None:
    """Ask for an id, flip its done flag, then show the list."""
    task_id = prompt("Task id to mark: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        manager.toggle_done(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    commit(manager)
    print_tasks(manager)


def handle_delete(manager: TaskManager) -> None:
    """Ask for an id, confirm, delete that task, then show the list."""
    task_id = prompt("Task id to delete: ", parse_task_id)
    if task_id is None:
        print("Cancelled.")
        return
    try:
        task = manager.get(task_id)
    except TaskNotFoundError:
        print(f"No task with id {task_id}.")
        return
    if not ask_confirm(f"Delete task {task_id} ({task.title})? (y/N) "):
        print("Nothing was deleted.")
        return
    manager.delete(task_id)
    commit(manager)
    print_tasks(manager)


def load_manager() -> TaskManager:
    """Build a manager from the task file, reporting a file it cannot read."""
    try:
        tasks, next_id = load_tasks(TASKS_FILE)
    except CorruptStorageError as error:
        print(f"{TASKS_FILE.name} could not be read: {error}.")
        print(f"It is kept as {error.spoiled_path.name}, and Duewright is starting empty.")
        tasks, next_id = [], 1
    except OSError as error:
        print(f"Could not read {TASKS_FILE.name}: {error}")
        print("Duewright is starting with an empty list.")
        tasks, next_id = [], 1
    return TaskManager(tasks, next_id)


def main() -> None:
    """Load the tasks, then run the menu loop until the user quits."""
    manager = load_manager()
    print("Duewright")
    try:
        while True:
            show_menu()
            choice = input("Choose an option: ").strip()

            if choice == "0":
                print("Goodbye.")
                break
            elif choice == "1":
                handle_add(manager)
            elif choice == "2":
                print_tasks(manager)
            elif choice == "3":
                handle_update(manager)
            elif choice == "4":
                handle_toggle(manager)
            elif choice == "5":
                handle_delete(manager)
            else:
                print(f"{choice!r} is not an option.")
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")

"""Duewright: a command-line task manager.

Phase 2 of the implementation guide. Every change is written to tasks.json
straight away, so tasks survive a restart and a crash loses nothing.

Run with: python main.py
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

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
TASKS_FILE = Path(__file__).resolve().parent / "tasks.json"

FILE_VERSION = 1

# The next id to hand out. It only ever goes up, so the id of a deleted task
# is never handed to a different task (see docs/adr/0002).
NEXT_ID = 1


def show_menu():
    """Print the menu."""
    print(MENU)


def add_task(tasks, title):
    """Append a new task and return it."""
    global NEXT_ID
    task = {
        "id": NEXT_ID,
        "title": title,
        "done": False,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    NEXT_ID += 1
    tasks.append(task)
    return task


def find_task(tasks, task_id):
    """Return the task with this id, or None."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    return None


def update_task(tasks, task_id, new_title):
    """Replace a task's title. Return False when the id is unknown."""
    task = find_task(tasks, task_id)
    if task is None:
        return False
    task["title"] = new_title
    return True


def toggle_done(tasks, task_id):
    """Flip a task's done flag. Return False when the id is unknown."""
    task = find_task(tasks, task_id)
    if task is None:
        return False
    task["done"] = not task["done"]
    return True


def delete_task(tasks, task_id):
    """Remove a task. Return False when the id is unknown."""
    task = find_task(tasks, task_id)
    if task is None:
        return False
    tasks.remove(task)
    return True


def print_tasks(tasks):
    """Print every task, or a message when the list is empty."""
    if not tasks:
        print("No tasks yet.")
        return
    for task in tasks:
        mark = "x" if task["done"] else " "
        print(f"[{mark}]  {task['id']}  {task['title']}")


def ask_id(question):
    """Read a task id, or return None when the answer is not a whole number."""
    try:
        return int(input(question))
    except ValueError:
        print("That is not a number.")
        return None


def save_tasks(path, tasks, next_id):
    """Write the task file in one step, so a crash cannot leave it half written."""
    tmp_path = path.with_name(path.name + ".tmp")
    payload = {"version": FILE_VERSION, "next_id": next_id, "tasks": tasks}
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)


def load_tasks(path):
    """Read the task file and return (tasks, next_id).

    A missing file gives an empty list. A file that cannot be read or parsed
    is moved aside rather than overwritten, because it may hold the only copy
    of the user's tasks.
    """
    if not path.exists():
        return [], 1
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        tasks = data["tasks"]
        if not isinstance(tasks, list) or not all(
            isinstance(task, dict) for task in tasks
        ):
            raise ValueError("the file does not hold a list of tasks")
    except json.JSONDecodeError as error:
        return _set_aside(path, f"it is not valid JSON ({error})")
    except (KeyError, TypeError, ValueError) as error:
        return _set_aside(path, f"it is not shaped like a task file ({error})")
    except OSError as error:
        print(f"Could not read {path.name}: {error}")
        print("Duewright is starting with an empty list.")
        return [], 1

    next_id = data.get("next_id")
    if not isinstance(next_id, int) or next_id < 1:
        # A hand-written file may carry no counter. The highest id it holds is
        # the best guess available.
        next_id = max((task.get("id", 0) for task in tasks), default=0) + 1
    return tasks, next_id


def _set_aside(path, reason):
    """Keep an unreadable file under a new name and return an empty task list."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    spoiled = path.with_name(f"{path.name}.corrupt-{stamp}")
    path.replace(spoiled)
    print(f"{path.name} could not be read: {reason}.")
    print(f"It is kept as {spoiled.name}, and Duewright is starting empty.")
    return [], 1


def main():
    """Load the tasks, then run the menu loop."""
    global NEXT_ID
    tasks, next_id = load_tasks(TASKS_FILE)
    NEXT_ID = next_id
    print("Duewright")
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            break
        elif choice == "1":
            add_task(tasks, input("Title: ").strip())
            save_tasks(TASKS_FILE, tasks, NEXT_ID)
            print_tasks(tasks)
        elif choice == "2":
            print_tasks(tasks)
        elif choice == "3":
            task_id = ask_id("Task id to edit: ")
            if task_id is not None:
                if update_task(tasks, task_id, input("New title: ").strip()):
                    save_tasks(TASKS_FILE, tasks, NEXT_ID)
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        elif choice == "4":
            task_id = ask_id("Task id to mark: ")
            if task_id is not None:
                if toggle_done(tasks, task_id):
                    save_tasks(TASKS_FILE, tasks, NEXT_ID)
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        elif choice == "5":
            task_id = ask_id("Task id to delete: ")
            if task_id is not None:
                if delete_task(tasks, task_id):
                    save_tasks(TASKS_FILE, tasks, NEXT_ID)
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        else:
            print(f"{choice!r} is not an option.")


if __name__ == "__main__":
    main()

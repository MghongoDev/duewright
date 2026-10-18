"""Duewright: a command-line task manager.

Phase 1 of the implementation guide. Tasks live in memory only, so they are
gone when the program exits. Saving them to a file is Phase 2.

Run with: python main.py
"""

from datetime import datetime, timezone

MENU = """
1) Add a task
2) List tasks
3) Edit a task title
4) Mark a task done / undone
5) Delete a task
0) Quit
"""

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


def main():
    """Run the menu loop."""
    tasks = []
    print("Duewright")
    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            break
        elif choice == "1":
            add_task(tasks, input("Title: ").strip())
            print_tasks(tasks)
        elif choice == "2":
            print_tasks(tasks)
        elif choice == "3":
            task_id = ask_id("Task id to edit: ")
            if task_id is not None:
                if update_task(tasks, task_id, input("New title: ").strip()):
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        elif choice == "4":
            task_id = ask_id("Task id to mark: ")
            if task_id is not None:
                if toggle_done(tasks, task_id):
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        elif choice == "5":
            task_id = ask_id("Task id to delete: ")
            if task_id is not None:
                if delete_task(tasks, task_id):
                    print_tasks(tasks)
                else:
                    print(f"No task with id {task_id}.")
        else:
            print(f"{choice!r} is not an option.")


if __name__ == "__main__":
    main()

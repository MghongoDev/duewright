# Duewright

A command-line task manager. You pick an option from a menu to add, list, edit, mark done and delete tasks, and every change is written to `tasks.json` in the project folder straight away.

Tasks are numbered with a stable id, and an id is never handed to a second task, so a number you wrote down keeps pointing at the same task even after a deletion.

## Run it

Duewright needs Python 3.12 or newer, and nothing else.

```
python -m duewright
```

The tests need pytest:

```
pip install pytest
python -m pytest
```

## What the list shows

```
[ ]    1  Pay the rent              high    due 2026-10-05  OVERDUE
[ ]    2  Water the plants          medium  due 2026-10-18  DUE TODAY
[ ]    4  Call Sam                  high
[x]    3  Book tickets              low
3 pending, 1 overdue, 1 done
```

Pending tasks come first, then tasks that carry a due date, earliest due date first, then higher priority before lower, then lower id. A task is overdue when it is pending and its due date has passed. A task due today gets its own marker, because it is not late yet.

## Menu

```
1) Add a task
2) List tasks
3) Edit a task title
4) Mark a task done / undone
5) Delete a task
6) Filter the list
7) Search titles
0) Quit
```

## Sample session

```
$ python -m duewright

Duewright

1) Add a task
...
Choose an option: 1
Title: Pay the rent
Priority (low/medium/high, blank for medium): high
Due date (YYYY-MM-DD, blank for none): 2026-10-05
[ ]    1  Pay the rent              high    due 2026-10-05  OVERDUE
1 pending, 1 overdue, 0 done
Choose an option: 7
Search titles: rent
[ ]    1  Pay the rent              high    due 2026-10-05  OVERDUE
1 pending, 1 overdue, 0 done
Choose an option: 4
Task id to mark: 1
[x]    1  Pay the rent              high    due 2026-10-05
0 pending, 0 overdue, 1 done
Choose an option: 5
Task id to delete: 1
Delete task 1 (Pay the rent)? (y/N) y
No tasks yet.
Choose an option: 0
Goodbye.
```

## Where the tasks live

`tasks.json`, in the project folder next to the code. It is plain JSON, and it is in `.gitignore`, so your tasks never reach the repository.

```json
{
  "version": 2,
  "next_id": 2,
  "tasks": [
    {
      "id": 1,
      "title": "Pay the rent",
      "done": false,
      "created_at": "2026-10-18T18:20:11+00:00",
      "priority": "high",
      "due_date": "2026-10-05"
    }
  ]
}
```

Three details are worth knowing. Every write goes to a temporary file that is swapped into place in one step, so a crash part-way through cannot leave a half-written file. If the file cannot be read, Duewright keeps it under a name like `tasks.json.corrupt-20261018-182011` and starts with an empty list, because that file may be the only copy of your tasks. And a file written by a newer version of Duewright is refused rather than opened, so an older program cannot quietly drop fields it does not understand.

## Layout

```
duewright/
├── duewright/
│   ├── __main__.py      # python -m duewright
│   ├── cli.py           # the menu, the only module that reads input or prints
│   ├── manager.py       # the rules: ordering, overdue, filter, search, summary
│   ├── models.py        # Task
│   ├── storage.py       # the only module that knows about JSON and the filesystem
│   └── validators.py    # pure functions for the input
├── tests/
├── GLOSSARY.md
├── docs/adr/            # the decisions, and why they were taken
└── tasks.json           # created at runtime, not committed
```

Three rules keep those apart, and they are the main lesson of the project:

1. Only `cli.py` calls `input()` or `print()`.
2. `manager.py` never touches the disk.
3. `validators.py` holds pure functions, so each rule is a short test.

## What I would improve

- Editing the priority or the due date of a task that already exists. Only the title can be edited today, so fixing a wrong due date means deleting the task and adding it again.
- Sorting and paging in the store instead of in Python. Fine for a few hundred tasks, wrong for a hundred thousand.
- A second place to keep the tasks. The rules do not care where tasks are stored, and the code should prove that.
- A warning when a task is about to become due.

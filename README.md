# Duewright

![CI](https://github.com/MghongoDev/duewright/actions/workflows/ci.yml/badge.svg)

A command-line task manager. You pick an option from a menu to add, list, edit, mark done and delete tasks, and every change is written to a store straight away.

Tasks are numbered with a stable id, and an id is never handed to a second task, so a number you wrote down keeps pointing at the same task even after a deletion.

## Install it

Duewright needs Python 3.12 or newer.

```
pip install -e ".[dev]"
```

That gives you a `duewright` command that works from any folder. Running it as a module works too:

```
python -m duewright
```

The `dev` extra brings pytest, which is what the tests need:

```
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

The service does the ordering and the paging in Python rather than in the store. That is the right trade at this size and the wrong one for hundreds of thousands of tasks. The keyword search also runs in Python, because the database compares text without case for ASCII only, and doing it here keeps every backend behaving the same way.

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
$ duewright

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

A SQLite database called `tasks.db`, in a folder named `.duewright` inside your home folder. It lives there rather than beside the code, so reinstalling or upgrading the program cannot touch your tasks. Set `DUEWRIGHT_DATA_DIR` to keep it somewhere else, which is also how the tests stay away from real data.

Set `DUEWRIGHT_BACKEND=json` to keep the tasks in a `tasks.json` file instead. Both backends pass the same contract tests and the menu behaves identically, but only the database copes with two copies of the program running at once.

Version 0.1.0 kept the JSON file beside the code. If you ran that version, move it into the data folder once:

```
mv tasks.json ~/.duewright/tasks.json
```

On Windows, that is `move tasks.json %USERPROFILE%\.duewright\tasks.json`. If you move it, also set `DUEWRIGHT_BACKEND=json`, because the database is the default and your tasks would not be read otherwise.

The database refuses bad data on its own: a title that is empty or longer than 100 characters, a priority that is not one of the three, and a done flag that is not 0 or 1 are all rejected by the table, so a bug in the code above cannot write them. It also records which version of the schema it holds, and refuses to open a database written by a newer version of the program.

The JSON file, when you use it, is plain JSON and looks like this:

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

Three details are worth knowing about it. Every write goes to a temporary file that is swapped into place in one step, so a crash part-way through cannot leave a half-written file. If the file cannot be read, Duewright keeps it under a name like `tasks.json.corrupt-20261018-182011` and starts with an empty list, because that file may be the only copy of your tasks. And a file written by a newer version is refused rather than opened, so an older program cannot quietly drop fields it does not understand.

## Layout

```
duewright/
├── duewright/
│   ├── __main__.py       # python -m duewright
│   ├── cli.py            # the menu, the only module that reads input or prints
│   ├── config.py         # where the tasks live, and which repository keeps them
│   ├── errors.py         # the errors the package raises
│   ├── models.py         # Task
│   ├── repositories/
│   │   ├── base.py       # the interface a repository has to satisfy
│   │   ├── json_repo.py  # the only module that knows about JSON
│   │   ├── memory.py     # for tests
│   │   └── sqlite_repo.py # the database, and the only module that knows SQL
│   ├── service.py        # the rules: ordering, overdue, filter, search, summary
│   └── validators.py     # pure functions for the input
├── tests/
│   ├── test_repositories.py  # the contract every repository has to satisfy
│   ├── test_json_repo.py     # the behaviours that belong to the file alone
│   ├── test_sqlite_repo.py   # the behaviours that belong to the database alone
│   └── ...
├── pyproject.toml
├── GLOSSARY.md
└── docs/adr/             # the decisions, and why they were taken
```

Three rules keep those apart, and they are the main lesson of the project:

1. Only `cli.py` calls `input()` or `print()`.
2. The service never touches the disk. It asks a repository, and only the repository modules know about files, JSON and SQL.
3. `validators.py` holds pure functions, so each rule is a short test.

## What I would improve

- Editing the priority or the due date of a task that already exists. Only the title can be edited today, so fixing a wrong due date means deleting the task and adding it again.
- Sorting and paging in the store instead of in Python. Fine for a few hundred tasks, wrong for a hundred thousand.
- A fourth place to keep the tasks, such as PostgreSQL. The contract suite and the interface are in place, so a new backend is one class and no change to the rules.
- A warning when a task is about to become due.

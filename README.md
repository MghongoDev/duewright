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

The server lives behind its own extra, so the menu works without it. Add it when you want the API:

```
pip install -e ".[api]"
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

## The same list over HTTP

The API runs on the same service the menu uses, so a rule fixed once is fixed in both places.

```
duewright serve
```

That binds to `127.0.0.1:8000`. It is the loopback address rather than every address, so starting the server does not put your task list on the network. `--host` and `--port` change both. Open `http://127.0.0.1:8000/docs` to try every route by hand.

The routes, all under `/api/v1`:

```
GET    /health          the server is up, without touching the store
GET    /tasks           list, with done, q, limit and offset
POST   /tasks           create, answers 201
GET    /tasks/{id}      read one
PATCH  /tasks/{id}      change the fields the body names
DELETE /tasks/{id}      delete, answers 204 with no body
```

Listing answers with an envelope, so a client always knows where it is:

```json
{
  "items": [
    {
      "id": 1,
      "title": "Buy milk",
      "done": false,
      "priority": "high",
      "due_date": "2026-10-05",
      "created_at": "2026-10-18T18:20:11+00:00"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

A partial update tells a field that was left out from one sent as null. Leaving `due_date` out keeps it, and sending `"due_date": null` clears it. A null title is refused, because a task without one makes no sense:

```
curl -X PATCH localhost:8000/api/v1/tasks/1 -H "Content-Type: application/json" -d '{"due_date": null}'
```

A missing task answers 404 with a body naming the task. A body or a query that makes no sense answers 422, and a misspelled field fails loudly instead of being ignored. Every error is mapped in one place, in `duewright/api/app.py`.

The request models check the shape of what arrives and the service checks what it means, so the API cannot create a task the menu would refuse. Every route that reaches the store is a plain function rather than an async one, so a slow store delays one request instead of the whole server.

## Where the tasks live

A SQLite database called `tasks.db`, in a folder named `.duewright` inside your home folder. It lives there rather than beside the code, so reinstalling or upgrading the program cannot touch your tasks. Set `DUEWRIGHT_DATA_DIR` to keep it somewhere else, which is also how the tests stay away from real data.

Set `DUEWRIGHT_BACKEND=json` to keep the tasks in a `tasks.json` file instead. Both backends pass the same contract tests and the menu behaves identically, but only the database copes with two copies of the program running at once.

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

## Why the database is the default

Two copies of the program can run at once, so one store has to cope with two writers. `scripts/concurrency_demo.py` measures what each store does: it starts four processes, each adding fifty tasks, and counts every task as stored, as one a worker failed to add, or as one another process overwrote.

The database stored all two hundred tasks, on Windows and on Linux. The file lost almost everything. On Windows one task of the two hundred survived and every process died with a permission error while replacing the file. On Linux none survived: the processes wrote over each other's work, one of them read the file half written, and the program moved it aside as unreadable.

```
$ python scripts/concurrency_demo.py --backend json     # on Linux
backend: json
workers: 4, tasks each: 50
tasks in the store before: 0
tasks the workers were asked to add: 200
tasks the workers reported adding: 2
tasks in the store afterwards: 0
tasks a worker failed to add: 198
tasks overwritten by another process: 2
worker 0 failed: CorruptStorageError: it is not valid JSON (Extra data: line 14 column 2 (char 235))
worker 1 failed: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/duewright-demo-9lasn8uu/tasks.json.tmp' -> '/tmp/duewright-demo-9lasn8uu/tasks.json'
worker 2 failed: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/duewright-demo-9lasn8uu/tasks.json.tmp' -> '/tmp/duewright-demo-9lasn8uu/tasks.json'
worker 3 failed: FileNotFoundError: [Errno 2] No such file or directory: '/tmp/duewright-demo-9lasn8uu/tasks.json' -> '/tmp/duewright-demo-9lasn8uu/tasks.json.corrupt-20261018-172721'
Not everything arrived: this store lost work when two processes wrote at once.
```

The exact numbers move from run to run, because this is a race. The database result has not moved: it stored all two hundred tasks in every run, on both platforms. Continuous integration runs the demonstration on Linux on every push, and the suite runs it with smaller numbers on both platforms.

## Moving a JSON file into the database

If your tasks are in a JSON file, one command moves them into the database:

```
duewright migrate-json ~/.duewright/tasks.json --dry-run
duewright migrate-json ~/.duewright/tasks.json
```

The dry run reads the file and checks it without writing anything. The real run moves the tasks, keeping their ids and their creation times, then reads both sides back and compares every field before it reports success. The file itself is left exactly as it was, so it stays a copy of your tasks.

It refuses to run when the database already holds tasks, because merging two lists is not what the command is for.

## Layout

```
duewright/
├── duewright/
│   ├── __main__.py       # python -m duewright
│   ├── cli.py            # the menu and the commands, the only module that prints
│   ├── config.py         # where the tasks live, and which repository keeps them
│   ├── errors.py         # the errors the package raises
│   ├── models.py         # Task
│   ├── api/
│   │   ├── app.py        # the routes, and the one place errors are mapped
│   │   ├── deps.py       # what a route asks for, so a test can swap the store
│   │   └── schemas.py    # the shape a request has and a response always has
│   ├── repositories/
│   │   ├── base.py       # the interface a repository has to satisfy
│   │   ├── json_repo.py  # the only module that knows about JSON
│   │   ├── memory.py     # for tests
│   │   ├── migrate.py    # moving a JSON file into the database
│   │   └── sqlite_repo.py # the database, and the only module that knows SQL
│   ├── service.py        # the rules: ordering, overdue, filter, search, summary
│   └── validators.py     # pure functions for the input
├── scripts/
│   └── concurrency_demo.py   # what several processes writing at once costs
├── tests/
│   ├── test_api.py           # the routes, in process, over an in-memory store
│   ├── test_repositories.py  # the contract every repository has to satisfy
│   ├── test_json_repo.py     # the behaviours that belong to the file alone
│   ├── test_sqlite_repo.py   # the behaviours that belong to the database alone
│   ├── test_migrate.py       # moving the tasks over without losing any
│   └── ...
├── pyproject.toml
├── GLOSSARY.md
└── docs/adr/             # the decisions, and why they were taken
```

Four rules keep those apart, and they are the main lesson of the project:

1. Only `cli.py` calls `input()` or `print()`.
2. The service never touches the disk. It asks a repository, and only the repository modules know about files, JSON and SQL.
3. `validators.py` holds pure functions, so each rule is a short test.
4. The menu and the API both work through the same service, so a rule added for one is enforced in the other.

## What I would improve

- Editing the priority or the due date of a task that already exists. Only the title can be edited today, so fixing a wrong due date means deleting the task and adding it again.
- Sorting and paging in the store instead of in Python. Fine for a few hundred tasks, wrong for a hundred thousand.
- A fourth place to keep the tasks, such as PostgreSQL. The contract suite and the interface are in place, so a new backend is one class and no change to the rules.
- A warning when a task is about to become due.

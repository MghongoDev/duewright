# Duewright

Duewright is a command-line task manager. You pick an option from a menu to add, list, edit, mark done and delete tasks. Each task carries a title, a done flag and the moment it was created.

Tasks are numbered with a stable id, and an id is never handed to a second task, so a number you wrote down keeps pointing at the same task even after a deletion. This first version keeps tasks in memory, which means they vanish when you quit; saving them to a file is the next step.

The plan of record is [`duewright-implementation-guide.md`](./duewright-implementation-guide.md), which is kept in the repo so the reasoning behind each phase stays next to the code.

## Menu

```
1) Add a task
2) List tasks
3) Edit a task title
4) Mark a task done / undone
5) Delete a task
0) Quit
```

## Sample session

```
$ python main.py

Duewright

1) Add a task
...
Choose an option: 1
Title: Buy milk
[ ]  1  Buy milk
Choose an option: 1
Title: Call Sam
[ ]  1  Buy milk
[ ]  2  Call Sam
Choose an option: 4
Task id to mark: 1
[x]  1  Buy milk
[ ]  2  Call Sam
Choose an option: 5
Task id to delete: 2
[x]  1  Buy milk
Choose an option: 0
Goodbye.
```

A task looks like this:

```json
{
  "id": 1,
  "title": "Buy milk",
  "done": false,
  "created_at": "2026-10-18T17:52:04+00:00"
}
```

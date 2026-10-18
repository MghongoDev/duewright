# Duewright

A command-line task manager for one person: a list of tasks, edited through a menu, stored in a file on that person's machine.

## Language

**Task**:
A single thing the user has decided to do, carrying a title and the metadata Duewright records about it.
_Avoid_: item, entry, todo, to-do, record, note

**Task id**:
The stable integer that identifies a Task. An id names one Task for the life of the store and is never handed to a different Task.
_Avoid_: task number, index, position, row, key, ref

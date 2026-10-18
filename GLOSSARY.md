# Duewright

A command-line task manager for one person: a list of tasks, edited through a menu, stored in a file on that person's machine.

## Language

**Task**:
A single thing the user has decided to do, carrying a title and the metadata Duewright records about it.
_Avoid_: item, entry, todo, to-do, record, note

**Task id**:
The stable integer that identifies a Task. An id names one Task for the life of the store and is never handed to a different Task.
_Avoid_: task number, index, position, row, key, ref

**Pending**:
A Task the user has not marked done. Pending is what a Task is until someone says otherwise.
_Avoid_: open, active, outstanding, unfinished, incomplete

**Done**:
A Task the user has finished.
_Avoid_: complete, completed, closed, finished, resolved

**Priority**:
How urgent a Task is: low, medium or high. A Task is medium unless the user says otherwise.
_Avoid_: importance, urgency, severity

**Due date**:
The day by which a Task should be finished, or none. A Task with no due date is never late.
_Avoid_: deadline, target date, date

**Overdue**:
A pending Task whose due date is before today.
_Avoid_: late, past due, expired

**Due today**:
A pending Task whose due date is today. It is not overdue.
_Avoid_: due now, urgent today

**Due soon**:
A pending Task whose due date is after today and no more than three days away. It is not overdue, and it is not due today.
_Avoid_: upcoming, approaching, imminent, nearly due, almost due

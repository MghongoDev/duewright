# The tasks live in a folder under the user's home

Duewright keeps the store in a folder named `.duewright` inside the user's home folder. `DUEWRIGHT_DATA_DIR` points it somewhere else when someone wants that, which is also how the tests stay away from real tasks.

The first release kept the task file beside the code instead, and that failed in three ways. Reinstalling or upgrading the program could overwrite or delete it, because the file lived inside the thing being replaced. A second clone, or a checkout in another folder, quietly got a list of its own. And the file sat inside the working tree, so it turned up in `git status` and could be committed by accident. The comment in that code says the file was put at the top of the repository so that there would be one list rather than one per working folder, which shows the problem was seen and then answered in the wrong place.

A file in whatever folder the command happened to run from has the same fault in another shape: the list would change with the directory you were standing in. A system-wide folder, under `/var` or `ProgramData`, was the other candidate, and it lost because it needs administrator rights on some systems while this is a tool for one person rather than a service.

## Consequences

The folder is created the moment it is asked for, so no caller has to check whether it is there first. That means the function returning the folder also does something, which is worth knowing when reading it.

One machine holds one list. That suits a tool for one person, and it is also why the store has to cope with two copies of the program writing at once, which is what the database is for.

The folder name starts with a dot, which hides it on Linux and macOS and does nothing on Windows. The path is short enough to type and to pass to the migration command by hand.

# A task file from a newer version is refused

Duewright writes a version number into the task file, and refuses to open a file whose version is higher than the one it knows. Loading what it can would be tempting, because the loader already tolerates absent fields: a version 3 file would open, and the next save would write it back as version 2, quietly dropping whatever the newer version had added. Refusing costs the user one upgrade. Loading costs them data.

## Consequences

The version guard runs after the parse, so a file that is both newer and unreadable is reported as corrupt and kept aside, not reported as newer.

Opening a newer file with an older program means editing the version number down by hand. That is the right amount of friction for something deliberate.

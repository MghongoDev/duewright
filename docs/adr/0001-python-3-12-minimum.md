# Python 3.12 is the minimum supported version

The guide asks for 3.11 or newer and tests 3.11 and 3.13 in CI. This machine runs 3.12, 3.13 and 3.14, and has no 3.11, and the project's Docker image is `python:3.12-slim`. We set `requires-python = ">=3.12"`, mypy's `python_version` to `3.12`, and the CI matrix to 3.12 and 3.13, so the declared floor is a version we can both run and test here. A floor nobody can reproduce hides bugs rather than catching them.

## Considered options

- **3.11**, the guide's floor: rejected because 3.11 is not installed on this machine, so the floor could not be run or tested without adding an interpreter for no other reason.
- **3.14**: rejected as the newest interpreter available, which buys nothing this project needs.

## Consequences

The floor sits one minor version above the guide. Raising it later is a one-line change. Lowering it means auditing the code for syntax that 3.11 rejects.

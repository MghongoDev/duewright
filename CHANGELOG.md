# Changelog

Notable changes to this project. The versions follow semantic versioning, and the format follows Keep a Changelog.

## 1.0.0

### Added

- The REST API under `/api/v1`, over the same service the menu uses: list with filtering, search and paging, create, read, change and delete.
- The API key, required by every route that holds data, compared in constant time, failing closed when none is configured, and refused at startup when it is missing or shorter than sixteen characters.
- `duewright serve`, which binds to the loopback address unless it is told otherwise.
- The Docker image, with the tasks in a volume and the container running as a user that is not root.
- A plain 500 answer for unexpected errors, with no traceback and no file paths in it.
- Continuous integration on Linux and Windows, on Python 3.12 and 3.13, with the image built and smoke-tested on every push.

### Changed

- The default store is the SQLite database rather than the JSON file, because it is the only one that survives two copies of the program writing at once. Set `DUEWRIGHT_BACKEND=json` for the earlier behaviour.
- The title and priority rules moved from the menu into the service, so both interfaces enforce the same ones.
- Coverage is measured across subprocesses, so the menu's process tests count. The suite reports 87% rather than the 69% a measurement blind to subprocesses shows.

## 0.1.0

### Added

- The menu: add a task, list, edit a title, mark done or undone, delete, filter and search.
- Tasks with a stable id that is never handed out twice, a priority and an optional due date, ordered with pending first and then by due date, priority and id.
- The JSON store, with writes swapped into place in one step, a damaged file kept aside rather than overwritten, and a file from a newer version refused.
- The data folder under the user's home folder, which `DUEWRIGHT_DATA_DIR` overrides.

### Notes

- This release came before the repository interface, the database, the API and the image.

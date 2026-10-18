"""Tests for the menu, run as a process so the real entry point is exercised."""

import json
import os
import socket
import subprocess
import sys
import time

import httpx

CREATED = "2026-10-18T17:52:04+00:00"
TEST_KEY = "test-key-1234567890"
HEADER = {"X-API-Key": TEST_KEY}


def run_menu(answers, data_dir, cwd, backend=None):
    """Run the menu as a process, with the data folder pointed somewhere temporary."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(data_dir))
    if backend is None:
        environment.pop("DUEWRIGHT_BACKEND", None)
    else:
        environment["DUEWRIGHT_BACKEND"] = backend
    return subprocess.run(
        [sys.executable, "-m", "duewright"],
        input=answers,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        cwd=str(cwd),
    )


def run_command(arguments, data_dir, cwd):
    """Run one of the operational commands as a process."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(data_dir))
    environment.pop("DUEWRIGHT_BACKEND", None)
    return subprocess.run(
        [sys.executable, "-m", "duewright", *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=environment,
        cwd=str(cwd),
    )


def write_a_file(path):
    """A task file holding one task."""
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "next_id": 2,
                "tasks": [
                    {
                        "id": 1,
                        "title": "Buy milk",
                        "done": False,
                        "created_at": CREATED,
                        "priority": "high",
                        "due_date": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_the_menu_writes_its_tasks_to_the_data_folder(tmp_path):
    """The default store is the database, and it lands in the configured folder."""
    result = run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "tasks.db").exists()


def test_the_menu_can_use_the_json_file_instead(tmp_path):
    """The setting picks the other store, and the database is left alone."""
    result = run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path, backend="json")
    assert result.returncode == 0
    assert (tmp_path / "tasks.json").exists()
    assert not (tmp_path / "tasks.db").exists()


def test_the_menu_keeps_the_tasks_between_runs(tmp_path):
    """A second run reads what the first one wrote, whatever the store is."""
    run_menu("1\nBuy milk\nhigh\n\n0\n", tmp_path, tmp_path)
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert "Buy milk" in result.stdout
    assert "1 pending, 0 overdue, 0 done" in result.stdout


def test_the_menu_reports_a_json_file_it_cannot_read(tmp_path):
    """A damaged file is kept aside, reported, and the menu still starts."""
    (tmp_path / "tasks.json").write_text('{"version": 2, "tasks": [', encoding="utf-8")
    result = run_menu("2\n0\n", tmp_path, tmp_path, backend="json")
    assert result.returncode == 0
    assert "could not be read" in result.stdout
    assert "No tasks yet." in result.stdout
    kept = [entry.name for entry in tmp_path.iterdir() if ".corrupt-" in entry.name]
    assert len(kept) == 1


def test_the_menu_reports_a_database_it_cannot_read(tmp_path):
    """A file that is not a database is reported rather than crashing the menu."""
    (tmp_path / "tasks.db").write_text("this is not a database", encoding="utf-8")
    result = run_menu("2\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert "could not be read" in result.stdout


def test_the_menu_refuses_a_json_file_from_a_newer_version(tmp_path):
    """A store from a newer version stops the program instead of being overwritten."""
    newer = '{"version": 99, "next_id": 1, "tasks": []}'
    (tmp_path / "tasks.json").write_text(newer, encoding="utf-8")
    result = run_menu("0\n", tmp_path, tmp_path, backend="json")
    assert "Cannot start" in result.stdout
    assert "Goodbye" not in result.stdout
    assert (tmp_path / "tasks.json").read_text(encoding="utf-8") == newer


def test_the_menu_refuses_a_backend_it_does_not_have(tmp_path):
    """A typo in the setting stops the program rather than quietly ignoring it."""
    result = run_menu("0\n", tmp_path, tmp_path, backend="postgres")
    assert "Cannot start" in result.stdout
    assert "Goodbye" not in result.stdout


def test_the_migration_command_moves_the_tasks(tmp_path):
    """The command moves the file's tasks into the database the menu then reads."""
    source = tmp_path / "tasks.json"
    write_a_file(source)
    result = run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    assert result.returncode == 0
    assert "Moved 1 tasks" in result.stdout
    listing = run_menu("2\n0\n", tmp_path, tmp_path)
    assert "Buy milk" in listing.stdout
    assert "1 pending, 0 overdue, 0 done" in listing.stdout


def test_the_migration_command_dry_run_writes_nothing(tmp_path):
    source = tmp_path / "tasks.json"
    write_a_file(source)
    result = run_command(["migrate-json", str(source), "--dry-run"], tmp_path, tmp_path)
    assert result.returncode == 0
    assert "dry run" in result.stdout
    assert not (tmp_path / "tasks.db").exists()


def test_the_migration_command_refuses_a_database_that_holds_tasks(tmp_path):
    source = tmp_path / "tasks.json"
    write_a_file(source)
    run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    again = run_command(["migrate-json", str(source)], tmp_path, tmp_path)
    assert again.returncode == 1
    assert "already holds" in again.stdout


def test_an_unknown_command_says_so(tmp_path):
    result = run_command(["sing"], tmp_path, tmp_path)
    assert result.returncode == 2
    assert "is not a command" in result.stdout


def free_port():
    """A port nothing is listening on."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def start_server(tmp_path, *arguments, key=TEST_KEY):
    """Start the server as a process, with its log going to a file."""
    environment = dict(os.environ, DUEWRIGHT_DATA_DIR=str(tmp_path))
    environment.pop("DUEWRIGHT_BACKEND", None)
    if key is None:
        environment.pop("DUEWRIGHT_API_KEY", None)
    else:
        environment["DUEWRIGHT_API_KEY"] = key
    log = open(tmp_path / "server.log", "w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-m", "duewright", "serve", *arguments],
        env=environment,
        cwd=str(tmp_path),
        stdout=log,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
    )
    return process, log


def server_log(tmp_path):
    """What the server wrote to its log."""
    return (tmp_path / "server.log").read_text(encoding="utf-8")


def wait_for_health(port, tmp_path, timeout=60.0):
    """Wait until the server answers, then return that response."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return httpx.get(f"http://127.0.0.1:{port}/health", timeout=5.0)
        except httpx.HTTPError:
            time.sleep(0.25)
    raise AssertionError(f"the server never answered:\n{server_log(tmp_path)}")


def test_the_serve_command_answers_over_http(tmp_path):
    """The server starts where it is told, and health answers without a key."""
    port = free_port()
    server, log = start_server(tmp_path, "--port", str(port))
    try:
        health = wait_for_health(port, tmp_path)
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
        created = httpx.post(
            f"http://127.0.0.1:{port}/api/v1/tasks",
            json={"title": "Buy milk", "priority": "high"},
            headers=HEADER,
            timeout=10.0,
        )
        assert created.status_code == 201
        listed = httpx.get(
            f"http://127.0.0.1:{port}/api/v1/tasks", headers=HEADER, timeout=10.0
        ).json()
        assert listed["total"] == 1
        assert listed["items"][0]["title"] == "Buy milk"
    finally:
        server.terminate()
        server.wait(timeout=30)
        log.close()


def test_a_real_server_refuses_a_request_without_the_key(tmp_path):
    """The key is enforced by the server, not only by the test client."""
    port = free_port()
    server, log = start_server(tmp_path, "--port", str(port))
    try:
        wait_for_health(port, tmp_path)
        refused = httpx.get(f"http://127.0.0.1:{port}/api/v1/tasks", timeout=10.0)
        assert refused.status_code == 401
        allowed = httpx.get(f"http://127.0.0.1:{port}/api/v1/tasks", headers=HEADER, timeout=10.0)
        assert allowed.status_code == 200
    finally:
        server.terminate()
        server.wait(timeout=30)
        log.close()


def test_the_serve_command_refuses_to_start_without_a_key(tmp_path):
    """A server with no key would be open to anything that can reach the port."""
    server, log = start_server(tmp_path, "--port", str(free_port()), key=None)
    try:
        assert server.wait(timeout=30) == 2
        assert "DUEWRIGHT_API_KEY is not set" in server_log(tmp_path)
        assert "token_urlsafe" in server_log(tmp_path)
    finally:
        log.close()


def test_the_serve_command_refuses_a_key_that_is_too_short(tmp_path):
    server, log = start_server(tmp_path, "--port", str(free_port()), key="short")
    try:
        assert server.wait(timeout=30) == 2
        assert "shorter than 16 characters" in server_log(tmp_path)
    finally:
        log.close()


def test_a_task_crosses_between_the_menu_and_the_api(tmp_path):
    """A task created over HTTP is in the menu, and one added in the menu is over HTTP."""
    port = free_port()
    server, log = start_server(tmp_path, "--port", str(port))
    try:
        wait_for_health(port, tmp_path)
        created = httpx.post(
            f"http://127.0.0.1:{port}/api/v1/tasks",
            json={"title": "Added over HTTP"},
            headers=HEADER,
            timeout=10.0,
        )
        assert created.status_code == 201

        listed = run_menu("2\n0\n", tmp_path, tmp_path)
        assert "Added over HTTP" in listed.stdout

        run_menu("1\nAdded in the menu\nlow\n\n0\n", tmp_path, tmp_path)
        over_http = httpx.get(
            f"http://127.0.0.1:{port}/api/v1/tasks", headers=HEADER, timeout=10.0
        ).json()
        assert over_http["total"] == 2
        titles = {task["title"] for task in over_http["items"]}
        assert titles == {"Added over HTTP", "Added in the menu"}
    finally:
        server.terminate()
        server.wait(timeout=30)
        log.close()


def edit_and_list(answers, data_dir, cwd):
    """Add a task, then run the menu again with the given answers."""
    run_menu("1\nPay the rent\nmedium\n2026-11-01\n0\n", data_dir, cwd)
    return run_menu(answers, data_dir, cwd)


def test_the_menu_can_change_a_priority(tmp_path):
    """A blank title and a blank due date keep what the task already has."""
    result = edit_and_list("3\n1\n\nhigh\n\n0\n", tmp_path, tmp_path)
    assert result.returncode == 0
    assert "Pay the rent" in result.stdout
    assert "high" in result.stdout
    assert "due 2026-11-01" in result.stdout


def test_the_menu_can_change_a_due_date(tmp_path):
    result = edit_and_list("3\n1\n\n\n2026-12-24\n0\n", tmp_path, tmp_path)
    assert "due 2026-12-24" in result.stdout


def test_the_menu_can_clear_a_due_date(tmp_path):
    result = edit_and_list("3\n1\n\n\nnone\n0\n", tmp_path, tmp_path)
    assert "due 2026-11-01" not in result.stdout
    assert "Pay the rent" in result.stdout


def test_the_menu_can_change_a_title_as_before(tmp_path):
    result = edit_and_list("3\n1\nPay the water bill\n\n\n0\n", tmp_path, tmp_path)
    assert "1  Pay the water bill" in result.stdout


def test_a_blank_answer_to_every_field_changes_nothing(tmp_path):
    result = edit_and_list("3\n1\n\n\n\n0\n", tmp_path, tmp_path)
    assert "Nothing was changed." in result.stdout
    assert "due 2026-11-01" in result.stdout


def test_an_answer_that_makes_no_sense_is_asked_again(tmp_path):
    """The bad answer is refused, and the question comes back."""
    result = edit_and_list("3\n1\n\nurgent\nhigh\n\n0\n", tmp_path, tmp_path)
    assert "Priority is low, medium or high." in result.stdout
    assert "high" in result.stdout


def test_editing_a_task_that_is_not_there_changes_nothing(tmp_path):
    result = edit_and_list("3\n99\n\nhigh\n\n0\n", tmp_path, tmp_path)
    assert "No task with id 99." in result.stdout
    assert "Goodbye." in result.stdout

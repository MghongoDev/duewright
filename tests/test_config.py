"""Tests for where the tasks are kept."""

import pytest

from duewright import config
from duewright.errors import UnknownBackendError
from duewright.repositories.json_repo import JsonTaskRepository
from duewright.repositories.sqlite_repo import SqliteTaskRepository


def test_data_dir_uses_the_environment_variable(monkeypatch, tmp_path):
    """The environment variable decides the folder, which is what keeps tests off real data."""
    monkeypatch.setenv("DUEWRIGHT_DATA_DIR", str(tmp_path))
    assert config.data_dir() == tmp_path


def test_data_dir_defaults_to_a_folder_in_the_home_folder(monkeypatch, tmp_path):
    """With no override, the folder sits under the home folder, named for the program."""
    monkeypatch.delenv("DUEWRIGHT_DATA_DIR", raising=False)
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    assert config.data_dir() == tmp_path / ".duewright"


def test_data_dir_creates_the_folder(monkeypatch, tmp_path):
    """The folder is created on demand, so nothing has to make it first."""
    target = tmp_path / "nested" / "duewright"
    monkeypatch.setenv("DUEWRIGHT_DATA_DIR", str(target))
    config.data_dir()
    assert target.is_dir()


@pytest.fixture
def data_folder(monkeypatch, tmp_path):
    """Point the data folder at a temporary one for the backend tests."""
    monkeypatch.setenv("DUEWRIGHT_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DUEWRIGHT_BACKEND", raising=False)
    return tmp_path


def test_the_backend_defaults_to_the_database(data_folder):
    """Two copies of the program can use a database at once, so it is the default."""
    assert isinstance(config.make_repository(), SqliteTaskRepository)


def test_the_backend_can_be_the_json_file(data_folder, monkeypatch):
    monkeypatch.setenv("DUEWRIGHT_BACKEND", "json")
    assert isinstance(config.make_repository(), JsonTaskRepository)


def test_the_backend_can_be_named_in_any_case(data_folder, monkeypatch):
    monkeypatch.setenv("DUEWRIGHT_BACKEND", "JSON")
    assert isinstance(config.make_repository(), JsonTaskRepository)


def test_the_json_backend_points_at_the_task_file(data_folder, monkeypatch):
    monkeypatch.setenv("DUEWRIGHT_BACKEND", "json")
    repository = config.make_repository()
    assert isinstance(repository, JsonTaskRepository)
    assert repository.path == data_folder / "tasks.json"


def test_the_database_backend_points_at_the_database_file(data_folder):
    repository = config.make_repository()
    assert isinstance(repository, SqliteTaskRepository)
    assert repository.path == data_folder / "tasks.db"


def test_an_unknown_backend_is_refused(data_folder, monkeypatch):
    """A typo in the setting fails loudly rather than quietly using the default."""
    monkeypatch.setenv("DUEWRIGHT_BACKEND", "postgres")
    with pytest.raises(UnknownBackendError):
        config.make_repository()

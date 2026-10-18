"""Tests for where the tasks are kept."""

from duewright import config


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

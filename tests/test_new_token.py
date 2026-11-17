import re

import pytest

from src.magutils.env.main import new_token


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.magutils.env.main._find_env", lambda: None)


def assert_hex_token(token, nbytes):
    assert isinstance(token, str)
    assert len(token) == 2 * nbytes
    assert re.fullmatch(r"[0-9a-fA-F]*", token) is not None


def test_defaults_create_env_with_token(tmp_path):
    token = new_token()

    assert_hex_token(token, 32)
    assert (tmp_path / ".env").read_text().splitlines() == [f"TOKEN={token}"]


@pytest.mark.parametrize("nbytes", [0, 1, 7, 32, 64])
def test_requested_token_length_without_writing(tmp_path, nbytes):
    token = new_token(nbytes=nbytes, write_file=False)

    assert_hex_token(token, nbytes)
    assert not (tmp_path / ".env").exists()


def test_custom_key_and_length_are_written(tmp_path):
    token = new_token(key="API_SECRET", nbytes=7, write_file=True)

    assert_hex_token(token, 7)
    assert (tmp_path / ".env").read_text().splitlines() == [f"API_SECRET={token}"]


def test_zero_byte_token_can_be_written(tmp_path):
    token = new_token(nbytes=0)

    assert token == ""
    assert (tmp_path / ".env").read_text().splitlines() == ["TOKEN="]


def test_disabled_writing_preserves_existing_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    original = b"# existing settings\nTOKEN=old\nOTHER=value"
    env_file.write_bytes(original)
    monkeypatch.setattr("src.magutils.env.main._find_env", lambda: env_file)

    token = new_token(write_file=False)

    assert_hex_token(token, 32)
    assert env_file.read_bytes() == original


@pytest.mark.parametrize("ending", ["\n", ""])
def test_append_preserves_content_and_separates_last_line(
    tmp_path, monkeypatch, ending
):
    env_file = tmp_path / ".env"
    original = f"# saved settings\n\nOTHER=value{ending}".encode()
    env_file.write_bytes(original)
    monkeypatch.setattr("src.magutils.env.main._find_env", lambda: env_file)

    token = new_token()

    assert env_file.read_bytes().startswith(original)
    assert env_file.read_text().splitlines() == [
        "# saved settings", "", "OTHER=value", f"TOKEN={token}"
    ]


def test_repeated_writes_remain_separate_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    monkeypatch.setattr(
        "src.magutils.env.main._find_env",
        lambda: env_file if env_file.exists() else None,
    )

    first = new_token()
    second = new_token()
    third = new_token(key="SECOND_KEY")

    assert env_file.read_text().splitlines() == [
        f"TOKEN={first}", f"TOKEN={second}", f"SECOND_KEY={third}"
    ]


def test_found_file_outside_cwd_receives_token(tmp_path, monkeypatch):
    working_dir = tmp_path / "working"
    working_dir.mkdir()
    env_file = tmp_path / ".env"
    original = b"OTHER=preserved\n"
    env_file.write_bytes(original)
    monkeypatch.chdir(working_dir)
    monkeypatch.setattr("src.magutils.env.main._find_env", lambda: env_file)

    token = new_token(key="EXTERNAL_TOKEN")

    assert env_file.read_bytes().startswith(original)
    assert env_file.read_text().splitlines() == [
        "OTHER=preserved", f"EXTERNAL_TOKEN={token}"
    ]
    assert not (working_dir / ".env").exists()

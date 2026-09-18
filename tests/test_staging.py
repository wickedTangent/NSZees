from pathlib import Path

from nszees.services.staging import is_risky_backend_path, stage_input_copy


def test_short_ascii_path_not_risky():
    assert is_risky_backend_path(Path("C:/Games/Mario.nsp")) is False


def test_long_path_is_risky():
    long_name = "A" * 250 + ".nsp"
    assert is_risky_backend_path(Path("C:/") / long_name) is True


def test_non_ascii_path_is_risky():
    assert is_risky_backend_path(Path("C:/Games/マリオ.nsp")) is True


def test_stage_input_copy_creates_ascii_named_copy(tmp_path):
    source = tmp_path / "マリオ.nsp"
    source.write_bytes(b"data")
    staged = stage_input_copy(source, tmp_path)
    assert staged.exists()
    assert staged.name == "staged_input.nsp"
    assert staged.read_bytes() == b"data"


def test_stage_input_copy_avoids_collision(tmp_path):
    source = tmp_path / "game.nsp"
    source.write_bytes(b"data1")
    staged1 = stage_input_copy(source, tmp_path)
    staged2 = stage_input_copy(source, tmp_path)
    assert staged1 != staged2
    assert staged2.name == "staged_input_1.nsp"

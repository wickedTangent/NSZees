import json

from nszees.services.app_settings import load_last_input_dir, save_last_input_dir


def test_load_returns_none_when_no_settings(tmp_path):
    assert load_last_input_dir(tmp_path) is None


def test_save_then_load_round_trips(tmp_path):
    target_dir = tmp_path / "roms"
    target_dir.mkdir()
    save_last_input_dir(tmp_path, target_dir)
    assert load_last_input_dir(tmp_path) == target_dir


def test_load_returns_none_if_dir_no_longer_exists(tmp_path):
    target_dir = tmp_path / "roms"
    target_dir.mkdir()
    save_last_input_dir(tmp_path, target_dir)
    target_dir.rmdir()
    assert load_last_input_dir(tmp_path) is None


def test_save_preserves_other_settings_keys(tmp_path):
    settings_path = tmp_path / "config" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")

    target_dir = tmp_path / "roms"
    target_dir.mkdir()
    save_last_input_dir(tmp_path, target_dir)

    data = json.loads(settings_path.read_text(encoding="utf-8"))
    assert data["other_key"] == "value"
    assert data["last_input_dir"] == str(target_dir)


def test_load_handles_corrupt_json(tmp_path):
    settings_path = tmp_path / "config" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("not valid json{{{", encoding="utf-8")
    assert load_last_input_dir(tmp_path) is None

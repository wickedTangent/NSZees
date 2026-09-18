import os

import pytest

from nszees.nsz.wrapper import NszCommandError, NszResult, NszRunner


def test_subprocess_env_forces_utf8_without_dropping_other_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("SOME_UNRELATED_VAR", "keep-me")
    runner = NszRunner(app_root=tmp_path)
    env = runner._subprocess_env()
    assert env["PYTHONIOENCODING"] == "UTF-8"
    assert env["SOME_UNRELATED_VAR"] == "keep-me"
    assert env is not os.environ


def test_keys_args_empty_when_no_prod_keys(tmp_path):
    runner = NszRunner(app_root=tmp_path)
    assert runner._keys_args() == []


def test_keys_args_includes_keys_flag_when_present(tmp_path):
    prod_keys = tmp_path / "prod.keys"
    prod_keys.write_text("master_key_00=deadbeef\n", encoding="utf-8")
    runner = NszRunner(app_root=tmp_path)
    assert runner._keys_args() == ["--keys", str(prod_keys)]


def test_ensure_backend_present_raises_when_missing(tmp_path):
    runner = NszRunner(app_root=tmp_path)
    with pytest.raises(NszCommandError):
        runner._ensure_backend_present()


def test_nsz_result_ok_property():
    assert NszResult(command=("nsz",), return_code=0, stdout="", stderr="").ok is True
    assert NszResult(command=("nsz",), return_code=1, stdout="", stderr="").ok is False


def test_compress_maximum_uses_solid_mode_for_nsp(tmp_path, monkeypatch):
    captured_args = {}

    def fake_run_cancellable(self, args, stop_requested=None):
        captured_args["args"] = args
        return NszResult(command=tuple(args), return_code=0, stdout="", stderr=""), False

    monkeypatch.setattr(NszRunner, "_run_cancellable", fake_run_cancellable)
    nsp_path = tmp_path / "game.nsp"
    nsp_path.write_bytes(b"")

    runner = NszRunner(app_root=tmp_path)
    runner.compress_maximum_cancellable(nsp_path)

    assert "--solid" in captured_args["args"]
    assert "--block" not in captured_args["args"]


def test_compress_maximum_uses_block_mode_for_xci(tmp_path, monkeypatch):
    captured_args = {}

    def fake_run_cancellable(self, args, stop_requested=None):
        captured_args["args"] = args
        return NszResult(command=tuple(args), return_code=0, stdout="", stderr=""), False

    monkeypatch.setattr(NszRunner, "_run_cancellable", fake_run_cancellable)
    xci_path = tmp_path / "game.xci"
    xci_path.write_bytes(b"")

    runner = NszRunner(app_root=tmp_path)
    runner.compress_maximum_cancellable(xci_path)

    assert "--block" in captured_args["args"]
    assert "--solid" not in captured_args["args"]

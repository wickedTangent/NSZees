import struct

from nszees.services.validator import FileValidator


def _minimal_valid_pfs0_bytes() -> bytes:
    file_count, string_table_size = 1, 8
    header = b"PFS0" + struct.pack("<II", file_count, string_table_size) + b"\x00\x00\x00\x00"
    body_size = 16 + file_count * 24 + string_table_size
    return header + b"\x00" * (body_size - len(header))


def test_validate_skips_signature_check_when_quick_verify_fails(tmp_path, monkeypatch):
    validator = FileValidator()
    p = tmp_path / "bad.nsp"
    p.write_bytes(_minimal_valid_pfs0_bytes())

    class _FailingResult:
        ok = False
        return_code = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(validator.nsz_runner, "quick_verify", lambda path: _FailingResult())
    monkeypatch.setattr(
        "nszees.services.validator.check_package_signature",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("signature check should not run")),
    )

    result = validator.validate(str(p))
    assert result.signature_checked is False
    assert result.signature_valid is None


def test_validate_rejects_unsupported_extension(tmp_path):
    validator = FileValidator()
    p = tmp_path / "not_a_game.txt"
    p.write_text("hello", encoding="utf-8")
    result = validator.validate(str(p))
    assert result.container_valid is False
    assert result.can_compress is False
    assert "Unsupported file type" in result.container_error


def test_validate_accepts_xci_and_skips_pfs0_structural_check(tmp_path, monkeypatch):
    validator = FileValidator()
    p = tmp_path / "game.xci"
    p.write_bytes(b"not a real xci - garbage bytes, HFS0 not PFS0")

    monkeypatch.setattr(
        "nszees.services.validator.inspect_key_requirement",
        lambda *a, **k: type("KR", (), {"required_key_name": None, "required_key_present": None})(),
    )

    class _PassingResult:
        ok = True
        return_code = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(validator.nsz_runner, "quick_verify", lambda path: _PassingResult())
    monkeypatch.setattr(
        "nszees.services.validator.check_package_signature",
        lambda *a, **k: type("SR", (), {"checked": False, "valid": None})(),
    )

    result = validator.validate(str(p))
    assert result.container_valid is True
    assert result.container_error is None
    assert result.primary_action == "compress"
    assert result.can_compress is True


def test_validate_treats_xcz_as_compressed_for_primary_action(tmp_path, monkeypatch):
    validator = FileValidator()
    p = tmp_path / "game.xcz"
    p.write_bytes(b"not a real xcz")

    monkeypatch.setattr(
        "nszees.services.validator.inspect_key_requirement",
        lambda *a, **k: type("KR", (), {"required_key_name": None, "required_key_present": None})(),
    )

    class _FailingResult:
        ok = False
        return_code = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(validator.nsz_runner, "quick_verify", lambda path: _FailingResult())

    result = validator.validate(str(p))
    assert result.primary_action == "decompress"
    assert result.can_force_compress is False


def test_validate_container_check_failure_skips_quick_verify(tmp_path, monkeypatch):
    validator = FileValidator()
    p = tmp_path / "bad.nsp"
    p.write_bytes(b"not a real nsp - too short")

    def fake_quick_verify(path):
        raise AssertionError("quick_verify should not run when container check fails")

    monkeypatch.setattr(validator.nsz_runner, "quick_verify", fake_quick_verify)

    result = validator.validate(str(p))
    assert result.container_valid is False
    assert result.can_compress is False
    assert result.can_force_compress is False

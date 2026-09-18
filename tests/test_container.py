import struct

from nszees.checks.container import check_pfs0_container


def _pfs0_bytes(file_count=1, string_table_size=8, total_size=None, magic=b"PFS0"):
    header = magic + struct.pack("<II", file_count, string_table_size) + b"\x00\x00\x00\x00"
    if total_size is None:
        total_size = 16 + file_count * 24 + string_table_size
    body = b"\x00" * max(0, total_size - len(header))
    return header + body


def test_valid_pfs0(tmp_path):
    p = tmp_path / "game.nsp"
    p.write_bytes(_pfs0_bytes())
    ok, err = check_pfs0_container(str(p))
    assert ok is True
    assert err is None


def test_missing_file(tmp_path):
    p = tmp_path / "missing.nsp"
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "not found" in err.lower()


def test_directory_is_not_a_file(tmp_path):
    ok, err = check_pfs0_container(str(tmp_path))
    assert ok is False
    assert "not a file" in err.lower()


def test_too_small(tmp_path):
    p = tmp_path / "tiny.nsp"
    p.write_bytes(b"\x00" * 10)
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "too small" in err.lower()


def test_bad_magic(tmp_path):
    p = tmp_path / "bad.nsp"
    p.write_bytes(_pfs0_bytes(magic=b"XXXX"))
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "invalid pfs0 magic" in err.lower()


def test_zero_file_count(tmp_path):
    p = tmp_path / "zero.nsp"
    p.write_bytes(_pfs0_bytes(file_count=0, string_table_size=0, total_size=16))
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "zero" in err.lower()


def test_suspicious_file_count(tmp_path):
    p = tmp_path / "huge.nsp"
    p.write_bytes(_pfs0_bytes(file_count=20000, string_table_size=0, total_size=16 + 20000 * 24))
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "suspicious file count" in err.lower()


def test_string_table_too_large(tmp_path):
    p = tmp_path / "strtab.nsp"
    p.write_bytes(_pfs0_bytes(file_count=1, string_table_size=11 * 1024 * 1024, total_size=40))
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "string table too large" in err.lower()


def test_header_exceeds_file_size(tmp_path):
    p = tmp_path / "short.nsp"
    # Header claims 5 file entries (needs 16 + 5*24 = 136 bytes) but the file is tiny.
    p.write_bytes(_pfs0_bytes(file_count=5, string_table_size=0, total_size=20))
    ok, err = check_pfs0_container(str(p))
    assert ok is False
    assert "exceeds file size" in err.lower()

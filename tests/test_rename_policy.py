from nsz.Fs.Xci import Xci

import nszees.services.rename_policy as rename_policy
from nszees.services.rename_policy import build_renamed_output_name


def test_base_package_simple(tmp_path):
    source = tmp_path / "Hello, Mario! [01007FE0221D8000][v0].nsp"
    assert build_renamed_output_name(source, tmp_path) == "Hello, Mario! [01007FE0221D8000][v0].nsz"


def test_title_id_normalized_to_uppercase(tmp_path):
    source = tmp_path / "Some Game [01007fe0221d8000][v0].nsp"
    assert build_renamed_output_name(source, tmp_path) == "Some Game [01007FE0221D8000][v0].nsz"


def test_update_with_display_version(tmp_path):
    source = tmp_path / "Some Game [0100000000010000][v65536][1.1.0].nsp"
    result = build_renamed_output_name(source, tmp_path)
    assert result == "Some Game [0100000000010000][v65536][v1.1.0].nsz"


def test_preserves_region_passthrough_tag(tmp_path):
    source = tmp_path / "Some Game [JP][0100000000010000][v0].nsp"
    assert build_renamed_output_name(source, tmp_path) == "Some Game [0100000000010000][JP][v0].nsz"


def test_returns_none_when_no_tags_and_not_a_real_package(tmp_path):
    source = tmp_path / "RandomFile.nsp"
    source.write_bytes(b"not a real nsp")
    assert build_renamed_output_name(source, tmp_path) is None


def test_xci_source_gets_xcz_output_extension(tmp_path):
    source = tmp_path / "Hello, Mario! [01007FE0221D8000][v0].xci"
    assert build_renamed_output_name(source, tmp_path) == "Hello, Mario! [01007FE0221D8000][v0].xcz"


def test_xci_metadata_fallback_looks_inside_secure_partition(tmp_path, monkeypatch):
    """XCI keeps ticket/cnmt nested in a "secure" HFS0 partition, unlike NSP's
    flat file list - the internal-metadata fallback needs to look there
    instead of calling Nsp-only ticket()/cnmt() methods."""

    class FakeCnmtFile:
        _path = "test.cnmt"
        version = 65536

        def open(self, *args, **kwargs):
            pass

    class FakeCnmtNca:
        _path = "abc.cnmt.nca"

        def __iter__(self):
            return iter([[FakeCnmtFile()]])

    rights_id_int = 0x0102030405060708090A0B0C0D0E0F10

    class FakeTicket(rename_policy.Ticket):
        def __init__(self):
            pass

        def getRightsId(self):
            return rights_id_int

        def close(self):
            pass

    class FakeSecurePartition:
        _path = "secure"

        def __iter__(self):
            return iter([FakeTicket(), FakeCnmtNca()])

    class FakeXci(Xci):
        def __init__(self):
            pass

        def open(self, *args, **kwargs):
            pass

        def close(self):
            pass

        @property
        def hfs0(self):
            return [FakeSecurePartition()]

    monkeypatch.setattr(rename_policy, "factory", lambda path: FakeXci())

    source = tmp_path / "SomeGame.xci"
    source.write_bytes(b"")
    title_id, version_int = rename_policy._extract_from_internal_metadata(source, tmp_path)
    assert title_id == format(rights_id_int, "X").zfill(32)[:16]
    assert version_int == "65536"

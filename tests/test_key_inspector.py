from nsz.Fs.Nca import Nca
from nsz.Fs.Xci import Xci

import nszees.services.key_inspector as key_inspector
from nszees.services.key_inspector import _read_available_keys, inspect_key_requirement


def test_read_available_keys_missing_file(tmp_path):
    assert _read_available_keys(tmp_path / "prod.keys") == set()


def test_read_available_keys_parses_key_names(tmp_path):
    p = tmp_path / "prod.keys"
    p.write_text(
        "master_key_00 = deadbeef\nmaster_key_11=cafebabe\n# comment\ninvalid line\n",
        encoding="utf-8",
    )
    keys = _read_available_keys(p)
    assert keys == {"master_key_00", "master_key_11"}


def test_inspect_key_requirement_returns_empty_result_for_invalid_package(tmp_path):
    package_path = tmp_path / "bad.nsp"
    package_path.write_bytes(b"not a real nsp")
    result = inspect_key_requirement(package_path, tmp_path)
    assert result.master_key_revision is None
    assert result.required_key_name is None
    assert result.required_key_present is None
    assert result.rights_id is None


def test_inspect_key_requirement_finds_nca_inside_xci_secure_partition(tmp_path, monkeypatch):
    """Xci isn't directly iterable like Nsp - its NCAs live nested inside a
    "secure" HFS0 partition reachable via package.hfs0. Regression test for a
    bug where every XCI silently produced an empty KeyRequirement because
    `for entry in package` raised TypeError on a bare Xci object."""

    class FakeHeader:
        masterKey = 0x11

        def getRightsId(self):
            return 0

    class FakeNca(Nca):
        def __init__(self):
            self.header = FakeHeader()

        def close(self):
            pass

    class FakeSecurePartition:
        _path = "secure"

        def __iter__(self):
            return iter([FakeNca()])

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

    monkeypatch.setattr(key_inspector, "factory", lambda path: FakeXci())

    package_path = tmp_path / "SomeGame.xci"
    package_path.write_bytes(b"")
    prod_keys = tmp_path / "prod.keys"
    prod_keys.write_text("master_key_11=deadbeef\n", encoding="utf-8")

    result = inspect_key_requirement(package_path, tmp_path)
    assert result.master_key_revision == 0x11
    assert result.required_key_name == "master_key_11"
    assert result.required_key_present is True

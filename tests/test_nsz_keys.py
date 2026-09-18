from nsz.nut import Keys

from nszees.services import nsz_keys


def test_sync_is_a_noop_when_prod_keys_missing(tmp_path):
    # Must not raise even though prod.keys doesn't exist.
    nsz_keys.sync(tmp_path)


def test_sync_loads_the_given_prod_keys_file(tmp_path):
    prod_keys = tmp_path / "prod.keys"
    prod_keys.write_text("master_key_00=" + "00" * 16 + "\n", encoding="utf-8")

    nsz_keys.sync(tmp_path)

    assert Keys.loadedKeysFile == str(prod_keys)

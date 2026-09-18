from nszees.naming import unique_destination_path


def test_returns_unchanged_when_free(tmp_path):
    target = tmp_path / "game.nsz"
    assert unique_destination_path(target) == target


def test_appends_1_when_taken(tmp_path):
    target = tmp_path / "game.nsz"
    target.write_bytes(b"x")
    assert unique_destination_path(target) == tmp_path / "game (1).nsz"


def test_increments_past_multiple_collisions(tmp_path):
    target = tmp_path / "game.nsz"
    target.write_bytes(b"x")
    (tmp_path / "game (1).nsz").write_bytes(b"x")
    (tmp_path / "game (2).nsz").write_bytes(b"x")
    assert unique_destination_path(target) == tmp_path / "game (3).nsz"

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss

from nsz.Fs.Nca import Nca
from nsz.Fs.Xci import Xci

from nszees.services.nca_signature import (
    _NCA_HDR_FIXED_KEY_MODULI_RETAIL,
    _verify_pss,
    SignatureCheck,
    verify_package_signature,
)


def test_fixed_key_moduli_are_well_formed():
    assert len(_NCA_HDR_FIXED_KEY_MODULI_RETAIL) == 2
    for modulus in _NCA_HDR_FIXED_KEY_MODULI_RETAIL:
        assert len(modulus) == 256
        assert modulus[0] & 0x80  # top bit set, as expected for a 2048-bit RSA modulus


def test_verify_pss_accepts_a_genuinely_valid_signature():
    key = RSA.generate(2048)
    modulus_bytes = key.n.to_bytes(256, "big")
    payload = b"header bytes 0x200-0x400" + b"\x00" * (0x200 - 24)

    signature = pss.new(key).sign(SHA256.new(payload))

    assert _verify_pss(payload, signature, modulus_bytes) is True


def test_verify_pss_rejects_a_tampered_payload():
    key = RSA.generate(2048)
    modulus_bytes = key.n.to_bytes(256, "big")
    payload = bytearray(b"header bytes 0x200-0x400" + b"\x00" * (0x200 - 24))

    signature = pss.new(key).sign(SHA256.new(bytes(payload)))
    payload[0] ^= 0xFF  # simulate a repacked/edited header

    assert _verify_pss(bytes(payload), signature, modulus_bytes) is False


def test_verify_pss_rejects_signature_from_a_different_key():
    key = RSA.generate(2048)
    other_key = RSA.generate(2048)
    modulus_bytes = other_key.n.to_bytes(256, "big")
    payload = b"header bytes 0x200-0x400" + b"\x00" * (0x200 - 24)

    signature = pss.new(key).sign(SHA256.new(payload))

    assert _verify_pss(payload, signature, modulus_bytes) is False


def test_verify_package_signature_reports_not_checked_with_no_nca_entries():
    result = verify_package_signature([])
    assert result == SignatureCheck(checked=False, valid=None, reason="no NCA headers available to check")


def test_verify_package_signature_traverses_xci_secure_partition(monkeypatch):
    """Xci isn't directly iterable like Nsp - its NCAs live nested inside a
    "secure" HFS0 partition reachable via package.hfs0. Regression test for a
    bug where every XCI silently reported checked=False because
    `for entry in package` raised TypeError on a bare Xci object."""

    class FakeNca(Nca):
        def __init__(self):
            pass

        def close(self):
            pass

    fake_nca = FakeNca()

    class FakeSecurePartition:
        _path = "secure"

        def __iter__(self):
            return iter([fake_nca])

    class FakeXci(Xci):
        def __init__(self):
            pass

        def close(self):
            pass

        @property
        def hfs0(self):
            return [FakeSecurePartition()]

    monkeypatch.setattr(
        "nszees.services.nca_signature.verify_nca_header_signature",
        lambda entry: SignatureCheck(checked=True, valid=True, reason=None)
        if entry is fake_nca
        else SignatureCheck(checked=False, valid=None, reason="unexpected entry"),
    )

    result = verify_package_signature(FakeXci())
    assert result == SignatureCheck(checked=True, valid=True, reason=None)

"""NCA header ("Signature 1") verification against Nintendo's published fixed keys.

Every NCA header carries two RSA-2048-PSS-SHA256 signatures over header
bytes 0x200-0x400. Signature 1 is checked against one of Nintendo's own
public "fixed key" moduli, selected by the header's SignatureKeyGeneration
byte (offset 0x221). This is separate from nsz's own --verify/--quick-verify,
which only checks content hash tables (PFS0/IVFC) - nsz never performs this
RSA check at all.

A failure here does not mean the game data is corrupt or unplayable. The
most common cause by far is a benign, common scene-distribution conversion
from title-key ("Rights ID") crypto to standard crypto, which edits header
bytes inside the signed region - it is informational (the file was
repackaged from its original retail form), not evidence of a broken or
malicious file.

The fixed-key moduli below are Nintendo's own public verification keys (not
secret material), extracted byte-for-byte from hactool's published source:
https://github.com/SciresM/hactool/blob/master/pki.c
(nca_keys_retail.nca_hdr_fixed_key_moduli)
"""

from __future__ import annotations

from dataclasses import dataclass

from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Signature import pss

from nsz.Fs import factory
from nsz.Fs.Nca import Nca
from nsz.nut import Print

from . import nsz_keys
from .package_files import iter_package_files

_RSA_PUBLIC_EXPONENT = 65537

_SIGNED_PAYLOAD_OFFSET = 0x200
_SIGNED_PAYLOAD_SIZE = 0x200
_KEY_GENERATION_OFFSET = 0x221

# Nintendo's retail NCA header fixed-key RSA-2048 moduli, indexed by the
# header's SignatureKeyGeneration byte. Generation 1 covers firmware 9.0.0+.
_NCA_HDR_FIXED_KEY_MODULI_RETAIL: tuple[bytes, ...] = (
    bytes.fromhex(
        "BFBE406CF4A780E9F07D0C99611D772F96BC4B9E58381B03ABB175499F2B4D5"
        "834B005A37522BE1A3F0373AC7068D116B904465EB707912F078B26DEF60007"
        "B2B451F80D0A5E58ADEBBC9AD649B964EFA782B5CF6D7013B00F85F6A908AA4"
        "D676687FA89FF7590181E6B3DE98A68C92604D980CE3F5E92CE01FF063BF2C1"
        "A90CCE026F16BC92420A4164CD52B6344DAEC02EDEA4DF27683CC1A060AD43F"
        "3FC86C13E6C46F77C299FFAFDF0E3CE64E735F2F656566F6DF1E242B08340A5"
        "C3202BCC9AAECAED4D7030A8701C70FD1363290279EAD2A7AF3528321C7BE62"
        "F1AAA407E328C2742FE8278EC0DEBE6834B6D8104401A9E9A67F67229FA04F0"
        "9DE4F403"
    ),
    bytes.fromhex(
        "ADE3E1FA0435E5B6DD49EA8929B1FFB643DFCA96A04A13DF43D9949796436548"
        "705833A27D357B96745E0B5C32181424C258B36C227AA1B7CB90A7A3F97D451"
        "6A5C8ED8FAD395E9E4B51687DF80C35C63F91AE44A592300D46F840FFD0FF06"
        "D21C7F9618DCB71D663ED173BC158A2F94F300C183F1CDD78188ABDF8CEF97D"
        "D1B175F58F69AE9E8C22F3815F52107F837905D2E024024150D25B7265D09CC"
        "4CF4F21B94705A9EEEED7777D45199F5DC761EE36C8CD112D457D1B683E4E4F"
        "EDAE9B43B33E5378ADFB57F89F19B9EB015B23AFEEA61845B7D4B23120B8312"
        "F2226BB922964B260B635E965752A3676422CAD0563E74B5981F0DF8B334E69"
        "8685AAD"
    ),
)


@dataclass(frozen=True)
class SignatureCheck:
    """Result of checking one or more NCA header signatures.

    checked: whether we were able to run the check at all.
    valid: True if the signature(s) matched Nintendo's key, False if not,
        None if not checked.
    reason: human-readable note for the not-checked/invalid cases.
    """

    checked: bool
    valid: bool | None
    reason: str | None


def _verify_pss(payload: bytes, signature: bytes, modulus: bytes) -> bool:
    key = RSA.construct((int.from_bytes(modulus, "big"), _RSA_PUBLIC_EXPONENT))
    verifier = pss.new(key)
    try:
        verifier.verify(SHA256.new(payload), signature)
        return True
    except (ValueError, TypeError):
        return False


def verify_nca_header_signature(nca: Nca) -> SignatureCheck:
    """Check a single already-opened Nca object's header Signature 1."""
    header = getattr(nca, "header", None)
    if header is None or not header.signature1:
        return SignatureCheck(checked=False, valid=None, reason="NCA header not available")

    header.seek(_KEY_GENERATION_OFFSET)
    key_generation = header.readInt8()

    if key_generation >= len(_NCA_HDR_FIXED_KEY_MODULI_RETAIL):
        return SignatureCheck(
            checked=False, valid=None, reason=f"unrecognized signature key generation {key_generation}"
        )

    header.seek(_SIGNED_PAYLOAD_OFFSET)
    payload = header.read(_SIGNED_PAYLOAD_SIZE)
    modulus = _NCA_HDR_FIXED_KEY_MODULI_RETAIL[key_generation]

    if _verify_pss(payload, header.signature1, modulus):
        return SignatureCheck(checked=True, valid=True, reason=None)

    return SignatureCheck(
        checked=True,
        valid=False,
        reason=(
            "NCA header signature does not match Nintendo's key - commonly caused by "
            "standard-crypto repackaging, not file corruption"
        ),
    )


def verify_package_signature(package) -> SignatureCheck:
    """Check Signature 1 across every NCA in an already-opened package."""
    results = [
        verify_nca_header_signature(entry) for entry in iter_package_files(package) if isinstance(entry, Nca)
    ]
    checked_results = [r for r in results if r.checked]

    if not checked_results:
        return SignatureCheck(checked=False, valid=None, reason="no NCA headers available to check")

    if all(r.valid for r in checked_results):
        return SignatureCheck(checked=True, valid=True, reason=None)

    failed = next(r for r in checked_results if not r.valid)
    return SignatureCheck(checked=True, valid=False, reason=failed.reason)


def check_package_signature(package_path, app_root) -> SignatureCheck:
    """Open package_path (NSP/NSZ/XCI) and check its NCA header signatures."""
    nsz_keys.sync(app_root)
    original_print_info = Print.info
    Print.info = lambda *args, **kwargs: None
    package = None
    try:
        package = factory(package_path)
        package.open(str(package_path), "rb")
        return verify_package_signature(package)
    except Exception:
        return SignatureCheck(checked=False, valid=None, reason="failed to open package")
    finally:
        if package is not None:
            try:
                package.close()
            except Exception:
                pass
        Print.info = original_print_info

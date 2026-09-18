from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nsz.Fs import factory
from nsz.Fs.Nca import Nca
from nsz.nut import Print

from . import nsz_keys
from .package_files import iter_package_files


@dataclass(frozen=True)
class KeyRequirement:
    master_key_revision: int | None
    required_key_name: str | None
    required_key_present: bool | None
    rights_id: str | None


def _read_available_keys(prod_keys_path: Path) -> set[str]:
    if not prod_keys_path.exists():
        return set()

    available: set[str] = set()
    for line in prod_keys_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key_name = line.split("=", 1)[0].strip().lower()
        if key_name:
            available.add(key_name)
    return available


def inspect_key_requirement(package_path: Path, app_root: Path) -> KeyRequirement:
    """Determine the master key an NSP/NSZ/XCI needs to decrypt.

    Reads this straight from an NCA header's own cryptoType/cryptoType2
    fields (the "masterKey" the real decryption pipeline actually uses),
    rather than the package's ticket. Tickets are absent entirely on
    "ticketless"/standard-crypto dumps (a common scene-distribution
    conversion), which would otherwise leave this unresolvable; reading the
    NCA header instead works identically for ticketed and ticketless
    packages, since every NCA in a package carries the same master key
    generation.
    """
    nsz_keys.sync(app_root)
    original_print_info = Print.info
    Print.info = lambda *args, **kwargs: None
    package = None
    try:
        package = factory(package_path)
        package.open(str(package_path), "rb")

        nca = next(
            (entry for entry in iter_package_files(package) if isinstance(entry, Nca) and entry.header is not None),
            None,
        )
        if nca is None:
            return KeyRequirement(
                master_key_revision=None,
                required_key_name=None,
                required_key_present=None,
                rights_id=None,
            )

        header = nca.header
        revision = header.masterKey
        key_name = f"master_key_{revision:02x}"
        rights_id = format(header.getRightsId(), "X").zfill(32)
        available_keys = _read_available_keys(app_root / "prod.keys")
        present = key_name in available_keys
        return KeyRequirement(
            master_key_revision=revision,
            required_key_name=key_name,
            required_key_present=present,
            rights_id=rights_id,
        )
    except Exception:
        return KeyRequirement(
            master_key_revision=None,
            required_key_name=None,
            required_key_present=None,
            rights_id=None,
        )
    finally:
        if package is not None:
            try:
                package.close()
            except Exception:
                pass
        Print.info = original_print_info
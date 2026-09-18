from __future__ import annotations

import re
from pathlib import Path

from nsz.Fs import factory
from nsz.Fs.Ticket import Ticket
from nsz.nut import Print

from . import nsz_keys
from .package_files import iter_package_files


_TITLE_ID_RE = re.compile(r"\[([0-9a-fA-F]{16})\]")
_VERSION_INT_RE = re.compile(r"\[v(\d+)\]", re.IGNORECASE)
_DISPLAY_IN_BRACKETS_RE = re.compile(r"\[(\d+\.\d+\.\d+(?:_[0-9]+)?)\]")
_DISPLAY_TRAILING_RE = re.compile(r"\s+v(\d+\.\d+\.\d+(?:_[0-9]+)?)$", re.IGNORECASE)
_BRACKET_TOKEN_RE = re.compile(r"\[[^\]]+\]")


def _extract_title(stem: str) -> tuple[str, str | None]:
    title = stem.split("[", 1)[0].strip()
    trailing_match = _DISPLAY_TRAILING_RE.search(title)
    if trailing_match:
        title = title[: trailing_match.start()].rstrip()
        return title, trailing_match.group(1)
    return title, None


def _extract_display_version(stem: str, trailing_display: str | None) -> str | None:
    bracket_match = _DISPLAY_IN_BRACKETS_RE.search(stem)
    if bracket_match:
        return bracket_match.group(1)
    return trailing_display


def _extract_passthrough_tags(stem: str) -> list[str]:
    """Return non-core bracket tags to preserve in output filename.

    Keeps tags like region markers (e.g. [JP]) while dropping canonical tags that
    are normalized elsewhere (Title ID, integer version, display version, UPD).
    """
    passthrough: list[str] = []
    for token in _BRACKET_TOKEN_RE.findall(stem):
        inner = token[1:-1].strip()
        inner_lower = inner.lower()

        if re.fullmatch(r"[0-9a-f]{16}", inner_lower):
            continue
        if re.fullmatch(r"v\d+", inner_lower):
            continue
        if re.fullmatch(r"\d+\.\d+\.\d+(?:_\d+)?", inner):
            continue
        if inner_lower == "upd":
            continue

        passthrough.append(token)
    return passthrough


def _extract_from_internal_metadata(source_path: Path, app_root: Path) -> tuple[str | None, str | None]:
    """Fallback extractor for Title ID and integer version from package internals."""
    nsz_keys.sync(app_root)
    original_print = Print.info
    Print.info = lambda *args, **kwargs: None
    package = None
    try:
        package = factory(source_path)
        package.open(str(source_path), "rb")

        title_id: str | None = None
        version_int: str | None = None

        files = list(iter_package_files(package))

        try:
            ticket = next(f for f in files if isinstance(f, Ticket))
            rights_id = format(ticket.getRightsId(), "X").zfill(32)
            title_id = rights_id[:16]
        except Exception:
            pass

        try:
            cnmt_nca = next(f for f in files if getattr(f, "_path", "").endswith(".cnmt.nca"))
            for fs in cnmt_nca:
                try:
                    for item in fs:
                        if getattr(item, "_path", "").endswith(".cnmt"):
                            item.open(None, "rb")
                            version_value = getattr(item, "version", None)
                            if version_value is not None:
                                version_int = str(version_value)
                                break
                    if version_int:
                        break
                except Exception:
                    pass
        except Exception:
            pass

        return title_id, version_int
    except Exception:
        return None, None
    finally:
        if package is not None:
            try:
                package.close()
            except Exception:
                pass
        Print.info = original_print


def build_renamed_output_name(source_path: Path, app_root: Path) -> str | None:
    """Build target NSZ filename from source filename tags.

    Pattern:
    - <title> [<titleId>][v<versionInt>][v<display>] for updates if display exists
    - <title> [<titleId>][v0][v0] for base packages (versionInt == 0)
    - For updates without display tag, omit the [vX.X.X] segment.
    """
    stem = source_path.stem
    title, trailing_display = _extract_title(stem)

    title_match = _TITLE_ID_RE.search(stem)
    version_match = _VERSION_INT_RE.search(stem)

    title_id = title_match.group(1).upper() if title_match else None
    version_int = version_match.group(1) if version_match else None

    if not title_id or not version_int:
        fallback_title_id, fallback_version = _extract_from_internal_metadata(source_path, app_root)
        title_id = title_id or fallback_title_id
        version_int = version_int or fallback_version

    if not title_id or not version_int:
        return None

    display_version = _extract_display_version(stem, trailing_display)
    passthrough_tags = _extract_passthrough_tags(stem)

    base = f"[{title_id}][v{version_int}]"
    if passthrough_tags:
        base = f"[{title_id}]{''.join(passthrough_tags)}[v{version_int}]"
    if title:
        base = f"{title} {base}"

    if version_int != "0" and display_version:
        base += f"[v{display_version}]"

    output_suffix = ".xcz" if source_path.suffix.lower() in {".xci", ".xcz"} else ".nsz"
    return base.strip() + output_suffix
"""Parse raw NSZ subprocess output into a concise visual summary."""

from __future__ import annotations

import re

from .validator import ValidationResult

_SKIP_TAGS = re.compile(r"^\[(OPEN|ADDING|EXISTS|NCA HASH)\s*\]")
_VERIFIED = re.compile(r"^\[VERIFIED\]\s+(\S+)")
_NSP_SHA256 = re.compile(r"^\[NSP SHA256\]\s+([0-9a-fA-F]+)")
_UNCONFIRMED = re.compile(r"Unconfirmed: crc32\(master_key_(\d+)\)")
_ERROR_TAG = re.compile(r"^\[ERROR\]\s*(.*)")
_WARN_TAG = re.compile(r"^\[WARN\]\s*(.*)")
_OP_HEADER = re.compile(r"^\[(VERIFY|COMPRESS|DECOMPRESS)\s+(NSZ|NSP)\]\s+(.+)", re.IGNORECASE)


def _abbrev(h: str) -> str:
    return f"{h[:8]}…{h[-6:]}" if len(h) > 16 else h


def summarise_nsz_output(stdout: str, stderr: str = "", exit_code: int = 0) -> str:
    """Return a concise visual summary of NSZ subprocess output."""
    verified: list[str] = []
    nsp_sha256: str | None = None
    unconfirmed_keys: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    operation: str | None = None
    done = False

    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if _SKIP_TAGS.match(line):
            continue
        if line == "Done!":
            done = True
            continue

        m = _OP_HEADER.match(line)
        if m:
            operation = f"{m.group(1).title()} {m.group(2).upper()}: {m.group(3)}"
            continue

        m = _VERIFIED.match(line)
        if m:
            verified.append(m.group(1))
            continue

        m = _NSP_SHA256.match(line)
        if m:
            nsp_sha256 = m.group(1)
            continue

        m = _UNCONFIRMED.search(line)
        if m:
            unconfirmed_keys.append(m.group(1))
            continue

        m = _ERROR_TAG.match(line)
        if m:
            errors.append(m.group(1) or line)
            continue

        m = _WARN_TAG.match(line)
        if m:
            warnings.append(m.group(1) or line)
            continue

    out: list[str] = []

    if operation:
        out.append(f"── {operation}")

    for fname in verified:
        out.append(f"✅  {fname}")

    if nsp_sha256:
        out.append(f"✅  Package SHA256: {_abbrev(nsp_sha256)}")

    if unconfirmed_keys:
        keys = ", ".join(unconfirmed_keys)
        out.append(f"⚠️  Unconfirmed master keys: {keys}  (prod.keys may be outdated)")

    for w in warnings:
        out.append(f"⚠️  {w}")

    for e in errors:
        out.append(f"❌  {e}")

    if errors or (exit_code != 0 and not done):
        out.append(f"❌  Failed (exit code {exit_code})")
    elif done or exit_code == 0:
        out.append("✅  Done")

    if stderr.strip():
        out.append(f"⚠️  stderr: {stderr.strip()[:300]}")

    return "\n".join(out)


def summarise_validation(result: ValidationResult) -> str:
    """Return a concise visual summary of a ValidationResult."""
    out: list[str] = []

    if result.container_valid:
        out.append("✅  Container valid")
    else:
        err = f": {result.container_error}" if result.container_error else ""
        out.append(f"❌  Container invalid{err}")

    if result.quick_verify_passed is True:
        out.append("✅  Quick verify passed")
    elif result.quick_verify_passed is False:
        out.append("⚠️  Quick verify failed")

    action = result.primary_action.replace("_", " ").title()
    out.append(f"→   Recommended action: {action}")

    if result.required_key_name and result.required_key_present is True:
        out.append(f"✅  Required key present: {result.required_key_name}")
    elif result.required_key_name and result.required_key_present is False:
        out.append(f"❌  Required key missing: {result.required_key_name}")

    if result.signature_checked and result.signature_valid is True:
        out.append("✅  NCA header signature matches Nintendo (not repackaged)")
    elif result.signature_checked and result.signature_valid is False:
        out.append("⚠️  File was repackaged (NCA header signature does not match Nintendo's key)")

    if result.quick_verify_output:
        keys = re.findall(r"Unconfirmed: crc32\(master_key_(\d+)\)", result.quick_verify_output)
        if keys:
            out.append(f"⚠️  Unconfirmed master keys: {', '.join(keys)}  (prod.keys may be outdated)")

    for w in result.warnings:
        if result.required_key_name and w in {
            f"Required key available: {result.required_key_name}",
            f"Required key missing: {result.required_key_name}",
        }:
            continue
        if w == "File was repackaged (NCA header signature does not match Nintendo's key)":
            continue
        out.append(f"⚠️  {w}")

    return "\n".join(out)

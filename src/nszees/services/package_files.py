"""Shared helper for enumerating files inside an opened nsz package.

Nsp exposes its files as a flat, directly-iterable list. Xci's own object
isn't iterable at all - its files are nested inside per-partition HFS0
sub-containers (update/logo/normal/secure) reachable via `package.hfs0`.
This flattens both container shapes into one generator so callers can
enumerate any opened package (NSP or XCI) the same way.
"""

from __future__ import annotations

from nsz.Fs.Xci import Xci


def iter_package_files(package):
    """Yield every file entry in an opened Nsp or Xci package.

    For Xci, the "secure" partition (the actual game content) is yielded
    first since that's what callers usually care about (e.g. the first NCA
    header found), with the other partitions (update/logo/normal) following
    as a fallback.
    """
    if isinstance(package, Xci):
        partitions = sorted(package.hfs0, key=lambda p: getattr(p, "_path", "") != "secure")
        for partition in partitions:
            yield from partition
        return

    yield from package

# NSZees

A portable Windows GUI for compressing and decompressing Nintendo Switch
game dumps (NSP/XCI to NSZ/XCZ) using the nsz compression backend.

NSZees is designed for archiving legally dumped backups. Compression is
lossless and does not include keys or game files; users supply their own
legally obtained `prod.keys` and optional `title.keys`.

## Highlights

- Portable Windows application with no installer or registry writes
- Structural validation and quick cryptographic verification before compression
- Responsive PySide6 interface with background workers and cancellation
- Collision-safe output naming
- Automated tests for validation, naming, and key-handling logic

## Start on Windows

1. Place your own `prod.keys` in the application folder.
2. Optionally place `title.keys` there as well.
3. Double-click `NSZees-NoConsole.cmd`.

See [PACKAGING.md](PACKAGING.md) for distribution requirements and
[THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md) for dependency notices.

## License

NSZees's own source code is licensed under the [MIT License](LICENSE).
Bundled dependencies retain their separate licenses.

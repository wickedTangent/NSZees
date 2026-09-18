# NSZees (v1) - Copilot Brief

## Goal
Portable Windows GUI app (Python + PySide6) to auto-validate an NSP and then compress it to NSZ using bundled `nsz.exe`.

## Non-negotiables
- Portable: no installer, no registry, do not write outside app folder.
- Keys: `prod.keys` must be in the app directory (project root for dev; next to exe when packaged).
- Bundle backend: `bin\nsz.exe`. Always run subprocess with `cwd = app root` so keys are found.

## Workflow
1. User opens an NSP.
2. App auto-runs:
   - Container Check (instant): Python PFS0 structural validation.
   - Quick Verify: `nsz --quick-verify <file>`
3. Results:
   - If Container Check fails: disable Compress.
   - If Quick Verify fails: warn but allow **Compress (Force)** with confirmation.

## Advanced (manual)
- Deep Verify: tool-driven: `nsz --verify <file>`
- Round-trip test: optional; advanced only.

## Compression preset (Maximum)
- `--solid --level 22 --long --threads 0`

## Unicode/long path fallback
If backend fails AND path is risky (non-ASCII or too long), offer "Retry using staging copy" into `temp\staging\`.

## Progress UI
- v1 per-file only.
- Separate steps: "Validating..." then "Compressing..."
- Always show marquee + elapsed time; if `--machine-readable` gives parseable progress, show %/ETA.

## Directories
bin/, config/, logs/, temp/staging/, output/

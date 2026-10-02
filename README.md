# Report File Purgifier

Report File Purgifier is a Windows Python utility for maintaining CMM run-data directories and organizing aging inspection reports. It reads its paths and retention periods from `PurgifierSettings.ini`, logs its work to `PurgifierRunLog.txt`, and can be run as a Python script or packaged as a Windows executable.

## What it does

When started, the program runs these tasks in order:

1. **Purge CMM run data.** In the configured CMM run-data directory, files older than `cmm_prg_days_to_keep` are deleted, regardless of extension. `.CAD` files are also subject to the `cmm_cad_days_to_keep` retention rule. Both cutoffs are midnight on the date that many days before today.
2. **Archive report files.** For each configured report mover, files older than its `days_to_keep` cutoff are moved from the mover's root directory into `archive_path\YYYY\MM-YYYY\`. For example, a file last modified in March 2024 is filed under `archive_path\2024\03-2024\`.
3. **Trim the log.** The run log is trimmed to its most recent 10,000 lines.

Both directory scans are non-recursive: only files directly in each configured root directory are considered. The report mover processes all files, not just PDFs.

> **Warning:** Purging permanently deletes files, and archiving moves files. Review `PurgifierSettings.ini` carefully and test with temporary directories before using or scheduling this program against production data.

## Requirements

- Windows
- Python 3
- `pytest` to run the test suite

The application itself uses only the Python standard library.

## Configuration

Edit `PurgifierSettings.ini` before running. It must be in the application's base directory: the current working directory when running the Python script, or beside the executable when running a packaged build.

The file should contain:

| Section | Setting | Purpose |
|---|---|---|
| `[CMMRunDataPurgifier]` | `root_path` | Directory containing CMM run data |
| `[CMMRunDataPurgifier]` | `cmm_prg_days_to_keep` | Age in days before any file is deleted by the general retention rule |
| `[CMMRunDataPurgifier]` | `cmm_cad_days_to_keep` | Age in days before a `.CAD` file is deleted by the CAD-specific rule |
| `[ReportFileMovers]` | `file_movers` | Comma-separated list of mover section names to run |
| Each mover section | `root_path` | Directory containing report files to scan |
| Each mover section | `archive_path` | Destination base directory for archived files |
| Each mover section | `days_to_keep` | Age in days before a file is archived |
| `[Loggers]` | logger-name setting | Set to `DEBUG` for debug logging; other values use `INFO` |

Each name in `file_movers` must match a corresponding INI section. Configure valid, accessible paths and numeric retention values. The program operates on local file modification times.

## Run

Open PowerShell in the project directory, configure the INI file, then run:

```powershell
python ReportFilePurgifier.py
```

The executable also expects `PurgifierSettings.ini` beside it. The log file is written to the same base directory.

## Tests

Install pytest if needed, then run from the project directory:

```powershell
python -m pip install pytest
python -m pytest Test
```

## Build executable

The optional `build\build.bat` script uses PyInstaller to create a one-file executable. It currently contains absolute paths specific to its original development environment; update those paths for your checkout before building. Ensure the INI file is present beside the resulting executable.

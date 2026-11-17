# Contributing to Grayjay Desktop to FreeTube Playlist Exporter

Thank you for helping improve this tool!

## Design Principles

1. **Zero external dependencies**: Keep `grayjay_to_freetube.py` strictly on Python 3.8+ standard library modules so everyday users never need `pip`.
2. **Read-only safety**: Never modify, rename, or delete files inside a user's Grayjay folder.
3. **Cross-platform compatibility**: Keep scripts working cleanly on Windows, macOS, and Linux.

## Submitting Changes

1. Fork the repository and create a new branch from `main`.
2. Add or update tests in `tests/test_converter.py` covering your change or new Grayjay file format.
3. Run the test suite locally:
   ```bash
   python -m unittest discover -s tests -v
   ```
4. Open a pull request explaining the change and which Grayjay Desktop / FreeTube versions you tested with.

## Reporting Format Changes

If a new Grayjay Desktop release changes how playlists are stored, please open a bug report with:
- Your operating system and Grayjay Desktop version.
- The folder structure inside your Grayjay directory (folder names only).
- A **sanitized sample** of one playlist entry (remove any personal info before sharing).

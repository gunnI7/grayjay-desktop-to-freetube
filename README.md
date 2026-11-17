# Grayjay Desktop to FreeTube Playlist Exporter

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-3776AB.svg)](https://www.python.org/downloads/)
[![Dependencies: None](https://img.shields.io/badge/Dependencies-Zero-brightgreen.svg)](#features)

<img width="1024" height="572" alt="image" src="https://github.com/user-attachments/assets/a7c11c58-370d-455c-a9ce-66f19fd59027" />


Export and back up your local **Grayjay Desktop** playlists and **Watch Later** list into a standard FreeTube `.db` (newline-delimited JSON) file with a single double-click. Works with **FreeTube**, any other video player that accepts FreeTube `.db` imports, or simply as an offline backup of your Grayjay playlists.

## Features

- **One-click export on Windows** — double-click `Export_Grayjay_to_FreeTube.bat` or drag your Grayjay folder onto it.
- **Auto-detects your Grayjay folder** — drop the tool inside your Grayjay folder or run it from anywhere on Windows, macOS, or Linux.
- **Zero dependencies** — runs using Python 3's built-in standard library only (no `pip install`).
- **100% local & private** — reads your local data read-only, makes zero network calls, and never modifies your Grayjay files.
- **Watch Later included** — exports Grayjay's Watch Later list as a `Grayjay Watch Later` playlist in FreeTube.
- **Multi-format support** — handles Grayjay Desktop JSON playlist files, newline-delimited store files, and SQLite fallback tables.

> **Note:** FreeTube only plays YouTube videos. Videos from other platforms (Rumble, Odysee, PeerTube, etc.) are automatically skipped and counted in the summary.

---

## Quick Start (Windows)

1. Install **Python 3** from [python.org/downloads](https://www.python.org/downloads/) if you don't already have it *(check **"Add python.exe to PATH"** during setup)*.
2. Download this repository (**Code → Download ZIP**) and extract all files into one folder.
3. Double-click **`Export_Grayjay_to_FreeTube.bat`**.
   - It automatically checks the folder it sits in, its parent folder, `%APPDATA%\Grayjay`, `%LOCALAPPDATA%\Grayjay`, and `%LOCALAPPDATA%\Programs\Grayjay`.
   - You can also copy the extracted files directly into your Grayjay folder, or **drag and drop** your Grayjay folder onto **`Export_Grayjay_to_FreeTube.bat`**.
4. A file named **`grayjay_freetube_playlists.db`** will be created in the same folder.

---

## Quick Start (Linux & macOS)

```bash
chmod +x export_grayjay_to_freetube.sh
./export_grayjay_to_freetube.sh
```

Or run Python directly:

```bash
python3 grayjay_to_freetube.py
```

---

## How to Import into FreeTube

1. Open **FreeTube**.
2. Go to **Settings → Data Settings**.
3. Click **Import Playlists**.
4. Select **`grayjay_freetube_playlists.db`**.
5. Open **Playlists** in FreeTube's left sidebar — your Grayjay playlists and YouTube videos will appear immediately.

---

## Backups & Other Compatible Apps

Even if you do not use FreeTube, this tool helps fill the gap while Grayjay Desktop lacks built-in desktop export/import ([futo-org/Grayjay.Desktop#317](https://github.com/futo-org/Grayjay.Desktop/issues/317)):

- **Local Backups for Grayjay Users:** Run the script manually or automate it with Windows Task Scheduler or `cron` to keep a clean, readable snapshot of all your playlists and Watch Later items outside your Grayjay folder.
- **Compatible with Other Apps:** Because the exported `.db` file uses FreeTube's widely supported newline-delimited JSON format, you can use it to move your playlists into any alternative video frontend or player that supports FreeTube playlist imports.
- **Need Subscriptions Too?** This tool focuses on playlists and Watch Later. To export your channel subscriptions and groups from Grayjay Desktop as well, pair it with [grayjay-subscriptions-exporter](https://github.com/wolfgang101/grayjay-subscriptions-exporter).

---

## Command-Line Options

```bash
python grayjay_to_freetube.py [source] [-o OUTPUT] [--no-watch-later] [--dry-run] [--version]
```

| Option | Description |
| --- | --- |
| `source` | Optional path to your Grayjay folder or `playlists` subfolder (auto-detected if omitted). |
| `-o`, `--output` | Custom path for the exported `.db` file (default: `grayjay_freetube_playlists.db` next to the script). |
| `--no-watch-later` | Export playlists only and skip Grayjay's Watch Later list. |
| `--dry-run` | Preview detected playlists and video counts without creating any file. |
| `--version` | Print the tool version and exit. |

### Examples

```bash
# Preview what will be exported without writing a file
python grayjay_to_freetube.py --dry-run

# Point to a portable Grayjay folder and choose a custom output file
python grayjay_to_freetube.py "D:\Portable\Grayjay" -o "D:\Backups\playlists.db"

# Export playlists only (skip Watch Later)
python grayjay_to_freetube.py --no-watch-later
```

---

## Troubleshooting

- **"No importable YouTube playlists were found"**
  Grayjay Desktop stores data either inside its program directory (portable mode, e.g. `C:\Users\<You>\AppData\Local\Programs\Grayjay`) or in your user data directory (`%APPDATA%\Grayjay` on Windows, `~/.local/share/Grayjay` or `~/Grayjay` on Linux, `~/Library/Application Support/Grayjay` on macOS). Find the folder containing a `playlists` or `stores` subfolder and drag that folder onto `Export_Grayjay_to_FreeTube.bat`.
- **Windows SmartScreen says "Windows protected your PC"**
  Batch files downloaded from GitHub are unsigned. Click **More info → Run anyway** (you can right-click and inspect `Export_Grayjay_to_FreeTube.bat` in Notepad first—it is plain text).

---

## Running Tests

```bash
python -m unittest discover -s tests -v
```

---

## Contributing

Contributions, bug reports, and format fixes for newer Grayjay Desktop versions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Released under the [MIT License](LICENSE).

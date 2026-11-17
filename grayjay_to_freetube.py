#!/usr/bin/env python3
"""
Grayjay Desktop to FreeTube Playlist Exporter

Converts local Grayjay Desktop playlists (and Watch Later items) into a
FreeTube-compatible `.db` file (newline-delimited JSON).

Zero external dependencies — uses Python 3 standard library only.
100% local — makes no network requests and never modifies your Grayjay files.
"""

import argparse
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

__version__ = "1.0.0"

YT_URL_RE = re.compile(
    r"(?:https?://)?(?:www\.|m\.|music\.)?"
    r"(?:youtube\.com/(?:watch\?(?:[^\s\"']*?&)?v=|shorts/|embed/|live/|v/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)
YT_CHANNEL_RE = re.compile(r"youtube\.com/channel/(UC[A-Za-z0-9_-]+)")
YT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

SKIP_EXTENSIONS = {
    ".bak", ".tmp", ".lock", ".log", ".exe", ".dll", ".so", ".dylib",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".svg",
    ".py", ".bat", ".sh", ".md", ".zip", ".7z", ".rar", ".yml", ".yaml",
}
SKIP_DIRS = {
    ".git", ".github", "__pycache__", "node_modules", "cache",
    "logs", "thumbnails", "tests", ".venv", "venv",
}
SQLITE_HEADER = b"SQLite format 3\x00"


def ci_get(mapping, *keys, default=None):
    """Case-insensitive dictionary lookup."""
    if not isinstance(mapping, dict):
        return default
    lowered = {str(k).lower(): v for k, v in mapping.items()}
    for key in keys:
        val = lowered.get(key.lower())
        if val is not None:
            return val
    return default


def parse_timestamp_ms(value, fallback_ms):
    """Convert Unix seconds/ms or ISO-8601 date strings into epoch milliseconds."""
    if value is None:
        return fallback_ms
    if isinstance(value, (int, float)):
        if value <= 0:
            return fallback_ms
        return int(value * 1000) if value < 10_000_000_000 else int(value)
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.isdigit():
            num = int(text)
            if num <= 0:
                return fallback_ms
            return num * 1000 if num < 10_000_000_000 else num
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return int(dt.timestamp() * 1000)
        except ValueError:
            pass
    return fallback_ms


def make_ft_video(
    video_id,
    title=None,
    author="Unknown",
    author_id="",
    length_seconds=0,
    published_ms=0,
    time_added_ms=0,
):
    """Build a FreeTube playlist video entry."""
    return {
        "videoId": video_id,
        "title": title or f"Video {video_id}",
        "author": author or "Unknown",
        "authorId": author_id or "",
        "lengthSeconds": max(0, int(length_seconds)),
        "published": int(published_ms),
        "timeAdded": int(time_added_ms),
        "playlistItemId": str(uuid.uuid4()),
        "type": "video",
    }


def extract_youtube_id_from_text(text):
    if not isinstance(text, str):
        return None
    match = YT_URL_RE.search(text)
    return match.group(1) if match else None


def extract_youtube_id(video):
    """Extract an 11-character YouTube video ID from a string or Grayjay video dict."""
    if isinstance(video, str):
        vid = extract_youtube_id_from_text(video)
        if vid:
            return vid
        stripped = video.strip()
        return stripped if YT_ID_RE.match(stripped) else None

    if not isinstance(video, dict):
        return None

    for key in ("url", "shareUrl", "link", "videoUrl"):
        vid = extract_youtube_id_from_text(ci_get(video, key))
        if vid:
            return vid

    vid_id = ci_get(video, "id", "videoId")
    if isinstance(vid_id, dict):
        platform = str(ci_get(vid_id, "platform", "pluginName", default="") or "").lower()
        val = str(ci_get(vid_id, "value", "id", default="") or "")
        if ("youtube" in platform or not platform) and YT_ID_RE.match(val):
            return val
    elif isinstance(vid_id, str) and YT_ID_RE.match(vid_id):
        url = str(ci_get(video, "url", default="") or "").lower()
        if not url or "youtube" in url or "youtu.be" in url:
            return vid_id

    return None


def extract_author(video):
    """Extract channel display name and YouTube UC... channel ID when available."""
    author = ci_get(video, "author", "channel", "uploader")
    if isinstance(author, dict):
        name = str(ci_get(author, "name", "title", default="Unknown") or "Unknown")
        aid = ci_get(author, "id")
        if isinstance(aid, dict):
            author_id = str(ci_get(aid, "value", "id", default="") or "")
        elif isinstance(aid, str):
            author_id = aid
        else:
            author_id = ""
        if not author_id:
            aurl = str(ci_get(author, "url", default="") or "")
            match = YT_CHANNEL_RE.search(aurl)
            if match:
                author_id = match.group(1)
        return name, author_id
    if isinstance(author, str) and author.strip():
        return author.strip(), ""
    return "Unknown", ""


def convert_video(video, now_ms):
    """Convert a Grayjay video record or URL into a FreeTube video object."""
    if isinstance(video, str):
        video_id = extract_youtube_id(video)
        if not video_id:
            return None
        return make_ft_video(video_id=video_id, time_added_ms=now_ms)

    if not isinstance(video, dict):
        return None

    video_id = extract_youtube_id(video)
    if not video_id:
        return None

    title = str(
        ci_get(video, "name", "title", default=f"Video {video_id}")
        or f"Video {video_id}"
    )
    author_name, author_id = extract_author(video)

    raw_duration = ci_get(video, "duration", "lengthSeconds", "length", default=0)
    try:
        length_seconds = max(0, int(float(raw_duration)))
    except (TypeError, ValueError):
        length_seconds = 0

    published_ms = parse_timestamp_ms(
        ci_get(video, "datetime", "uploadDate", "published", "date"), 0
    )

    return make_ft_video(
        video_id=video_id,
        title=title,
        author=author_name,
        author_id=author_id,
        length_seconds=length_seconds,
        published_ms=published_ms,
        time_added_ms=now_ms,
    )


def parse_newline_playlist_string(text, fallback_name, now_ms):
    """Parse Grayjay newline-delimited playlist strings (title on line 0, URLs after)."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None, 0

    if extract_youtube_id_from_text(lines[0]):
        pl_name = fallback_name
        video_lines = lines
    else:
        pl_name = lines[0]
        video_lines = lines[1:]

    videos = []
    seen = set()
    skipped = 0

    for idx, line in enumerate(video_lines):
        vid = extract_youtube_id_from_text(line)
        if vid:
            if vid not in seen:
                seen.add(vid)
                videos.append(make_ft_video(video_id=vid, time_added_ms=now_ms + idx))
        elif line.startswith(("http://", "https://")):
            skipped += 1

    if not videos:
        return None, skipped

    return {
        "playlistName": pl_name.strip() or fallback_name,
        "protected": False,
        "description": "",
        "videos": videos,
        "_id": f"ft-playlist--{uuid.uuid4()}",
        "createdAt": now_ms,
        "lastUpdatedAt": now_ms,
    }, skipped


def is_sqlite_file(path: Path) -> bool:
    try:
        with path.open("rb") as fh:
            return fh.read(16) == SQLITE_HEADER
    except OSError:
        return False


def read_file_content(path: Path):
    """Read a candidate data file as parsed JSON or plain text."""
    if not path.is_file():
        return None, None
    if path.name.startswith(".") or path.suffix.lower() in SKIP_EXTENSIONS:
        return None, None
    if path.suffix.lower() == ".db" or is_sqlite_file(path):
        return None, None
    try:
        raw = path.read_text(encoding="utf-8-sig")
    except Exception:
        return None, None

    if not raw.strip():
        return None, None

    try:
        return json.loads(raw), raw
    except Exception:
        return None, raw


def find_subfolder(base: Path, candidates, max_depth=2):
    """Breadth-first search for a matching subfolder up to max_depth levels deep."""
    candidate_set = {c.lower() for c in candidates}
    queue = [(base, 0)]
    while queue:
        current, depth = queue.pop(0)
        try:
            entries = sorted(current.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir() or entry.name.lower() in SKIP_DIRS:
                continue
            if entry.name.lower() in candidate_set:
                return entry
            if depth + 1 < max_depth:
                queue.append((entry, depth + 1))
    return None


def convert_playlist_dict(pl, fallback_name, now_ms):
    pl_name = str(
        ci_get(pl, "name", "title", "playlistName", default=fallback_name)
        or fallback_name
    ).strip()
    pl_desc = str(ci_get(pl, "description", default="") or "")
    raw_videos = ci_get(pl, "videos", "items", "entries", default=[])
    if not isinstance(raw_videos, list):
        return None, 0

    converted = []
    seen_vids = set()
    skipped = 0

    for idx, video in enumerate(raw_videos):
        ft_vid = convert_video(video, now_ms + idx)
        if ft_vid:
            if ft_vid["videoId"] not in seen_vids:
                seen_vids.add(ft_vid["videoId"])
                converted.append(ft_vid)
        else:
            skipped += 1

    if not converted:
        return None, skipped

    created_ms = parse_timestamp_ms(ci_get(pl, "dateCreated", "createdAt"), now_ms)
    updated_ms = parse_timestamp_ms(
        ci_get(pl, "dateUpdate", "dateUpdated", "lastUpdatedAt"), now_ms
    )

    return {
        "playlistName": pl_name or fallback_name,
        "protected": False,
        "description": pl_desc,
        "videos": converted,
        "_id": f"ft-playlist--{uuid.uuid4()}",
        "createdAt": created_ms,
        "lastUpdatedAt": updated_ms,
    }, skipped


def extract_playlists_from_data(data, raw_text, fallback_name, now_ms, seen_ids):
    """Recursively extract FreeTube playlist objects from parsed JSON or plain text."""
    results = []
    skipped_total = 0

    if isinstance(data, dict):
        if ci_get(data, "videos", "items", "entries") is not None:
            pl_id = str(ci_get(data, "id", default="") or "")
            if not pl_id or pl_id not in seen_ids:
                if pl_id:
                    seen_ids.add(pl_id)
                pl_obj, skipped = convert_playlist_dict(data, fallback_name, now_ms)
                skipped_total += skipped
                if pl_obj:
                    results.append(pl_obj)
        else:
            for key, val in data.items():
                if isinstance(val, dict) and ci_get(val, "videos", "items", "entries") is not None:
                    sub_res, sub_skip = extract_playlists_from_data(
                        val, None, str(key), now_ms, seen_ids
                    )
                    results.extend(sub_res)
                    skipped_total += sub_skip
                elif isinstance(val, str) and "\n" in val:
                    pl_obj, skipped = parse_newline_playlist_string(val, str(key), now_ms)
                    skipped_total += skipped
                    if pl_obj:
                        results.append(pl_obj)

    elif isinstance(data, list):
        for idx, entry in enumerate(data):
            if isinstance(entry, dict) and ci_get(entry, "videos", "items", "entries") is not None:
                sub_res, sub_skip = extract_playlists_from_data(
                    entry, None, f"{fallback_name}_{idx + 1}", now_ms, seen_ids
                )
                results.extend(sub_res)
                skipped_total += sub_skip
            elif isinstance(entry, str):
                pl_obj, skipped = parse_newline_playlist_string(
                    entry, f"{fallback_name}_{idx + 1}", now_ms
                )
                skipped_total += skipped
                if pl_obj:
                    results.append(pl_obj)

    elif isinstance(data, str):
        pl_obj, skipped = parse_newline_playlist_string(data, fallback_name, now_ms)
        skipped_total += skipped
        if pl_obj:
            results.append(pl_obj)

    elif data is None and raw_text:
        pl_obj, skipped = parse_newline_playlist_string(raw_text, fallback_name, now_ms)
        skipped_total += skipped
        if pl_obj:
            results.append(pl_obj)

    return results, skipped_total


def extract_from_sqlite(db_path: Path, now_ms, seen_ids):
    """Best-effort read-only extraction of playlist JSON records from a Grayjay SQLite DB."""
    results = []
    skipped_total = 0
    uri = f"file:{db_path.as_posix()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error:
        return results, skipped_total

    try:
        cur = conn.cursor()
        tables = [
            row[0]
            for row in cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        playlist_tables = [t for t in tables if "playlist" in t.lower()]
        for table in playlist_tables:
            safe_table = table.replace('"', '""')
            try:
                rows = cur.execute(f'SELECT * FROM "{safe_table}"').fetchall()
            except sqlite3.Error:
                continue
            for idx, row in enumerate(rows):
                for cell in row:
                    if not isinstance(cell, str) or len(cell) < 10:
                        continue
                    stripped = cell.strip()
                    if stripped.startswith(("{", "[")):
                        try:
                            parsed = json.loads(stripped)
                        except ValueError:
                            continue
                        found, skipped = extract_playlists_from_data(
                            parsed, None, f"{table}_{idx + 1}", now_ms, seen_ids
                        )
                        results.extend(found)
                        skipped_total += skipped
    finally:
        conn.close()

    return results, skipped_total


def collect_playlists(root_dir: Path, include_watch_later: bool = True):
    """Scan a Grayjay folder and return (playlists, total_videos, skipped_count)."""
    now_ms = int(time.time() * 1000)
    freetube_playlists = []
    skipped_non_yt = 0
    seen_ids = set()

    if root_dir.name.lower() == "playlists":
        playlists_dir = root_dir
        stores_dir = None
        wl_dir = find_subfolder(root_dir.parent, ["watchLater", "watch_later"], max_depth=1)
    else:
        playlists_dir = find_subfolder(root_dir, ["playlists"], max_depth=2)
        stores_dir = find_subfolder(root_dir, ["stores"], max_depth=2)
        wl_dir = find_subfolder(root_dir, ["watchLater", "watch_later"], max_depth=2)

    # 1. Standard `playlists/` subfolder
    if playlists_dir and playlists_dir.is_dir():
        try:
            entries = sorted(playlists_dir.iterdir())
        except OSError:
            entries = []
        for item in entries:
            data, raw = read_file_content(item)
            if data is None and raw is None:
                continue
            found, skipped = extract_playlists_from_data(
                data, raw, item.stem, now_ms, seen_ids
            )
            freetube_playlists.extend(found)
            skipped_non_yt += skipped

    # 2. `stores/` subfolder (Android/export store layout)
    if stores_dir and stores_dir.is_dir():
        try:
            entries = sorted(stores_dir.iterdir())
        except OSError:
            entries = []
        for item in entries:
            if "playlist" in item.name.lower():
                data, raw = read_file_content(item)
                if data is None and raw is None:
                    continue
                found, skipped = extract_playlists_from_data(
                    data, raw, item.stem, now_ms, seen_ids
                )
                freetube_playlists.extend(found)
                skipped_non_yt += skipped

    # 3. Direct folder fallback (user pointed straight at files)
    if not playlists_dir and not stores_dir:
        try:
            entries = sorted(root_dir.iterdir())
        except OSError:
            entries = []
        for item in entries:
            data, raw = read_file_content(item)
            if data is None and raw is None:
                continue
            found, skipped = extract_playlists_from_data(
                data, raw, item.stem, now_ms, seen_ids
            )
            freetube_playlists.extend(found)
            skipped_non_yt += skipped

    # 4. SQLite fallback if no JSON playlist files were found
    if not freetube_playlists:
        try:
            root_entries = sorted(root_dir.iterdir())
        except OSError:
            root_entries = []
        for item in root_entries:
            if item.is_file() and item.name != "grayjay_freetube_playlists.db" and is_sqlite_file(item):
                found, skipped = extract_from_sqlite(item, now_ms, seen_ids)
                freetube_playlists.extend(found)
                skipped_non_yt += skipped

    # 5. Watch Later items
    if include_watch_later:
        wl_videos = []
        seen_wl = set()

        def ingest_wl_entry(entry):
            nonlocal skipped_non_yt
            ft_vid = convert_video(entry, now_ms + len(wl_videos))
            if ft_vid:
                if ft_vid["videoId"] not in seen_wl:
                    seen_wl.add(ft_vid["videoId"])
                    wl_videos.append(ft_vid)
            elif isinstance(entry, dict) and (ci_get(entry, "url") or ci_get(entry, "id")):
                skipped_non_yt += 1
            elif isinstance(entry, str) and entry.strip().startswith(("http://", "https://")):
                skipped_non_yt += 1

        if wl_dir and wl_dir.is_dir():
            try:
                wl_entries = sorted(wl_dir.iterdir())
            except OSError:
                wl_entries = []
            for item in wl_entries:
                data, raw = read_file_content(item)
                if data is not None:
                    entries = data if isinstance(data, list) else [data]
                    for video in entries:
                        ingest_wl_entry(video)
                elif raw:
                    for line in raw.splitlines():
                        if line.strip():
                            ingest_wl_entry(line.strip())

        if stores_dir and stores_dir.is_dir() and not wl_videos:
            try:
                store_entries = sorted(stores_dir.iterdir())
            except OSError:
                store_entries = []
            for item in store_entries:
                if "watchlater" in item.name.lower() or "watch_later" in item.name.lower():
                    data, raw = read_file_content(item)
                    if data is not None:
                        entries = data if isinstance(data, list) else [data]
                        for video in entries:
                            ingest_wl_entry(video)
                    elif raw:
                        for line in raw.splitlines():
                            if line.strip():
                                ingest_wl_entry(line.strip())

        if wl_videos:
            freetube_playlists.append(
                {
                    "playlistName": "Grayjay Watch Later",
                    "protected": False,
                    "description": "Imported from Grayjay Desktop Watch Later",
                    "videos": wl_videos,
                    "_id": f"ft-playlist--{uuid.uuid4()}",
                    "createdAt": now_ms,
                    "lastUpdatedAt": now_ms,
                }
            )

    total_videos = sum(len(pl["videos"]) for pl in freetube_playlists)
    return freetube_playlists, total_videos, skipped_non_yt


def get_candidate_folders(script_dir: Path):
    """Return likely Grayjay Desktop folders in priority order."""
    raw_candidates = [script_dir, script_dir.parent, Path.cwd()]

    if sys.platform == "win32":
        for env_var, rel in (
            ("APPDATA", "Grayjay"),
            ("LOCALAPPDATA", "Grayjay"),
            ("LOCALAPPDATA", r"Programs\Grayjay"),
        ):
            base = os.environ.get(env_var)
            if base:
                raw_candidates.append(Path(base) / rel)
    elif sys.platform == "darwin":
        home = Path.home()
        raw_candidates.extend(
            [
                home / "Library" / "Application Support" / "Grayjay",
                home / "Grayjay",
            ]
        )
    else:
        home = Path.home()
        xdg_data = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
        xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        raw_candidates.extend(
            [
                xdg_data / "Grayjay",
                xdg_config / "Grayjay",
                home / "Grayjay",
                home / ".var" / "app" / "app.grayjay.Grayjay" / "data" / "Grayjay",
            ]
        )

    unique = []
    seen = set()
    for folder in raw_candidates:
        try:
            resolved = folder.expanduser().resolve()
        except OSError:
            continue
        if resolved.is_dir() and resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Export Grayjay Desktop playlists into a FreeTube-compatible .db file."
    )
    parser.add_argument(
        "source",
        nargs="?",
        help="Path to your Grayjay folder or playlists subfolder (auto-detected if omitted).",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output .db file path (default: grayjay_freetube_playlists.db next to this script).",
    )
    parser.add_argument(
        "--no-watch-later",
        action="store_true",
        help="Skip exporting Grayjay's Watch Later list.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview detected playlists without writing an output file.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    script_dir = Path(__file__).resolve().parent
    include_wl = not args.no_watch_later

    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else script_dir / "grayjay_freetube_playlists.db"
    )

    found_source = None
    playlists = []
    total_videos = 0
    skipped = 0

    if args.source:
        source_path = Path(args.source).expanduser().resolve()
        if not source_path.is_dir():
            print(f"Error: Folder not found: {source_path}")
            return 1
        playlists, total_videos, skipped = collect_playlists(
            source_path, include_watch_later=include_wl
        )
        found_source = source_path
    else:
        candidates = get_candidate_folders(script_dir)
        for candidate in candidates:
            playlists, total_videos, skipped = collect_playlists(
                candidate, include_watch_later=include_wl
            )
            if playlists:
                found_source = candidate
                break

        if not playlists:
            print("Could not automatically find Grayjay playlists in these folders:")
            for candidate in candidates:
                print(f"  - {candidate}")
            print()
            print("Tip: Drop this tool inside your Grayjay folder (the one containing a")
            print("'playlists' subfolder) or drag your Grayjay folder onto")
            print("Export_Grayjay_to_FreeTube.bat.")
            return 1

    if not playlists:
        print(f"No importable YouTube playlists were found inside: {found_source}")
        print("Make sure the folder contains your Grayjay 'playlists' or 'watchLater' directory.")
        return 1

    print(f"Source folder: {found_source}")
    print(f"Found {len(playlists)} playlist(s) ({total_videos} YouTube videos):")
    for pl in playlists:
        print(f"  - {pl['playlistName']} ({len(pl['videos'])} videos)")

    if skipped:
        print()
        print(
            f"Note: Skipped {skipped} non-YouTube or unrecognized item(s), "
            "since FreeTube only supports YouTube videos."
        )

    if args.dry_run:
        print()
        print("Dry run complete — no file was written.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as out:
        for pl in playlists:
            out.write(json.dumps(pl, ensure_ascii=False) + "\n")

    print()
    print("Saved FreeTube file to:")
    print(f"  {output_path}")
    print()
    print("Next step in FreeTube:")
    print("  Settings -> Data Settings -> Import Playlists -> select the .db file above.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

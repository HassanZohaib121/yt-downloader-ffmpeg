"""Local storage, validation, stream probing, and FFmpeg download jobs."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import queue
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit

APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
HOST_NAME = "local.media_link_capture"
EXTENSION_ID = "media-link-inspector@local.example"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

OUTPUT_FORMATS = ("mkv", "mp4", "mov", "webm")

def title_filename(title, extension="mkv"):
    if extension not in OUTPUT_FORMATS:
        raise ValueError("Choose MKV, MP4, MOV, or WebM.")
    title = re.sub(r"\s+-\s+YouTube\s*$", "", str(title), flags=re.I).strip()
    title = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", title).strip(" .")
    title = title[:140].rstrip(" .") or "video"
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", title, re.I):
        title = "_" + title
    return title + "." + extension

def change_extension(filename, extension):
    if extension not in OUTPUT_FORMATS:
        raise ValueError("Unsupported output format.")
    path = Path(filename)
    stem = path.stem if path.suffix.lower().lstrip(".") in OUTPUT_FORMATS else filename
    return stem + "." + extension

def validate_url(value):
    if not isinstance(value, str) or not value or len(value) > 24000:
        raise ValueError("A media URL is missing or too long.")
    if any(ord(c) < 32 for c in value):
        raise ValueError("The URL contains control characters.")
    parsed = urlsplit(value)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        raise ValueError("Only HTTP and HTTPS media URLs are accepted.")
    return value

def validate_capture(payload):
    if not isinstance(payload, dict) or payload.get("action") not in ("capture", "open"):
        raise ValueError("Unknown app action.")
    choices = payload.get("choices", [])
    if not isinstance(choices, list) or len(choices) > 100:
        raise ValueError("At most 100 sources can be sent at a time.")
    clean = []
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("Invalid source.")
        kind = choice.get("kind")
        if kind not in ("single", "pair", "existing"):
            raise ValueError("Invalid source type.")
        item = {"kind": kind, "label": str(choice.get("label", "Captured media"))[:240]}
        if kind in ("single", "pair"):
            item["video"] = validate_url(choice.get("video"))
        if kind in ("pair", "existing"):
            item["audio"] = validate_url(choice.get("audio"))
        clean.append(item)
    return {"action": payload["action"], "title": str(payload.get("title", "Browser capture"))[:240], "choices": clean}

@contextmanager
def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DATA_DIR / "captures.sqlite3", timeout=10)
    db.execute("CREATE TABLE IF NOT EXISTS captures (id INTEGER PRIMARY KEY, created REAL NOT NULL, title TEXT NOT NULL, choices TEXT NOT NULL)")
    try:
        with db:
            yield db
    finally:
        db.close()

def add_capture(payload):
    payload = validate_capture(payload)
    if not payload["choices"]:
        return None
    with connect() as db:
        cursor = db.execute("INSERT INTO captures(created,title,choices) VALUES(?,?,?)",
                            (time.time(), payload["title"], json.dumps(payload["choices"])))
        ident = cursor.lastrowid
        db.execute("DELETE FROM captures WHERE id NOT IN (SELECT id FROM captures ORDER BY id DESC LIMIT 100)")
    return ident

def list_captures():
    with connect() as db:
        return [{"id": r[0], "created": r[1], "title": r[2], "choices": json.loads(r[3])}
                for r in db.execute("SELECT id,created,title,choices FROM captures ORDER BY id DESC")]

def delete_capture(ident):
    with connect() as db:
        db.execute("DELETE FROM captures WHERE id=?", (int(ident),))

def load_settings():
    defaults = {"ffmpeg": shutil.which("ffmpeg") or r"C:\ffmpeg\bin\ffmpeg.exe",
                "folder": str(APP_DIR / "downloads"), "format": "mkv"}
    try:
        defaults.update(json.loads((DATA_DIR / "settings.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    return defaults

def save_settings(settings):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp = DATA_DIR / "settings.tmp"
    temp.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    temp.replace(DATA_DIR / "settings.json")

def tool_paths(ffmpeg):
    ffmpeg = Path(ffmpeg)
    probe = ffmpeg.with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    if not ffmpeg.is_file():
        raise ValueError("Choose a valid ffmpeg executable.")
    if not probe.is_file():
        raise ValueError("ffprobe must be in the same folder as ffmpeg.")
    return str(ffmpeg), str(probe)

def probe_source(probe, source, cancel, process_callback=lambda p: None):
    command = [probe, "-v", "error", "-rw_timeout", "15000000", "-show_entries",
               "stream=index,codec_type,codec_name:format=duration", "-of", "json", source]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=NO_WINDOW)
    process_callback(process)
    deadline = time.monotonic() + 35
    try:
        while True:
            if cancel.is_set():
                raise InterruptedError("Cancelled.")
            if time.monotonic() > deadline:
                raise TimeoutError("Stream check timed out. Capture a fresh URL and try again.")
            try:
                stdout, stderr = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode:
            detail = stderr.decode("utf-8", "replace")[-3000:]
            raise ValueError("Cannot read this source. Its URL may have expired or require browser session data.\n" + detail)
        data = json.loads(stdout)
        if not data.get("streams"):
            raise ValueError("No media streams found in this source.")
        return data
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()
        process_callback(None)

def command_for(ffmpeg, choice, output, local_video=None):
    args = [ffmpeg, "-hide_banner", "-n", "-loglevel", "warning", "-nostats", "-progress", "pipe:1"]
    def source(value, remote=True):
        if remote:
            validate_url(value)
            args.extend(["-rw_timeout", "15000000"])
        args.extend(["-i", value])
    if choice["kind"] == "existing":
        if not local_video or not Path(local_video).is_file():
            raise ValueError("Choose the downloaded video file.")
        source(str(local_video), False)
    else:
        source(choice["video"])
    if choice["kind"] in ("pair", "existing"):
        source(choice["audio"])
        args.extend(["-map", "0:v:0", "-map", "1:a:0"])
    else:
        args.extend(["-map", "0:v:0?", "-map", "0:a:0?"])
    args.extend(["-c", "copy", str(output)])
    return args

class DownloadJob:
    def __init__(self, ffmpeg, choice, output, events, local_video=None):
        self.ffmpeg, self.choice, self.output = ffmpeg, choice, Path(output)
        self.events, self.local_video = events, local_video
        self.cancelled = threading.Event()
        self.process = None
        self.downloading = False

    def emit(self, kind, value):
        self.events.put((kind, value))

    def cancel(self):
        self.cancelled.set()

    def run(self):
        try:
            ffmpeg, ffprobe = tool_paths(self.ffmpeg)
            if self.output.exists():
                raise ValueError("The output file already exists. Choose another filename.")
            self.output.parent.mkdir(parents=True, exist_ok=True)
            first = self.local_video if self.choice["kind"] == "existing" else self.choice["video"]
            self.emit("status", "Checking streams…")
            info = probe_source(ffprobe, first, self.cancelled, lambda p: setattr(self, "process", p))
            types = {stream["codec_type"] for stream in info["streams"]}
            if self.choice["kind"] in ("pair", "existing"):
                if "video" not in types:
                    raise ValueError("The selected video source has no video stream.")
                audio_info = probe_source(ffprobe, self.choice["audio"], self.cancelled, lambda p: setattr(self, "process", p))
                if not any(stream["codec_type"] == "audio" for stream in audio_info["streams"]):
                    raise ValueError("The selected audio source has no audio stream. Capture an actual audio source.")
            elif "audio" not in types:
                raise ValueError("This source has no audio. Send a video + audio pair from Firefox to download with sound.")
            try:
                duration = float(info.get("format", {}).get("duration", 0))
            except (TypeError, ValueError):
                duration = 0
            if self.cancelled.is_set():
                raise InterruptedError("Cancelled.")
            command = command_for(ffmpeg, self.choice, self.output, self.local_video)
            self.process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, text=True, encoding="utf-8",
                                            errors="replace", bufsize=1, creationflags=NO_WINDOW)
            self.downloading = True
            self.emit("status", "Downloading and combining streams…")
            def errors():
                for line in self.process.stderr:
                    self.emit("log", line.rstrip())
            def cancel_watch():
                while self.process and self.process.poll() is None:
                    if self.cancelled.wait(0.1):
                        try:
                            self.process.stdin.write("q\n")
                            self.process.stdin.flush()
                        except (OSError, ValueError):
                            pass
                        try:
                            self.process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                        return
            error_thread = threading.Thread(target=errors, daemon=True)
            error_thread.start()
            threading.Thread(target=cancel_watch, daemon=True).start()
            progress = {}
            for line in self.process.stdout:
                key, separator, value = line.strip().partition("=")
                if separator:
                    progress[key] = value
                if key == "progress":
                    seconds = max(0, int(progress.get("out_time_us", "0"))) / 1000000 if progress.get("out_time_us", "0").lstrip("-").isdigit() else 0
                    self.emit("progress", {"seconds": seconds, "speed": progress.get("speed", ""),
                                          "percent": min(99.9, seconds / duration * 100) if duration > 0 else None})
            code = self.process.wait()
            error_thread.join(timeout=2)
            if self.cancelled.is_set():
                raise InterruptedError("Cancelled. A partial file may remain.")
            if code:
                raise ValueError("FFmpeg failed. See the details below. If the selected container does not support these codecs, choose MKV. A partial output may remain.")
            self.emit("done", str(self.output))
        except InterruptedError as exc:
            self.emit("cancelled", str(exc))
        except Exception as exc:
            self.emit("error", str(exc))
        finally:
            if self.process and self.process.poll() is None:
                self.process.kill()
                self.process.wait()
            self.process = None

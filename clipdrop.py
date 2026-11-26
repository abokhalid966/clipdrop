"""
ClipDrop - your own game clipper. Keeps the last few seconds of gameplay in
the background, saves a clip when you press a hotkey, and lets you watch,
edit, sort and save your clips on your PC and iPhone over Wi-Fi.

Files:
  clipdrop.py     this file: settings, clip library, web server, tray icon
  recorder.py     the replay buffer (FFmpeg)
  winutil.py      hotkeys, game detection, monitors, in-game pop-up, sounds
  web/app.html    the ClipDrop page (phone and PC)
  web/help.html   how to use it
  web/shortcut.html  setting up auto-send to iPhone Photos
  settings.json   your settings (created on first run, safe to edit)

Run:  ClipDrop from the Start Menu, or start.bat to see messages.
"""

import hashlib
import html
import json
import mimetypes
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# the bundled Python doesn't look next to this file for modules, so tell it to
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import recorder as rec_mod  # noqa: E402
import winutil  # noqa: E402

VERSION = "5.9"
UPDATE_REPO = os.environ.get("CLIPDROP_UPDATE_REPO", "abokhalid966/clipdrop")  # where new versions are published
HERE = Path(__file__).resolve().parent
SETTINGS_FILE = HERE / "settings.json"
WEB_DIR = HERE / "web"
CACHE_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / ".cache")) / "ClipDrop"
THUMB_DIR = CACHE_DIR / "thumbs"
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".webm", ".mkv"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".heif", ".bmp"}
PHOTOS_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".heic", ".heif", ".mp4", ".mov", ".m4v"}  # what iPhone Photos accepts
SETTLE_SECONDS = 3
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LOG_MAX_BYTES = 5 * 1024 * 1024
GAME_GONE_GRACE = 20  # seconds to keep recording after the game closes ("only while gaming")

DEFAULTS = {
    # recording
    "recording_on": True,
    "record_when": "always",     # always | game  (only while a game is open)
    "capture": "screen",         # screen | window (only the game window)
    "video_format": "h264",      # h264 | hevc | av1
    "fps": 60,
    "bitrate": "20M",
    "height": 0,                 # 0 = same as screen, or 1440 / 1080 / 720
    "encoder": "auto",
    "monitor": 0,
    "show_mouse": False,
    # hotkeys: each saves a different length
    "hotkeys": [{"keys": "ctrl+f9", "seconds": 30}],
    # sound
    "game_audio": True,
    "speaker_device": "",        # "" = Windows default
    "game_volume": 100,
    "microphone": False,
    "mic_device": "",
    "mic_volume": 100,
    # feedback
    "save_sound": "click",       # click | chime | off  (plays the moment you press the hotkey)
    "overlay": True,
    # clips
    "name_by_game": True,
    "save_folder": "~/Videos/ClipDrop",
    "extra_folders": [],
    "extra_games": [],           # programs that always count as games (e.g. "minecraft")
    "not_games": [],             # programs that never count as games
    # sharing files between PC and phone
    "share_folder": "~/Downloads/ClipDrop Shared",
    "share_to_photos": True,     # photos/videos sent from the PC go to iPhone Photos with auto-send
    "notify_files": True,        # pop-up + sound on the PC when files arrive from the phone
    # app
    "language": "auto",          # auto | en | ar
    "update_check": True,        # look for a new version at start and once a day
    "update_auto": False,        # install it without asking
    "port": 8765,
    "start_with_windows": False,
}

mimetypes.add_type("video/mp4", ".mp4")
mimetypes.add_type("video/mp4", ".m4v")
mimetypes.add_type("video/quicktime", ".mov")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("video/x-matroska", ".mkv")
mimetypes.add_type("image/heic", ".heic")
mimetypes.add_type("image/heif", ".heif")
mimetypes.add_type("image/webp", ".webp")


# ================================================================ language

TEXT_AR = {
    "Open ClipDrop": "فتح ClipDrop",
    "Save clip now ({keys}, {secs}s)": "حفظ مقطع الآن ({keys}، {secs} ث)",
    "Recording on": "التسجيل يعمل",
    "Send files to phone": "إرسال ملفات للجوال",
    "Connect phone (QR code)": "ربط الجوال (رمز QR)",
    "Open clips folder": "فتح مجلد المقاطع",
    "Open shared files folder": "فتح مجلد الملفات المشتركة",
    "Help": "المساعدة",
    "Quit ClipDrop": "إغلاق ClipDrop",
    "Clip saved  •  {secs}s": "تم حفظ المقطع  •  {secs} ث",
    "Couldn't save the clip": "تعذّر حفظ المقطع",
    "Saving clip...": "جارٍ حفظ المقطع...",
    "{n} file(s) from {device}": "{n} ملف من {device}",
    "Check for updates": "البحث عن تحديثات",
    "Install update {v}": "تثبيت التحديث {v}",
    "ClipDrop {v} is ready": "ClipDrop {v} جاهز",
    "Open ClipDrop to see what's new and update.": "افتح ClipDrop لتشوف الجديد وتحدّث.",
    "Updating ClipDrop to {v}...": "جارٍ تحديث ClipDrop إلى {v}...",
    "ClipDrop updated to {v}": "تم تحديث ClipDrop إلى {v}",
    "Sent to your phone: {n} file(s)": "جاهز لجوالك: {n} ملف",
    "ClipDrop isn't running and couldn't be started.": "ClipDrop لا يعمل وتعذّر تشغيله.",
    "Recording was off. It's on again now, so your next clip will work.":
        "كان التسجيل متوقف. شغّلناه الحين، والمقطع الجاي بينحفظ.",
    "Recording is off": "التسجيل متوقف",
    "Press your clip key or open ClipDrop to turn it back on.":
        "اضغط زر حفظ المقطع أو افتح ClipDrop عشان ترجّعه.",
    "Recording is on again": "رجع التسجيل يشتغل",
}


def ui_lang(settings):
    lang = settings.get("language", "auto")
    if lang in ("en", "ar"):
        return lang
    if sys.platform == "win32":
        try:
            import ctypes
            if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x01:
                return "ar"
        except Exception:
            pass
    return "en"


def tr(settings, text, **kw):
    if ui_lang(settings) == "ar":
        text = TEXT_AR.get(text, text)
    return text.format(**kw) if kw else text


# ================================================================ settings

def load_settings():
    s = dict(DEFAULTS)
    raw = {}
    if SETTINGS_FILE.exists():
        try:
            raw = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            s.update(raw)
        except Exception as e:
            print(f"settings.json has a mistake, using defaults for now: {e}")
    # older versions had one hotkey + one clip length
    if "hotkey" in raw and "hotkeys" not in raw:
        s["hotkeys"] = [{"keys": raw["hotkey"], "seconds": int(raw.get("clip_seconds", 30))}]
    # before 5.6 the clip sound was just on/off
    if raw.get("sound_on_save") is False and "save_sound" not in raw:
        s["save_sound"] = "off"
    for old in ("hotkey", "clip_seconds", "sound_on_save"):
        s.pop(old, None)
    if not s.get("phone_key"):
        s["phone_key"] = secrets.token_urlsafe(6)
    save_settings(s)
    return s


def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, indent=2), encoding="utf-8")


def clean_settings(new, current):
    """Check values coming from the settings page. Raises ValueError with a friendly message."""
    out = {}
    for k, v in new.items():
        if k not in DEFAULTS:
            continue
        d = DEFAULTS[k]
        if k == "hotkeys":
            hks = []
            for h in v or []:
                keys = str(h.get("keys", "")).strip().lower()
                if not keys:
                    continue
                winutil.parse_hotkey(keys)  # raises ValueError if it's not a real key
                secs = int(h.get("seconds", 30))
                if not 5 <= secs <= 600:
                    raise ValueError("Clip length must be between 5 seconds and 10 minutes")
                hks.append({"keys": keys, "seconds": secs})
            if not hks:
                raise ValueError("Keep at least one hotkey")
            if len({h["keys"] for h in hks}) != len(hks):
                raise ValueError("Two hotkeys use the same keys")
            out[k] = hks[:8]
        elif isinstance(d, bool):
            out[k] = bool(v)
        elif isinstance(d, int):
            out[k] = int(v)
        elif isinstance(d, list):
            if isinstance(v, str):
                v = re.split(r"[,\n]", v)
            out[k] = [str(x).strip() for x in v if str(x).strip()]
        else:
            out[k] = str(v)
    if "save_folder" in out:
        out["save_folder"] = out["save_folder"].strip().strip('"')
        if not out["save_folder"]:
            raise ValueError("Pick a folder for your clips")
    if out.get("record_when", "always") not in ("always", "game"):
        raise ValueError("Unknown recording option")
    if out.get("capture", "screen") not in ("screen", "window"):
        raise ValueError("Unknown capture option")
    if out.get("language", "auto") not in ("auto", "en", "ar"):
        raise ValueError("Unknown language")
    if out.get("save_sound", "click") not in winutil.SOUNDS:
        raise ValueError("Unknown sound")
    if out.get("video_format", "h264") not in ("h264", "hevc", "av1"):
        raise ValueError("Unknown video format")
    if "bitrate" in out and not re.fullmatch(r"\d{1,3}(\.\d)?[MK]", out["bitrate"]):
        raise ValueError("Quality must look like 20M")
    if "fps" in out and not 10 <= out["fps"] <= 240:
        raise ValueError("Frames per second must be between 10 and 240")
    if "height" in out and not (out["height"] == 0 or 240 <= out["height"] <= 4320):
        raise ValueError("Unknown video size")
    for vol in ("game_volume", "mic_volume"):
        if vol in out:
            out[vol] = max(0, min(200, out[vol]))
    return out


def expand(p):
    return Path(os.path.expandvars(os.path.expanduser(p)))


def lan_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("10.255.255.255", 1))  # nothing is actually sent
        return sock.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        sock.close()


def fatal(msg):
    """Show an error, as a popup when there is no console window."""
    print(msg)
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, msg, "ClipDrop", 0x10)
        except Exception:
            pass
    sys.exit(1)


def startup_file():
    return Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/ClipDrop.vbs"


def autostart_on():
    return startup_file().exists()


def set_autostart(on):
    """Start ClipDrop when you sign in to Windows (a tiny script in the Startup folder)."""
    if sys.platform != "win32":
        return
    link = startup_file()
    if on:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_text(f'CreateObject("WScript.Shell").Run """{HERE / "ClipDrop.vbs"}""", 0\r\n',
                        encoding="utf-8")
    else:
        link.unlink(missing_ok=True)


def find_ffmpeg():
    """Use the FFmpeg the installer put next to the app, else the one on PATH."""
    local = HERE / "runtime" / "ffmpeg"
    exe = ".exe" if sys.platform == "win32" else ""
    if (local / f"ffmpeg{exe}").exists():
        return str(local / f"ffmpeg{exe}"), str(local / f"ffprobe{exe}")
    return shutil.which("ffmpeg"), shutil.which("ffprobe")


def safe_name(name):
    name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", name).strip().rstrip(".")
    return name[:120]


def unique_path(p):
    if not p.exists():
        return p
    i = 2
    while True:
        q = p.with_name(f"{p.stem} ({i}){p.suffix}")
        if not q.exists():
            return q
        i += 1


def fingerprint(size, mtime):
    # size + time survive renames, so favorites and "already sent" stick to the clip
    return f"{size}-{int(mtime)}"


class JsonStore:
    """A small JSON file in %LOCALAPPDATA%\\ClipDrop."""

    def __init__(self, name, default):
        self.file = CACHE_DIR / name
        self.lock = threading.RLock()
        try:
            self.data = json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            self.data = default

    def save(self):
        with self.lock:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data), encoding="utf-8")
            os.replace(tmp, self.file)


# ================================================================ clip library

class Library:
    def __init__(self, app):
        self.app = app
        self._lock = threading.Lock()
        self._by_id = {}
        self._cache = []
        self._at = 0
        self.ours = set()  # files ClipDrop just wrote: complete, no need to wait for them to settle
        self.meta = JsonStore("meta.json", {})  # fingerprint -> {"fav": bool, "dur": seconds}
        self._probe_q = []
        self._probe_evt = threading.Event()
        threading.Thread(target=self._prober, daemon=True).start()

    def folders(self):
        s = self.app.settings
        return [expand(s["save_folder"])] + [expand(f) for f in s.get("extra_folders", [])]

    def invalidate(self):
        self._at = 0

    def scan(self):
        with self._lock:
            if time.time() - self._at < 2:
                return self._cache
            clips, by_id, now = [], {}, time.time()
            missing = []
            for root in self.folders():
                if not root.exists():
                    continue
                for dirpath, dirnames, files in os.walk(root):
                    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                    for name in files:
                        if name.startswith("."):
                            continue
                        p = Path(dirpath) / name
                        if p.suffix.lower() not in VIDEO_EXTS:
                            continue
                        try:
                            st = p.stat()
                        except OSError:
                            continue
                        if st.st_size == 0 or (now - st.st_mtime < SETTLE_SECONDS and str(p) not in self.ours):
                            continue
                        cid = hashlib.sha1(str(p).encode("utf-8")).hexdigest()[:16]
                        rel = p.parent.relative_to(root)
                        fp = fingerprint(st.st_size, st.st_mtime)
                        m = self.meta.data.get(fp, {})
                        if "dur" not in m:
                            missing.append((fp, p))
                        clips.append({
                            "id": cid, "name": p.stem, "file": p.name,
                            "game": rel.parts[0] if rel.parts else "Other",
                            "ext": p.suffix.lower().lstrip("."),
                            "size": st.st_size, "mtime": st.st_mtime, "fp": fp,
                            "fav": bool(m.get("fav")), "duration": m.get("dur"),
                        })
                        by_id[cid] = p
            clips.sort(key=lambda c: c["mtime"], reverse=True)
            self._cache, self._by_id, self._at = clips, by_id, time.time()
            if missing:
                self._probe_q = missing
                self._probe_evt.set()
            return clips

    def _prober(self):
        """Finds clip lengths in the background (for sorting by length)."""
        while True:
            self._probe_evt.wait()
            self._probe_evt.clear()
            todo, self._probe_q = self._probe_q, []
            changed = False
            for fp, p in todo:
                try:
                    dur = self._duration(p)
                except Exception:
                    dur = 0
                with self.meta.lock:
                    self.meta.data.setdefault(fp, {})["dur"] = round(dur, 2)
                changed = True
            if changed:
                self.meta.save()
                self.invalidate()

    def _duration(self, p):
        r = subprocess.run([self.app.ffprobe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(p)], capture_output=True, timeout=20, creationflags=NO_WINDOW)
        return float((r.stdout or b"0").strip() or 0)

    def path(self, cid):
        self.scan()
        p = self._by_id.get(cid)
        if p is None:  # maybe it was just created
            self.invalidate()
            self.scan()
            p = self._by_id.get(cid)
        return p

    def clip(self, cid):
        self.path(cid)
        return next((c for c in self._cache if c["id"] == cid), None)

    def storage(self):
        clips = self.scan()
        root = expand(self.app.settings["save_folder"])
        try:
            du = shutil.disk_usage(root if root.exists() else root.anchor or "/")
            free, total = du.free, du.total
        except Exception:
            free = total = 0
        return {"clips_bytes": sum(c["size"] for c in clips), "count": len(clips),
                "free_bytes": free, "disk_bytes": total, "folder": str(root)}

    def thumb(self, cid):
        src = self.path(cid)
        if not src:
            return None
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        out = THUMB_DIR / f"{cid}.jpg"
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            return out
        subprocess.run([self.app.ffmpeg, "-y", "-loglevel", "error", "-ss", "1", "-i", str(src),
                        "-frames:v", "1", "-vf", "scale=480:-2", str(out)],
                       timeout=20, creationflags=NO_WINDOW)
        return out if out.exists() else None

    def set_fav(self, cid, on):
        c = self.clip(cid)
        if not c:
            raise ValueError("Clip not found")
        with self.meta.lock:
            self.meta.data.setdefault(c["fp"], {})["fav"] = bool(on)
        self.meta.save()
        self.invalidate()

    def rename(self, cid, new_name):
        p = self.path(cid)
        if not p:
            raise ValueError("Clip not found")
        new_name = safe_name(new_name)
        if not new_name:
            raise ValueError("Name can't be empty")
        target = unique_path(p.with_name(new_name + p.suffix))
        p.rename(target)
        if str(p) in self.ours:  # a clip saved a moment ago: show it right away under its new name
            self.ours.add(str(target))
        self.invalidate()
        return target

    def delete(self, cid):
        p = self.path(cid)
        if not p:
            raise ValueError("Clip not found")
        p.unlink()
        self.invalidate()

    def probe(self, cid):
        """Duration and number of audio tracks of a clip."""
        p = self.path(cid)
        if not p:
            raise ValueError("Clip not found")
        r = subprocess.run([self.app.ffprobe, "-v", "error", "-show_entries",
                            "format=duration:stream=codec_type,codec_name", "-of", "json", str(p)],
                           capture_output=True, timeout=20, creationflags=NO_WINDOW)
        info = json.loads(r.stdout or b"{}")
        streams = info.get("streams", [])
        audio = sum(1 for st in streams if st.get("codec_type") == "audio")
        vcodec = next((st.get("codec_name") for st in streams if st.get("codec_type") == "video"), "")
        return {"duration": float(info.get("format", {}).get("duration") or 0),
                "audio_tracks": audio, "video_codec": vcodec}

    def strip(self, cid, count=10):
        """One image with `count` small frames side by side, for the trim timeline."""
        src = self.path(cid)
        if not src:
            return None
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        out = THUMB_DIR / f"{cid}_strip.jpg"
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            return out
        dur = self.probe(cid)["duration"] or 1
        subprocess.run([self.app.ffmpeg, "-y", "-loglevel", "error", "-i", str(src),
                        "-vf", f"fps={count / dur:.5f},scale=160:-2,tile={count}x1",
                        "-frames:v", "1", "-q:v", "5", str(out)],
                       timeout=60, creationflags=NO_WINDOW)
        return out if out.exists() else None

    def export(self, cid, keep, game_vol=1.0, voice_vol=1.0, share=False, replace=False):
        """Make a new clip from the parts in `keep` ([[start, end], ...] seconds).

        - Re-encodes so cuts are exact, in the same format as the original.
        - Clips with a separate voice track get their own game/voice volume.
        - share=True makes a small 720p H.264 copy (aims for ~15 MB) for WhatsApp/Snapchat.
        - replace=True overwrites the original instead of saving a copy.
        """
        p = self.path(cid)
        if not p:
            raise ValueError("Clip not found")
        info = self.probe(cid)
        dur = info["duration"]
        parts = []
        for a, b in keep or [[0, dur]]:
            a, b = max(0.0, float(a)), min(dur, float(b)) if dur else float(b)
            if b - a >= 0.1:
                parts.append((a, b))
        parts.sort()
        total = sum(b - a for a, b in parts)
        if total < 0.5:
            raise ValueError("The clip must be at least half a second long")
        game_vol, voice_vol = max(0.0, float(game_vol)), max(0.0, float(voice_vol))

        # --- audio source: separate tracks if we have them, else the only track
        tracks = info["audio_tracks"]
        if tracks >= 3:
            amix = (f"[0:a:1]volume={game_vol}[ga];[0:a:2]volume={voice_vol}[vo];"
                    f"[ga][vo]amix=inputs=2:normalize=0[asrc]")
        elif tracks >= 1:
            amix = f"[0:a:0]volume={game_vol}[asrc]"
        else:
            amix = ""

        vscale = "scale=-2:'min(720,ih)'," if share else ""
        n = len(parts)
        fc = [f"[0:v]{vscale}split={n}" + "".join(f"[v{i}]" for i in range(n))] if n > 1 else []
        if amix:
            fc.append(amix)
            if n > 1:
                fc.append(f"[asrc]asplit={n}" + "".join(f"[a{i}]" for i in range(n)))
        for i, (a, b) in enumerate(parts):
            vin = f"[v{i}]" if n > 1 else f"[0:v]{vscale}"
            fc.append(f"{vin}trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[vt{i}]")
            if amix:
                ain = f"[a{i}]" if n > 1 else "[asrc]"
                fc.append(f"{ain}atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[at{i}]")
        if amix:
            fc.append("".join(f"[vt{i}][at{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[vout][aout]")
        else:
            fc.append("".join(f"[vt{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vout]")

        if share:
            enc = self.app.encoder_for("h264")  # H.264 plays everywhere
            # bitrate so the whole clip fits in about 14 MB, never more than 6 Mbit/s
            vbr = int(min(6_000_000, max(800_000, 14 * 8_000_000 / total - 128_000)))
            vargs = ["-c:v", enc, "-b:v", str(vbr), "-maxrate", str(vbr), "-bufsize", str(vbr * 2)]
            aargs = ["-c:a", "aac", "-b:a", "128k"]
        else:
            fmt = {"hevc": "hevc", "av1": "av1"}.get(info.get("video_codec"), "h264")
            enc = self.app.encoder_for(fmt)
            vargs = ["-c:v", enc, "-b:v", self.app.settings["bitrate"]] + rec_mod.mp4_tag(enc)
            aargs = ["-c:a", "aac", "-b:a", "192k"]

        suffix = " (share)" if share else " (edited)"
        out = unique_path(p.with_name(f"{p.stem}{suffix}.mp4"))
        tmp = p.with_name(f".{p.stem}.tmp.mp4")
        cmd = [self.app.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(p),
               "-filter_complex", ";".join(fc), "-map", "[vout]"]
        if amix:
            cmd += ["-map", "[aout]"]
        cmd += vargs + ["-pix_fmt", "yuv420p"] + (aargs if amix else []) + ["-movflags", "+faststart", str(tmp)]
        r = subprocess.run(cmd, capture_output=True, timeout=900, creationflags=NO_WINDOW)
        if r.returncode != 0 or not tmp.exists():
            tmp.unlink(missing_ok=True)
            raise RuntimeError(r.stderr.decode("utf-8", "replace")[-300:] or "FFmpeg failed")
        if replace and not share:
            final = p.with_suffix(".mp4")
            p.unlink()
            tmp.rename(final)
            out = final
        else:
            tmp.rename(out)
        self.ours.add(str(out))
        self.invalidate()
        return out


# ================================================================ shared files

def file_type(ext):
    ext = ext.lower()
    if ext in VIDEO_EXTS:
        return "video"
    if ext in IMAGE_EXTS:
        return "image"
    if ext in {".mp3", ".m4a", ".wav", ".aac", ".flac", ".ogg", ".opus"}:
        return "audio"
    if ext in {".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".pages", ".key", ".numbers"}:
        return "doc"
    if ext in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return "zip"
    return "other"


class Shared:
    """Files sent between the PC and phones. They live in the shared folder:
    "From PC" holds what the PC sent, "From <phone name>" what each phone sent.
    The folder tells who sent a file; shared.json remembers what kind of
    device each phone is (iPhone, Android...) for its icon."""

    def __init__(self, app):
        self.app = app
        self.meta = JsonStore("shared.json", {})
        self._by_id = {}
        self._cache, self._at = [], 0
        self._lock = threading.Lock()
        self._incoming = {}   # device -> count, for the "files arrived" pop-up
        self._notify_timer = None
        self.pc_name = socket.gethostname() or "PC"

    def root(self):
        return expand(self.app.settings.get("share_folder") or DEFAULTS["share_folder"])

    def invalidate(self):
        self._at = 0

    def scan(self):
        with self._lock:
            if time.time() - self._at < 1.5:
                return self._cache
            root, items, by_id = self.root(), [], {}
            if root.exists():
                for dirpath, dirnames, files in os.walk(root):
                    dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                    for name in files:
                        if name.startswith(".") or name.endswith(".part") or name.lower() == "desktop.ini":
                            continue
                        p = Path(dirpath) / name
                        try:
                            st = p.stat()
                        except OSError:
                            continue
                        fid = hashlib.sha1(("f:" + str(p)).encode("utf-8")).hexdigest()[:16]
                        fp = fingerprint(st.st_size, st.st_mtime)
                        top = p.parent.relative_to(root).parts
                        top = top[0] if top else ""
                        if top.lower().startswith("from ") and top.lower() != "from pc":
                            dev = top[5:]
                            m = {"from": "phone", "device": dev, "kind": self.meta.data.get(dev, "phone")}
                        else:   # "From PC", or put in the folder by hand
                            m = {"from": "pc", "device": self.pc_name, "kind": "pc"}
                        items.append({
                            "id": fid, "name": p.stem, "file": p.name, "ext": p.suffix.lower().lstrip("."),
                            "type": file_type(p.suffix), "size": st.st_size, "mtime": st.st_mtime, "fp": fp,
                            "from": m.get("from", "pc"), "device": m.get("device") or "", "kind": m.get("kind", "pc"),
                        })
                        by_id[fid] = p
            items.sort(key=lambda f: f["mtime"], reverse=True)
            self._cache, self._by_id, self._at = items, by_id, time.time()
            return items

    def path(self, fid):
        self.scan()
        p = self._by_id.get(fid)
        if p is None:
            self.invalidate()
            self.scan()
            p = self._by_id.get(fid)
        return p

    def item(self, fid):
        self.path(fid)
        return next((f for f in self._cache if f["id"] == fid), None)

    def _folder_for(self, origin, device):
        name = "From PC" if origin == "pc" else "From " + (safe_name(device)[:40] or "phone")
        d = self.root() / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _remember(self, p, origin, device, kind):
        dev = safe_name(device)[:40] or "phone"
        if origin == "phone" and self.meta.data.get(dev) != kind:
            with self.meta.lock:
                self.meta.data[dev] = kind
            self.meta.save()
        self.invalidate()

    def receive(self, read, length, name, origin, device, kind):
        """Save an upload. `read(n)` gives the next bytes; length=None means read until empty."""
        name = safe_name(name or "") or time.strftime("File %Y-%m-%d %H-%M-%S")
        folder = self._folder_for(origin, device)
        part = folder / f".{secrets.token_hex(4)}.part"
        got = 0
        try:
            with open(part, "wb") as f:
                while length is None or got < length:
                    chunk = read(min(1024 * 1024, (length - got) if length is not None else 1024 * 1024))
                    if not chunk:
                        break
                    f.write(chunk)
                    got += len(chunk)
            if (length is not None and got < length) or got == 0:
                raise ValueError("The upload stopped before the end. Try again.")
            final = unique_path(folder / name)
            os.replace(part, final)
        finally:
            part.unlink(missing_ok=True)
        self._remember(final, origin, device, kind)
        if origin == "phone":
            self._announce(device)
        return final

    def add_paths(self, paths):
        """Copy files from the PC (Explorer "Send to") into the shared folder."""
        folder, done = self._folder_for("pc", self.pc_name), []
        for raw in paths:
            src = Path(raw)
            if not src.is_file():
                continue
            dest = unique_path(folder / src.name)
            part = dest.with_name(f".{secrets.token_hex(4)}.part")
            shutil.copyfile(src, part)
            os.replace(part, dest)
            self._remember(dest, "pc", self.pc_name, "pc")
            done.append(dest)
        if done:
            s = self.app.settings
            if s.get("notify_files", True):
                winutil.show_overlay(tr(s, "Sent to your phone: {n} file(s)", n=len(done)), 2.5)
        return done

    def _announce(self, device):
        """One pop-up for a batch of files, a few seconds after the last one arrives."""
        s = self.app.settings
        if not s.get("notify_files", True):
            return
        with self._lock:
            self._incoming[device] = self._incoming.get(device, 0) + 1
            if self._notify_timer:
                self._notify_timer.cancel()

            def fire():
                with self._lock:
                    batch, self._incoming = self._incoming, {}
                for dev, n in batch.items():
                    winutil.ding(True)
                    winutil.show_overlay(tr(s, "{n} file(s) from {device}", n=n, device=dev), 3)
            self._notify_timer = threading.Timer(3, fire)
            self._notify_timer.daemon = True
            self._notify_timer.start()

    def rename(self, fid, new_name):
        p = self.path(fid)
        if not p:
            raise ValueError("File not found")
        new_name = safe_name(new_name)
        if not new_name:
            raise ValueError("Name can't be empty")
        target = unique_path(p.with_name(new_name + p.suffix))
        p.rename(target)
        self.invalidate()
        return target

    def delete(self, fid):
        p = self.path(fid)
        if not p:
            raise ValueError("File not found")
        p.unlink()
        self.invalidate()

    def thumb(self, fid):
        it, src = self.item(fid), self.path(fid)
        if not src or not it or it["type"] not in ("video", "image"):
            return None
        THUMB_DIR.mkdir(parents=True, exist_ok=True)
        out = THUMB_DIR / f"f_{fid}.jpg"
        if out.exists() and out.stat().st_mtime >= src.stat().st_mtime:
            return out
        cmd = [self.app.ffmpeg, "-y", "-loglevel", "error"]
        if it["type"] == "video":
            cmd += ["-ss", "1"]
        cmd += ["-i", str(src), "-frames:v", "1", "-vf", "scale=320:-2", str(out)]
        subprocess.run(cmd, timeout=20, creationflags=NO_WINDOW)
        if not out.exists() and it["type"] == "video":   # very short video: try the first frame
            subprocess.run([self.app.ffmpeg, "-y", "-loglevel", "error", "-i", str(src), "-frames:v", "1",
                            "-vf", "scale=320:-2", str(out)], timeout=20, creationflags=NO_WINDOW)
        return out if out.exists() else None

    def for_photos(self):
        """Photos and videos the PC sent, for the iPhone auto-send shortcut."""
        if not self.app.settings.get("share_to_photos", True):
            return []
        return [f for f in self.scan() if f["from"] == "pc" and "." + f["ext"] in PHOTOS_EXTS]


# ================================================================ auto-send

class Deliveries:
    """Remembers which clips each phone already has, so the iPhone Shortcut
    only downloads new ones. Stored in %LOCALAPPDATA%\\ClipDrop\\delivered.json."""

    def __init__(self):
        self.store = JsonStore("delivered.json", {})

    @property
    def data(self):
        return self.store.data

    def pending(self, device, clips):
        """Clips this device doesn't have yet, oldest first.
        The first time a device asks, everything already there counts as sent,
        so you don't get your whole history at once."""
        with self.store.lock:
            if device not in self.data:
                self.data[device] = [c["fp"] for c in clips]
                self.store.save()
                return []
            have = set(self.data[device])
            new = [c for c in clips if c["fp"] not in have and "(share)" not in c["name"]]
            return sorted(new, key=lambda c: c["mtime"])

    def mark(self, device, clip):
        with self.store.lock:
            lst = self.data.setdefault(device, [])
            if clip["fp"] not in lst:
                lst.append(clip["fp"])
                del lst[:-5000]
                self.store.save()

    def resend(self, clips):
        """Send these clips again to every phone (used by "Send to iPhone Photos")."""
        fps = {c["fp"] for c in clips}
        with self.store.lock:
            for device, lst in self.data.items():
                self.data[device] = [f for f in lst if f not in fps]
            self.store.save()


# ================================================================ updates

def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", v or "")[:4]) or (0,)


class Updater:
    """Looks for a newer ClipDrop on GitHub, downloads the setup, checks its
    SHA-256 fingerprint, then runs it quietly. The setup closes ClipDrop,
    updates the files (settings and clips stay) and starts it again.

    New versions are published as updates/latest.json + the setup .exe in the
    GitHub repository (see README, "Releasing a new version")."""

    BASE = "https://raw.githubusercontent.com/{repo}/main/updates/"

    def __init__(self, app):
        self.app = app
        self.lock = threading.Lock()
        self.state = {"status": "idle", "current": VERSION, "available": False, "version": "",
                      "notes_en": "", "notes_ar": "", "size": 0, "progress": 0, "error": "",
                      "checked_at": 0, "page": f"https://github.com/{UPDATE_REPO}/blob/main/updates/CHANGES.md"}
        self._release = None
        self._told = ""

    def _get(self, url, timeout=20):
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": f"ClipDrop/{VERSION}", "Cache-Control": "no-cache"})
        return urllib.request.urlopen(req, timeout=timeout)

    def check(self):
        with self.lock:
            if self.state["status"] in ("downloading", "installing"):
                return self.state
            self.state.update(status="checking", error="")
        try:
            base = self.BASE.format(repo=UPDATE_REPO)
            rel = json.loads(self._get(base + "latest.json").read())
            ver = str(rel.get("version") or "")
            name = os.path.basename(str(rel.get("file") or ""))
            sha = str(rel.get("sha256") or "").lower()
            ok = name.lower().endswith(".exe") and re.fullmatch(r"[0-9a-f]{64}", sha)
            newer = bool(ok and version_tuple(ver) > version_tuple(VERSION))
            self._release = ({"url": base + urllib.parse.quote(name), "name": name, "sha256": sha,
                              "size": int(rel.get("size") or 0), "version": ver} if newer else None)
            self.state.update(status="idle", available=newer, version=ver if newer else "",
                              notes_en=str(rel.get("notes_en") or "") if newer else "",
                              notes_ar=str(rel.get("notes_ar") or "") if newer else "",
                              size=int(rel.get("size") or 0) if newer else 0, checked_at=time.time())
            if newer:
                print(f"Update available: {ver}")
        except Exception as e:
            msg = str(e)
            if "404" in msg:   # no versions published yet
                self.state.update(status="idle", available=False, checked_at=time.time())
            else:
                self.state.update(status="error", error="Couldn't check for updates. Are you online?")
                print(f"Update check failed: {e}")
        return self.state

    def install(self):
        """Download, verify and start the new setup (in the background)."""
        with self.lock:
            if not self._release:
                raise ValueError("No update to install")
            if self.state["status"] in ("downloading", "installing"):
                return
            self.state.update(status="downloading", progress=0, error="")
        threading.Thread(target=self._install, daemon=True).start()

    def _install(self):
        rel = self._release
        folder = CACHE_DIR / "update"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            for old in folder.glob("*"):
                old.unlink(missing_ok=True)
            want = rel["sha256"]
            exe = folder / rel["name"]
            h, got, total = hashlib.sha256(), 0, rel["size"] or 1
            with self._get(rel["url"], timeout=60) as r, open(exe, "wb") as f:
                while True:
                    chunk = r.read(256 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    got += len(chunk)
                    self.state["progress"] = min(99, int(got * 100 / total))
            if h.hexdigest() != want:
                exe.unlink(missing_ok=True)
                raise RuntimeError("The download didn't match its fingerprint, so it wasn't installed. Try again.")
            self.state.update(status="installing", progress=100)
            print(f"Installing update {rel['version']} from {exe}")
            s = self.app.settings
            if s.get("overlay", True):
                winutil.show_overlay(tr(s, "Updating ClipDrop to {v}...", v=rel["version"]), 4)
            # the new version says "updated" when it starts (see announce_update)
            (folder / "updating.txt").write_text(rel["version"], encoding="utf-8")
            if sys.platform == "win32":
                flags = 0x00000008 | 0x00000200 | 0x01000000  # detached, new group, break away from job
                args = [str(exe), "/S", "/UPDATE", f"/D={HERE}"]
                try:
                    subprocess.Popen(args, creationflags=flags, close_fds=True)
                except OSError:
                    subprocess.Popen(args, creationflags=0x00000008 | 0x00000200, close_fds=True)
            # the setup closes ClipDrop and starts the new version
        except Exception as e:
            print(f"Update failed: {e}")
            msg = str(e) if isinstance(e, RuntimeError) else "The update couldn't be downloaded. Check your internet and try again."
            self.state.update(status="error", error=msg)

    def announce_update(self):
        """Right after an update: show "ClipDrop updated to X" in game."""
        mark = CACHE_DIR / "update" / "updating.txt"
        try:
            ver = mark.read_text(encoding="utf-8").strip()
            mark.unlink()
        except OSError:
            return
        if ver == VERSION:
            print(f"Updated to {VERSION}")
            if self.app.settings.get("overlay", True):
                time.sleep(3)  # let the app finish starting
                winutil.show_overlay(tr(self.app.settings, "ClipDrop updated to {v}", v=VERSION), 4)

    def loop(self):
        """Check at start (after a minute) and then once a day."""
        self.announce_update()
        time.sleep(60)
        while True:
            if self.app.settings.get("update_check", True):
                st = self.check()
                if st["available"]:
                    if self.app.settings.get("update_auto"):
                        try:
                            self.install()
                        except Exception as e:
                            print(f"Auto-update: {e}")
                    elif self._told != st["version"]:
                        self._told = st["version"]
                        self.app.notify(tr(self.app.settings, "ClipDrop {v} is ready", v=st["version"]),
                                        tr(self.app.settings, "Open ClipDrop to see what's new and update."))
            time.sleep(24 * 3600)


# ================================================================ app

class App:
    def __init__(self):
        self.settings = load_settings()
        if sys.platform == "win32":   # the setup can tick "start with Windows" too; the Startup file decides
            self.settings["start_with_windows"] = autostart_on()
        self.ffmpeg, self.ffprobe = find_ffmpeg()
        if not self.ffmpeg:
            fatal("FFmpeg is missing. Run the ClipDrop setup again to fix it.")
        if not self.ffprobe:
            fatal("FFprobe is missing (it comes with FFmpeg). Run the ClipDrop setup again.")
        self.library = Library(self)
        self.deliveries = Deliveries()
        self.shared = Shared(self)
        self.updater = Updater(self)
        self.tray = None
        self.recorder = None
        self.hotkeys = None
        self._hotkey_lock = threading.Lock()
        self.last_clip = None
        self.public_url = ""
        self.public_host = ""
        self.public_base = ""
        self.game = None            # the game we're recording, if any
        self.game_seen_at = 0
        self.caps = None            # which video formats this PC supports
        self._rec_lock = threading.RLock()
        self._last_recorder = None
        self._wake = threading.Event()

    def notify(self, title, text):
        """A Windows notification from the tray icon."""
        print(f"{title}: {text}")
        try:
            if self.tray:
                self.tray.notify(text, title)
        except Exception:
            pass

    # --- formats

    def load_caps(self):
        self.caps = rec_mod.capabilities(self.ffmpeg)
        print("Formats this PC can record: " +
              ", ".join(f"{k.upper()} ({v['encoder']})" for k, v in self.caps.items() if v))

    def encoder_for(self, fmt):
        caps = self.caps or rec_mod.capabilities(self.ffmpeg)
        c = caps.get(fmt) or caps.get("h264")
        return c["encoder"] if c else "libx264"

    def buffer_seconds(self):
        return max(h["seconds"] for h in self.settings["hotkeys"])

    # --- recorder: decides when to record and what

    def _want_recording(self):
        s = self.settings
        if not s.get("recording_on", True):
            return False, None
        target = self.game if s.get("capture") == "window" else None
        if s.get("record_when") == "game":
            return bool(self.game), target
        return True, target

    def apply_recorder(self, force=False):
        """Start, stop or restart the recorder to match the settings and the current game."""
        with self._rec_lock:
            want, target = self._want_recording()
            r = self.recorder
            same_target = (r is not None and (r.target or {}).get("hwnd") == (target or {}).get("hwnd"))
            if want and r and same_target and not force:
                return
            if r:
                r.stop()
                self._last_recorder = r
                self.recorder = None
            if want:
                # keep the pieces the last recorder made, so changing a setting
                # (or the game window) doesn't throw away the replay buffer
                self.recorder = rec_mod.Recorder(self.settings, self.ffmpeg, self.buffer_seconds(), target,
                                                 keep_from=self._last_recorder)
                self.recorder.start()

    def watch_games(self):
        """Every 2 seconds: is a game open? Used for "only while gaming",
        "only the game window" and naming clips after the game."""
        while True:
            self._wake.wait(2)
            self._wake.clear()
            try:
                s = self.settings
                g = winutil.foreground_game(s.get("extra_games", []), s.get("not_games", []))
                now = time.time()
                if g:
                    if not self.game or self.game["hwnd"] != g["hwnd"]:
                        print(f"Game detected: {g['name']}")
                    self.game, self.game_seen_at = g, now
                elif self.game:
                    # the game is still open in the background (alt-tab): keep it
                    if winutil.window_alive(self.game["hwnd"]):
                        self.game_seen_at = now
                    elif now - self.game_seen_at > GAME_GONE_GRACE:
                        print(f"Game closed: {self.game['name']}")
                        self.game = None
                self.apply_recorder()
            except Exception as e:
                print(f"Game watcher: {e}")

    # --- hotkeys

    def start_hotkeys(self):
        # one at a time: the old hotkeys must let go of the keys before the new ones take them
        with self._hotkey_lock:
            if self.hotkeys:
                self.hotkeys.stop()
            items = [(h["keys"], (lambda secs=h["seconds"]: self.save_clip_from_hotkey(secs)))
                     for h in self.settings["hotkeys"]]
            hk = winutil.Hotkeys(items)
            hk.start()
            self.hotkeys = hk
        if winutil.IS_WIN:
            for h in self.settings["hotkeys"]:
                ok = self.hotkeys.ok.get(h["keys"])
                print(f"Hotkey {h['keys']} ({h['seconds']}s): " +
                      ("ready" if ok else self.hotkeys.errors.get(h["keys"], "problem")))

    # --- saving clips

    def save_clip(self, seconds=None, source="phone"):
        try:
            return self._save_clip(seconds, source)
        except Exception as e:
            print(f"Could not save clip ({source}): {e}")
            raise

    def _save_clip(self, seconds, source):
        if not self.recorder:
            if not self.settings.get("recording_on", True):
                # You asked for a clip, so you want recording: turn it back on
                # instead of leaving it off without you noticing.
                self.update_settings({"recording_on": True}, source=f"clip asked for from {source}")
                raise RuntimeError("Recording was off. It's on again now, so your next clip will work.")
            raise RuntimeError("Not recording right now: no game is open (Settings > When to record).")
        try:
            seconds = int(seconds or self.settings["hotkeys"][0]["seconds"])
        except (TypeError, ValueError):
            raise ValueError("Clip length must be a number of seconds")
        if not 5 <= seconds <= 600:
            raise ValueError("Clip length must be between 5 seconds and 10 minutes")
        game = None
        if self.settings.get("name_by_game"):
            game = (self.game or {}).get("name") or winutil.foreground_app()
        p = self.recorder.save_clip(seconds, game=game)
        self.library.ours.add(str(p))
        self.library.invalidate()
        self.last_clip = {"file": p.name, "at": time.time(), "seconds": seconds}
        return p

    def save_clip_from_hotkey(self, seconds=None):
        s = self.settings
        sound = s.get("save_sound", "click")
        # answer the key press right away; writing the file takes a few seconds
        if self.recorder:
            winutil.play_sound(sound)
            if s.get("overlay", True):
                winutil.show_overlay(tr(s, "Saving clip..."), 15)
        try:
            p = self.save_clip(seconds, source="hotkey")
            if s.get("overlay", True):
                winutil.show_overlay(tr(s, "Clip saved  •  {secs}s", secs=self.last_clip["seconds"]))
            return p
        except Exception as e:
            if sound != "off":
                winutil.play_sound("error")
            if s.get("overlay", True):
                msg = str(e) if str(e).startswith("Recording was off") else "Couldn't save the clip"
                winutil.show_overlay(tr(s, msg), 5, ok=False)

    # --- info for the page

    def status(self):
        r = self.recorder
        s = self.settings
        if r and r.running:
            state = "recording"
        elif not s.get("recording_on", True):
            state = "off"
        elif s.get("record_when") == "game" and not self.game:
            state = "waiting"   # waiting for a game
        else:
            state = "starting"
        hk = []
        for h in s["hotkeys"]:
            ok = bool(self.hotkeys and self.hotkeys.ok.get(h["keys"]))
            err = self.hotkeys.errors.get(h["keys"], "") if self.hotkeys else ""
            hk.append({"keys": h["keys"], "seconds": h["seconds"], "ok": ok, "error": err})
        return {
            "state": state,
            "recording": state == "recording",
            "encoder": r.encoder if r else None,
            "capture_mode": r.mode if r else None,
            "game": (self.game or {}).get("name"),
            "error": r.last_error if r else "",
            "hotkeys": hk,
            "last_clip": self.last_clip,
            "version": VERSION,
            "update": {k: self.updater.state[k] for k in ("available", "version", "status", "progress")},
        }

    def options(self):
        """Lists for the settings page: formats, screens, sound devices."""
        caps = self.caps or {}
        return {
            "formats": {k: ({"encoder": v["encoder"], "gpu": v["gpu"]} if v else None) for k, v in caps.items()},
            "formats_ready": self.caps is not None,
            "monitors": [{k: m[k] for k in ("index", "name", "width", "height")} for m in winutil.monitors()],
            "audio": rec_mod.audio_devices(),
            "game": (self.game or {}).get("name"),
            "phone_url": self.public_url,
            "defaults": DEFAULTS,
            "pc_name": self.shared.pc_name,
            "lang": ui_lang(self.settings),
            "on_windows": winutil.IS_WIN,
        }

    def update_settings(self, new, source="settings page"):
        old = dict(self.settings)
        self.settings.update(clean_settings(new, self.settings))
        save_settings(self.settings)
        if old.get("recording_on", True) != self.settings.get("recording_on", True):
            print(f"Recording turned {'on' if self.settings.get('recording_on', True) else 'OFF'} ({source})")
        # settings that change how we record (the save folder and hotkeys don't:
        # the recorder reads the folder when saving, and only needs a new length)
        rec_keys = ("fps", "bitrate", "height", "encoder", "monitor", "show_mouse", "video_format",
                    "game_audio", "microphone", "speaker_device", "mic_device", "game_volume",
                    "mic_volume", "recording_on", "record_when", "capture")
        changed_rec = any(old.get(k) != self.settings.get(k) for k in rec_keys)
        if old.get("hotkeys") != self.settings["hotkeys"]:
            self.start_hotkeys()
            if self.recorder:
                self.recorder.buffer_seconds = self.buffer_seconds()
        if old.get("start_with_windows") != self.settings["start_with_windows"]:
            set_autostart(self.settings["start_with_windows"])
        if changed_rec:
            threading.Thread(target=self.apply_recorder, kwargs={"force": True}, daemon=True).start()
        if old.get("language") != self.settings.get("language") and getattr(self, "tray", None):
            try:
                self.tray.update_menu()
            except Exception:
                pass
        self.library.invalidate()
        self.shared.invalidate()
        return self.settings


# ================================================================ web server

class QuietServer(ThreadingHTTPServer):
    """Doesn't fill the log when a phone closes the page mid-download."""

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionResetError, ConnectionAbortedError, BrokenPipeError,
                                          TimeoutError)):
            return
        super().handle_error(request, client_address)


class TimedLog:
    """Log file that puts the time at the start of every line."""

    def __init__(self, f):
        self.f = f
        self.at_start = True
        self.lock = threading.Lock()

    def write(self, text):
        if not text:
            return 0
        with self.lock:
            out = []
            for part in text.splitlines(keepends=True):
                if self.at_start and part.strip():
                    out.append(time.strftime("%m-%d %H:%M:%S "))
                out.append(part)
                self.at_start = part.endswith("\n")
            self.f.write("".join(out))
        return len(text)

    def flush(self):
        try:
            self.f.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self.f, name)


def make_handler(app):
    key = app.settings["phone_key"]

    class Handler(BaseHTTPRequestHandler):
        server_version = "ClipDrop/5"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            pass

        def _local(self):
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return self.client_address[0] in ("127.0.0.1", "::1") and host in ("127.0.0.1", "localhost", "::1", "")

        def _authed(self, q):
            if self._local() or q.get("k", [""])[0] == key:
                return True
            c = SimpleCookie(self.headers.get("Cookie", ""))
            return "cd_key" in c and c["cd_key"].value == key

        def _send(self, code, body, ctype="text/html; charset=utf-8", extra=None):
            data = body.encode("utf-8") if isinstance(body, str) else body
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            if "Cache-Control" not in (extra or {}):
                self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def _json(self, obj, code=200):
            self._send(code, json.dumps(obj), "application/json")

        def _lang(self):
            lang = app.settings.get("language", "auto")
            if lang in ("en", "ar"):
                return lang
            al = (self.headers.get("Accept-Language") or "").strip().lower()
            if al:
                return "ar" if al.startswith("ar") else "en"
            return ui_lang(app.settings)

        def _page(self, name, **subs):
            if self._lang() == "ar" and (WEB_DIR / name.replace(".html", ".ar.html")).exists():
                name = name.replace(".html", ".ar.html")
            page = (WEB_DIR / name).read_text(encoding="utf-8")
            lang = self._lang()
            subs.update(__LANG__=lang, __DIR__="rtl" if lang == "ar" else "ltr")
            for k, v in subs.items():
                page = page.replace(k, v)
            return self._send(200, page, extra={
                "Set-Cookie": f"cd_key={key}; Max-Age=31536000; Path=/; SameSite=Lax"})

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            parts = [p for p in url.path.split("/") if p]

            if url.path == "/pair":
                if not self._local():
                    return self._send(403, "Forbidden")
                page = PAIR_PAGE_AR if self._lang() == "ar" else PAIR_PAGE
                return self._send(200, page.replace("__URL__", html.escape(app.public_url)))
            if url.path == "/i18n.js":
                return self._send(200, (WEB_DIR / "i18n.js").read_bytes(), "text/javascript; charset=utf-8")
            if (len(parts) == 2 and parts[0] == "fonts" and re.fullmatch(r"[a-z0-9-]+\.(woff2|css)", parts[1])
                    and (WEB_DIR / "fonts" / parts[1]).is_file()):
                ctype = "font/woff2" if parts[1].endswith(".woff2") else "text/css; charset=utf-8"
                return self._send(200, (WEB_DIR / "fonts" / parts[1]).read_bytes(), ctype,
                                  {"Cache-Control": "max-age=604800"})
            if url.path in ("/icon.png", "/icon180.png"):
                return self._send(200, (WEB_DIR / url.path[1:]).read_bytes(), "image/png",
                                  {"Cache-Control": "max-age=86400"})
            if not self._authed(q):
                return self._send(403, LOCKED_PAGE_AR if self._lang() == "ar" else LOCKED_PAGE)

            if url.path == "/":
                return self._page("app.html")
            if url.path == "/help":
                return self._page("help.html", __PHONE_URL__=html.escape(app.public_url))
            if url.path == "/shortcut":
                link = f"{app.public_base}/api/inbox?k={key}&device=iphone"
                up = f"{app.public_base}/api/upload?k={key}&device=iPhone&kind=iphone"
                return self._page("shortcut.html", __INBOX__=html.escape(link), __UPLOAD__=html.escape(up))
            if url.path == "/api/clips":
                return self._json({"clips": app.library.scan(), "status": app.status(),
                                   "storage": app.library.storage()})
            if url.path == "/api/settings":
                s = dict(app.settings)
                s.pop("phone_key", None)
                return self._json(s)
            if url.path == "/api/options":
                return self._json(app.options())
            if url.path == "/api/inbox":
                # used by the iPhone Shortcut: links to clips this phone doesn't have yet
                device = (q.get("device", ["iphone"])[0] or "iphone")[:40]
                files = app.shared.for_photos()
                file_ids = {f["id"] for f in files}
                new = app.deliveries.pending(device, app.library.scan() + files)
                base = f"http://{self.headers.get('Host') or app.public_host}"
                dev = urllib.parse.quote(device)
                return self._json({
                    "count": len(new),
                    "clips": [f"{base}/{'fdl' if c['id'] in file_ids else 'dl'}/{c['id']}?k={key}&device={dev}"
                              for c in new],
                    "names": [c["name"] for c in new],
                })
            if url.path == "/api/update":
                return self._json(app.updater.state)
            if url.path == "/api/files":
                return self._json({"files": app.shared.scan(), "folder": str(app.shared.root()),
                                   "pc_name": app.shared.pc_name})
            if len(parts) == 2 and parts[0] in ("f", "fdl"):
                p = app.shared.path(parts[1])
                if not p:
                    return self._send(404, "Not found")
                device = q.get("device", [""])[0][:40] if parts[0] == "fdl" else ""
                inline_ok = file_type(p.suffix) in ("image", "video", "audio") and p.suffix.lower() != ".svg"
                done = self._stream(p, download=parts[0] == "fdl" or not inline_ok)
                if done and device:
                    it = app.shared.item(parts[1])
                    if it:
                        app.deliveries.mark(device, it)
                return
            if len(parts) == 2 and parts[0] == "ft":
                try:
                    t = app.shared.thumb(parts[1])
                except Exception:
                    t = None
                if not t:
                    return self._send(404, "No picture")
                return self._send(200, t.read_bytes(), "image/jpeg", {"Cache-Control": "max-age=3600"})
            if len(parts) == 2 and parts[0] in ("v", "dl"):
                p = app.library.path(parts[1])
                if not p:
                    return self._send(404, "Not found")
                device = q.get("device", [""])[0][:40] if parts[0] == "dl" else ""
                done = self._stream(p, download=parts[0] == "dl")
                if done and device:
                    clip = app.library.clip(parts[1])
                    if clip:
                        app.deliveries.mark(device, clip)
                return
            if len(parts) == 2 and parts[0] == "info":
                try:
                    return self._json(app.library.probe(parts[1]))
                except Exception as e:
                    return self._json({"error": str(e)}, 404)
            if len(parts) == 2 and parts[0] in ("strip", "t"):
                try:
                    t = (app.library.strip if parts[0] == "strip" else app.library.thumb)(parts[1])
                except Exception:
                    t = None
                if not t:
                    return self._send(404, "No picture")
                return self._send(200, t.read_bytes(), "image/jpeg", {"Cache-Control": "max-age=3600"})
            return self._send(404, "Not found")

        def _same_site(self):
            """A web page from another site can't send commands (it would come with its own Origin)."""
            origin = self.headers.get("Origin")
            if origin and origin != "null" and urllib.parse.urlparse(origin).netloc != (self.headers.get("Host") or ""):
                return False
            return True

        def do_POST(self):
            url = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(url.query)
            if not self._same_site():
                return self._json({"error": "Not allowed"}, 403)
            if not self._authed(q):
                return self._json({"error": "Not allowed"}, 403)
            if url.path == "/api/upload":
                return self._upload(q)
            try:
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json({"error": "Bad request"}, 400)
            lib = app.library
            try:
                if url.path == "/api/clip":
                    p = app.save_clip(body.get("seconds"))
                    return self._json({"ok": True, "file": p.name})
                if url.path == "/api/rename":
                    p = lib.rename(body["id"], body["name"])
                    return self._json({"ok": True, "name": p.stem})
                if url.path == "/api/delete":
                    lib.delete(body["id"])
                    return self._json({"ok": True})
                if url.path == "/api/favorite":
                    lib.set_fav(body["id"], body.get("on", True))
                    return self._json({"ok": True})
                if url.path == "/api/bulk":
                    ids, action = list(body.get("ids") or []), body.get("action")
                    clips = [c for c in (lib.clip(i) for i in ids) if c]
                    if action in ("fav", "unfav"):
                        for c in clips:
                            lib.set_fav(c["id"], action == "fav")
                    elif action == "delete":
                        for c in clips:
                            lib.delete(c["id"])
                    elif action == "send":
                        app.deliveries.resend(clips)
                    else:
                        raise ValueError("Unknown action")
                    return self._json({"ok": True, "count": len(clips)})
                if url.path == "/api/export":
                    p = lib.export(body["id"], body.get("keep"), body.get("game_vol", 1),
                                   body.get("voice_vol", 1), bool(body.get("share")),
                                   bool(body.get("replace")))
                    cid = hashlib.sha1(str(p).encode("utf-8")).hexdigest()[:16]
                    return self._json({"ok": True, "name": p.stem, "id": cid, "file": p.name})
                if url.path == "/api/settings":
                    s = dict(app.update_settings(body))
                    s.pop("phone_key", None)
                    return self._json({"ok": True, "settings": s})
                if url.path == "/api/test_sound":
                    name = str(body.get("name", ""))
                    if name not in winutil.SOUNDS:
                        raise ValueError("Unknown sound")
                    winutil.play_sound(name)
                    return self._json({"ok": True})
                if url.path == "/api/update/check":
                    return self._json(app.updater.check())
                if url.path == "/api/update/install":
                    app.updater.install()
                    return self._json({"ok": True})
                if url.path == "/api/files/rename":
                    p = app.shared.rename(body["id"], body["name"])
                    return self._json({"ok": True, "name": p.stem})
                if url.path == "/api/files/delete":
                    ids = body.get("ids") or [body.get("id")]
                    for i in ids:
                        app.shared.delete(i)
                    return self._json({"ok": True, "count": len(ids)})
                if url.path == "/api/files/resend":
                    items = [f for f in (app.shared.item(i) for i in body.get("ids") or []) if f]
                    app.deliveries.resend(items)
                    return self._json({"ok": True, "count": len(items)})
                if url.path == "/api/share_paths" and self._local():
                    done = app.shared.add_paths(body.get("paths") or [])
                    return self._json({"ok": True, "count": len(done)})
                if url.path == "/api/files/open" and self._local():
                    root = app.shared.root()
                    root.mkdir(parents=True, exist_ok=True)
                    p = app.shared.path(body["id"]) if body.get("id") else None
                    if p and sys.platform == "win32":
                        subprocess.Popen(["explorer", "/select,", str(p)])
                    elif hasattr(os, "startfile"):
                        os.startfile(root)
                    return self._json({"ok": True})
                if url.path == "/api/open_folder" and self._local():
                    folder = expand(app.settings["save_folder"])
                    if body.get("id"):
                        p = lib.path(body["id"])
                        if p and sys.platform == "win32":
                            subprocess.Popen(["explorer", "/select,", str(p)])
                            return self._json({"ok": True})
                    if hasattr(os, "startfile"):
                        os.startfile(folder)
                    return self._json({"ok": True})
            except (ValueError, KeyError, RuntimeError, OSError) as e:
                return self._json({"error": str(e)}, 400)
            return self._json({"error": "Not found"}, 404)

        def _upload(self, q):
            """A file sent from a phone or the PC page. The body is the file itself."""
            name = q.get("name", [""])[0] or urllib.parse.unquote(self.headers.get("X-File-Name") or "")
            if not name:
                ext = mimetypes.guess_extension((self.headers.get("Content-Type") or "").split(";")[0].strip()) or ""
                name = time.strftime("File %Y-%m-%d %H-%M-%S") + ext
            if self._local():
                origin, device, kind = "pc", app.shared.pc_name, "pc"
            else:
                origin = "pc" if q.get("from", [""])[0] == "pc" else "phone"
                device = (q.get("device", [""])[0] or "Phone").strip()[:40]
                kind = (q.get("kind", ["phone"])[0] or "phone")[:12]
            try:
                if "chunked" in (self.headers.get("Transfer-Encoding") or "").lower():
                    p = app.shared.receive(self._chunked_reader(), None, name, origin, device, kind)
                else:
                    length = int(self.headers.get("Content-Length") or 0)
                    p = app.shared.receive(self.rfile.read, length, name, origin, device, kind)
            except (ValueError, OSError) as e:
                self.close_connection = True
                return self._json({"error": str(e)}, 400)
            return self._json({"ok": True, "file": p.name})

        def _chunked_reader(self):
            buf = bytearray()
            done = False

            def read(n):
                nonlocal done
                while len(buf) < n and not done:
                    size = int(self.rfile.readline().split(b";")[0].strip() or b"0", 16)
                    if size == 0:
                        while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                            pass
                        done = True
                        break
                    buf.extend(self.rfile.read(size))
                    self.rfile.readline()
                out = bytes(buf[:n])
                del buf[:n]
                return out
            return read

        def _stream(self, path, download=False):
            """Send a video with Range support (iPhone needs this to play video)."""
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            rng = self.headers.get("Range")
            if rng and rng.startswith("bytes="):
                s, _, e = rng[6:].split(",")[0].partition("-")
                try:
                    if s:
                        start, end = int(s), (int(e) if e else size - 1)
                    else:
                        start = max(0, size - int(e))
                    end = min(end, size - 1)
                    if start > end:
                        raise ValueError
                    status = 206
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return False
            length = end - start + 1
            self.send_response(status)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-cache")
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            if download:
                self.send_header("Content-Disposition",
                                 f"attachment; filename*=UTF-8''{urllib.parse.quote(path.name)}")
            self.end_headers()
            if self.command == "HEAD":
                return False
            left = length
            try:
                with open(path, "rb") as f:
                    f.seek(start)
                    while left > 0:
                        chunk = f.read(min(1024 * 1024, left))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        left -= len(chunk)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                self.close_connection = True
                return False
            return left == 0 and end == size - 1  # reached the end of the file

    return Handler


LOCKED_PAGE = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href="/fonts/fonts.css"><body style="background:#0d0c0a;color:#eee7da;font-family:'IBM Plex Sans','IBM Plex Sans Arabic',system-ui;padding:40px;text-align:center">
<h2>ClipDrop</h2><p>Scan the QR code on your PC to connect.<br>(ClipDrop icon by the clock &rarr; Connect iPhone)</p></body>"""

LOCKED_PAGE_AR = """<!doctype html><html dir=rtl lang=ar><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<link rel=stylesheet href="/fonts/fonts.css"><body style="background:#0d0c0a;color:#eee7da;font-family:'IBM Plex Sans','IBM Plex Sans Arabic',system-ui;padding:40px;text-align:center">
<h2>ClipDrop</h2><p>امسح رمز QR الظاهر على الكمبيوتر للربط.<br>(أيقونة ClipDrop بجانب الساعة &larr; ربط الجوال)</p></body></html>"""

PAIR_PAGE = """<!doctype html><html><head><meta charset=utf-8><title>ClipDrop - connect your phone</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<link rel=stylesheet href="/fonts/fonts.css"><style>body{background:#0d0c0a;color:#eee7da;font-family:'IBM Plex Sans',system-ui,Segoe UI,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0}
.box{text-align:center;max-width:460px;padding:20px}#qr{background:#fff;padding:16px;border-radius:4px;display:inline-block;margin:20px 0}
code{background:#15130f;padding:6px 10px;border-radius:3px;font-size:15px;word-break:break-all}p,li{color:#9a9184;line-height:1.5}ol{text-align:left}
a{color:#f0a53a}</style></head>
<body><div class=box><h1>Connect your phone</h1>
<div id=qr></div><p>Or type this into Safari:</p><code>__URL__</code>
<ol><li>Your phone and PC must be on the same Wi-Fi.</li>
<li>Open the camera and scan the code, then tap the link.</li>
<li>In Safari tap Share &rarr; <b>Add to Home Screen</b> so ClipDrop opens like an app.</li>
<li>Want clips to go straight into Photos? On your phone open ClipDrop &rarr; settings &rarr; <b>Phone</b> &rarr; <b>Auto-send to Photos</b>.</li></ol>
<p><a href="/help">How to use ClipDrop</a></p></div>
<script>try{new QRCode(document.getElementById('qr'),{text:"__URL__",width:240,height:240})}catch(e){document.getElementById('qr').remove()}</script>
</body></html>"""


PAIR_PAGE_AR = """<!doctype html><html dir=rtl lang=ar><head><meta charset=utf-8><title>ClipDrop - ربط الجوال</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
<link rel=stylesheet href="/fonts/fonts.css"><style>body{background:#0d0c0a;color:#eee7da;font-family:'IBM Plex Sans','IBM Plex Sans Arabic',system-ui,Segoe UI,Tahoma,sans-serif;display:grid;place-items:center;min-height:100vh;margin:0}
.box{text-align:center;max-width:460px;padding:20px}#qr{background:#fff;padding:16px;border-radius:4px;display:inline-block;margin:20px 0}
code{background:#15130f;padding:6px 10px;border-radius:3px;font-size:15px;word-break:break-all;direction:ltr;display:inline-block}p,li{color:#9a9184;line-height:1.7}ol{text-align:right}
a{color:#f0a53a}</style></head>
<body><div class=box><h1>اربط جوالك</h1>
<div id=qr></div><p>أو اكتب هذا الرابط في Safari:</p><code>__URL__</code>
<ol><li>لازم يكون الجوال والكمبيوتر على نفس شبكة الواي فاي.</li>
<li>افتح الكاميرا وامسح الرمز، ثم اضغط على الرابط.</li>
<li>في Safari اضغط مشاركة &larr; <b>إضافة إلى الشاشة الرئيسية</b> عشان يفتح ClipDrop مثل التطبيق.</li>
<li>تبي المقاطع تنزل في الصور تلقائيًا؟ في الجوال افتح ClipDrop &larr; الإعدادات &larr; <b>الجوال</b> &larr; <b>الإرسال التلقائي للصور</b>.</li></ol>
<p><a href="/help">طريقة استخدام ClipDrop</a></p></div>
<script>try{new QRCode(document.getElementById('qr'),{text:"__URL__",width:240,height:240})}catch(e){document.getElementById('qr').remove()}</script>
</body></html>"""


# ================================================================ tray icon

def run_tray(app, server):
    try:
        import pystray
        from PIL import Image
    except Exception:
        print("(No tray icon: pystray/pillow not installed. Close this window to quit.)")
        server.serve_forever()
        return

    icon_img = Image.open(WEB_DIR / "icon.png")
    port = app.settings["port"]
    local = f"http://127.0.0.1:{port}"

    def open_folder(*_):
        folder = expand(app.settings["save_folder"])
        folder.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(folder)

    def quit_app(icon, *_):
        icon.stop()
        if app.recorder:
            app.recorder.stop()
        server.shutdown()

    def first_hotkey_label(*_):
        h = app.settings["hotkeys"][0]
        return tr(app.settings, "Save clip now ({keys}, {secs}s)", keys=h["keys"], secs=h["seconds"])

    def T(text):
        return lambda *_: tr(app.settings, text)

    def update_label(*_):
        st = app.updater.state
        if st["available"]:
            return tr(app.settings, "Install update {v}", v=st["version"])
        return tr(app.settings, "Check for updates")

    def update_click(*_):
        if app.updater.state["available"]:
            winutil.open_app_window(local + "/#update")
        else:
            def run():
                st = app.updater.check()
                if st["available"]:
                    winutil.open_app_window(local + "/#update")
                else:
                    winutil.show_overlay(f"ClipDrop {VERSION} ✓", 2.5)
            threading.Thread(target=run, daemon=True).start()

    def open_shared(*_):
        folder = app.shared.root()
        folder.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(folder)

    def toggle_recording(*_):
        on = not app.settings.get("recording_on", True)
        app.update_settings({"recording_on": on}, source="tray menu")
        if on:
            app.notify("ClipDrop", tr(app.settings, "Recording is on again"))
        else:
            app.notify(tr(app.settings, "Recording is off"),
                       tr(app.settings, "Press your clip key or open ClipDrop to turn it back on."))

    menu = pystray.Menu(
        pystray.MenuItem(T("Open ClipDrop"), lambda *_: winutil.open_app_window(local + "/"), default=True),
        pystray.MenuItem(first_hotkey_label, lambda *_: app.save_clip_from_hotkey()),
        pystray.MenuItem(T("Send files to phone"), lambda *_: winutil.open_app_window(local + "/#files")),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(T("Connect phone (QR code)"), lambda *_: webbrowser.open(local + "/pair")),
        pystray.MenuItem(T("Open clips folder"), open_folder),
        pystray.MenuItem(T("Open shared files folder"), open_shared),
        pystray.MenuItem(T("Help"), lambda *_: winutil.open_app_window(local + "/help")),
        pystray.MenuItem(update_label, update_click),
        pystray.Menu.SEPARATOR,
        # kept away from "Save clip now", so a slip of the mouse can't turn recording off
        pystray.MenuItem(T("Recording on"), toggle_recording,
                         checked=lambda *_: app.settings.get("recording_on", True)),
        pystray.MenuItem(T("Quit ClipDrop"), quit_app),
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    app.tray = pystray.Icon("ClipDrop", icon_img, "ClipDrop", menu)
    app.tray.run()


# ================================================================ main

def send_from_explorer(paths):
    """Explorer right-click > Send to > ClipDrop: hand the files to the running app."""
    import urllib.request
    settings = dict(DEFAULTS)
    try:
        settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except Exception:
        pass
    url = f"http://127.0.0.1:{int(settings['port'])}/api/share_paths"
    body = json.dumps({"paths": [str(Path(p).resolve()) for p in paths]}).encode("utf-8")
    started = False
    for _ in range(40):
        try:
            req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=600).read()
            return
        except Exception:
            if not started:   # ClipDrop isn't running: start it, then try again
                started = True
                pyw = Path(sys.executable).with_name("pythonw.exe")
                exe = str(pyw) if pyw.exists() else sys.executable
                subprocess.Popen([exe, str(HERE / "clipdrop.py")], cwd=str(HERE), creationflags=NO_WINDOW)
            time.sleep(1)
    fatal(tr(settings, "ClipDrop isn't running and couldn't be started."))


def main():
    if "--send" in sys.argv:
        files = sys.argv[sys.argv.index("--send") + 1:]
        if files:
            send_from_explorer(files)
        return
    # Started without a console window (ClipDrop.vbs / pythonw): write messages to a log file
    if sys.stdout is None or sys.stderr is None or "pythonw" in Path(sys.executable).name.lower():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        log_path = CACHE_DIR / "clipdrop.log"
        try:  # keep the log small: start a new one past 5 MB, keep one old one
            if log_path.stat().st_size > LOG_MAX_BYTES:
                log_path.replace(CACHE_DIR / "clipdrop.old.log")
        except OSError:
            pass
        logf = TimedLog(open(log_path, "a", encoding="utf-8", buffering=1))
        sys.stdout = sys.stderr = logf
        print(f"\n--- ClipDrop {VERSION} started {time.ctime()} ---")
    app = App()
    port = int(app.settings["port"])
    app.public_host = f"{lan_ip()}:{port}"
    app.public_base = f"http://{app.public_host}"
    app.public_url = f"{app.public_base}/?k={app.settings['phone_key']}"
    try:
        server = QuietServer(("0.0.0.0", port), make_handler(app))
    except OSError as e:
        fatal(f"ClipDrop is probably already running (look for its icon by the clock).\n\n"
              f"Port {port} is busy: {e}")
    server.daemon_threads = True

    expand(app.settings["save_folder"]).mkdir(parents=True, exist_ok=True)
    try:
        app.shared.root().mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"Can't make the shared files folder: {e}")
    app.load_caps()   # find out which formats the graphics card can record (takes a few seconds)
    app.start_hotkeys()
    app.apply_recorder(force=True)
    threading.Thread(target=app.watch_games, daemon=True).start()
    threading.Thread(target=app.updater.loop, daemon=True).start()

    print("=" * 60)
    print(f" ClipDrop {VERSION} is running")
    for h in app.settings["hotkeys"]:
        print(f"   {h['keys']:<12} saves the last {h['seconds']} seconds")
    print(f"   Clips go to:  {expand(app.settings['save_folder'])}")
    print(f"   Phone link:   {app.public_url}")
    print(" If Windows asks about the firewall, allow PRIVATE networks.")
    print("=" * 60)

    if not app.settings.get("recording_on", True):
        print("Recording is OFF (turned off earlier). Press the clip key or use the menu to turn it on.")
        threading.Timer(8.0, lambda: app.settings.get("recording_on", True) or app.notify(
            tr(app.settings, "Recording is off"),
            tr(app.settings, "Press your clip key or open ClipDrop to turn it back on."))).start()

    first_run = not (CACHE_DIR / "paired").exists()
    if first_run or "--pair" in sys.argv:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / "paired").touch()
        threading.Timer(1.0, lambda: webbrowser.open(f"http://127.0.0.1:{port}/pair")).start()

    try:
        if "--no-tray" in sys.argv:
            server.serve_forever()
        else:
            run_tray(app, server)
    except KeyboardInterrupt:
        pass
    finally:
        if app.recorder:
            app.recorder.stop()
        if app.hotkeys:
            app.hotkeys.stop()


if __name__ == "__main__":
    main()

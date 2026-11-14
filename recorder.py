"""
ClipDrop recorder: a replay buffer built on FFmpeg.

FFmpeg records non-stop into short 2-second pieces in a temp folder. Old
pieces are deleted, so only the last N seconds are kept. When you press a
hotkey (or tap "Clip it" on your phone), the newest pieces are joined into one
MP4 without re-encoding, so saving is instant.

What to record:
  screen  - a whole monitor, via FFmpeg "ddagrab" (Desktop Duplication),
            falls back to "gdigrab".
  window  - only the game window. Tries Windows Graphics Capture
            ("gfxcapture", FFmpeg 8+), else crops the screen to the window.

Video format: H.264, HEVC or AV1, using your graphics card when it can
(NVIDIA NVENC, AMD AMF, Intel Quick Sync), else the CPU.

Sound: game/desktop sound via the "soundcard" package (WASAPI loopback), and
optionally the mic. With the mic on, clips get 3 audio tracks:
  1 = game + voice mixed (what phones play), 2 = game only, 3 = voice only.
"""

import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path

SEGMENT_SECONDS = 2
SAMPLE_RATE = 48000
CHANNELS = 2
AUDIO_CHUNK = 960  # 20 ms at 48 kHz

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

try:
    import numpy as np
    import soundcard as sc
except Exception:  # optional
    np = None
    sc = None

# Encoders to try for each format, best first. True = uses the graphics card.
ENCODERS = {
    "h264": [("h264_nvenc", True), ("h264_amf", True), ("h264_qsv", True), ("libx264", False)],
    "hevc": [("hevc_nvenc", True), ("hevc_amf", True), ("hevc_qsv", True), ("libx265", False)],
    "av1": [("av1_nvenc", True), ("av1_amf", True), ("av1_qsv", True), ("libsvtav1", False)],
}


def log(msg):
    print(f"[recorder] {msg}", flush=True)


def _encoder_works(ffmpeg, enc):
    try:
        r = subprocess.run(
            [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
             "color=black:s=1280x720:r=30", "-frames:v", "5", "-pix_fmt", "yuv420p",
             "-c:v", enc, "-f", "null", "-"],
            capture_output=True, timeout=30, creationflags=NO_WINDOW)
        return r.returncode == 0
    except Exception:
        return False


_caps_cache = {}
_caps_lock = threading.Lock()


def capabilities(ffmpeg):
    """Which formats this PC can record, and with which encoder.
    {'h264': {'encoder': 'h264_nvenc', 'gpu': True}, 'av1': None, ...}"""
    with _caps_lock:
        if ffmpeg in _caps_cache:
            return _caps_cache[ffmpeg]
        caps = {}
        for fmt, options in ENCODERS.items():
            caps[fmt] = None
            for enc, gpu in options:
                if _encoder_works(ffmpeg, enc):
                    caps[fmt] = {"encoder": enc, "gpu": gpu}
                    break
        _caps_cache[ffmpeg] = caps
        return caps


def pick_encoder(ffmpeg, fmt="h264", wanted="auto"):
    if wanted and wanted != "auto":
        return wanted
    cap = capabilities(ffmpeg).get(fmt)
    if cap:
        return cap["encoder"]
    log(f"This PC can't record {fmt.upper()}, using H.264 instead")
    cap = capabilities(ffmpeg).get("h264")
    return cap["encoder"] if cap else "libx264"


def codec_of(encoder):
    if encoder.startswith(("hevc", "libx265")):
        return "hevc"
    if encoder.startswith(("av1", "libsvtav1", "libaom")):
        return "av1"
    return "h264"


def encoder_args(enc, bitrate, fps, keyframe_seconds=SEGMENT_SECONDS):
    gop = str(max(1, int(float(fps) * keyframe_seconds)))  # a keyframe every piece, so cuts are clean
    rate = ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", bitrate]
    common = ["-g", gop, "-pix_fmt", "yuv420p"]
    if enc.endswith("_nvenc"):
        return ["-c:v", enc, "-preset", "p4", "-tune", "ll", "-rc", "cbr", "-forced-idr", "1"] + rate + common
    if enc.endswith("_amf"):
        return ["-c:v", enc, "-quality", "speed", "-rc", "cbr"] + rate + common
    if enc.endswith("_qsv"):
        return ["-c:v", enc, "-preset", "faster"] + rate + common
    if enc == "libx265":
        return ["-c:v", enc, "-preset", "ultrafast", "-tune", "zerolatency",
                "-x265-params", "log-level=error"] + rate + common
    if enc == "libsvtav1":
        return ["-c:v", enc, "-preset", "11", "-b:v", bitrate] + common
    return ["-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency"] + rate + common


def mp4_tag(encoder):
    """iPhones only play HEVC in MP4 when it's tagged 'hvc1'."""
    return ["-tag:v", "hvc1"] if codec_of(encoder) == "hevc" else []


# ---------------------------------------------------------------- sound devices

def audio_devices():
    """Speakers (for game sound) and microphones you can pick in Settings."""
    if sc is None:
        return {"speakers": [], "mics": [], "available": False}
    out = {"speakers": [], "mics": [], "available": True}
    try:
        default_spk = sc.default_speaker().name
        out["speakers"] = [{"name": s.name, "default": s.name == default_spk} for s in sc.all_speakers()]
    except Exception:
        pass
    try:
        default_mic = sc.default_microphone().name
        out["mics"] = [{"name": m.name, "default": m.name == default_mic}
                       for m in sc.all_microphones(include_loopback=False)]
    except Exception:
        pass
    return out


def _find_speaker(name):
    if name:
        for s in sc.all_speakers():
            if s.name == name:
                return sc.get_microphone(s.id, include_loopback=True)
        log(f"Speaker '{name}' not found, using the default one")
    return sc.get_microphone(str(sc.default_speaker().name), include_loopback=True)


def _find_mic(name):
    if name:
        for m in sc.all_microphones(include_loopback=False):
            if m.name == name:
                return m
        log(f"Microphone '{name}' not found, using the default one")
    return sc.default_microphone()


class AudioPump:
    """Feeds a steady stream of PCM into FFmpeg, 20 ms at a time.

    Windows loopback goes quiet (sends nothing) when no sound is playing, so
    we pace by the clock and fill gaps with silence. That keeps the sound in
    sync with the video.

    With the mic on, we send 4 channels: game L/R then mic L/R. FFmpeg splits
    them into separate tracks so the voice can be turned down later.
    """

    def __init__(self, sink, s):
        self.sink = sink
        self.want_mic = bool(s.get("microphone"))
        self.channels = 4 if self.want_mic else 2
        self.game_vol = max(0.0, float(s.get("game_volume", 100)) / 100)
        self.mic_vol = max(0.0, float(s.get("mic_volume", 100)) / 100)
        self.speaker_name = s.get("speaker_device") or ""
        self.mic_name = s.get("mic_device") or ""
        self.game_q = queue.Queue(maxsize=50) if (s.get("game_audio", True) and sc is not None) else None
        self.mic_q = queue.Queue(maxsize=50) if (self.want_mic and sc is not None) else None
        self.stop_evt = threading.Event()

    def start(self):
        if sc is None:
            log("No 'soundcard' package: clips will have no sound.")
        if self.game_q is not None:
            self._add_source(self.game_q, lambda: _find_speaker(self.speaker_name), "game sound")
        if self.mic_q is not None:
            self._add_source(self.mic_q, lambda: _find_mic(self.mic_name), "microphone")
        threading.Thread(target=self._writer, daemon=True).start()

    def _add_source(self, q, get_dev, label):
        def run():
            try:
                if sys.platform == "win32":
                    import ctypes
                    ctypes.windll.ole32.CoInitializeEx(None, 0)
                dev = get_dev()
                log(f"Recording {label}: {dev.name}")
                with dev.recorder(samplerate=SAMPLE_RATE, channels=CHANNELS, blocksize=AUDIO_CHUNK) as rec:
                    while not self.stop_evt.is_set():
                        data = rec.record(numframes=AUDIO_CHUNK)
                        try:
                            q.put_nowait(data)
                        except queue.Full:
                            pass
            except Exception as e:
                log(f"{label} unavailable: {e}")

        threading.Thread(target=run, daemon=True).start()

    def _take(self, q, n):
        """Pull exactly n stereo frames from a source queue, padding with silence."""
        if q is None:
            return np.zeros((n, CHANNELS), dtype=np.float32)
        parts, have = [], 0
        buf = getattr(q, "_left", None)
        if buf is not None:
            parts.append(buf)
            have += len(buf)
            q._left = None
        while have < n:
            try:
                d = q.get_nowait()
            except queue.Empty:
                break
            parts.append(d)
            have += len(d)
        if not parts:
            return np.zeros((n, CHANNELS), dtype=np.float32)
        a = np.concatenate(parts)
        if a.ndim == 1:
            a = a[:, None]
        if a.shape[1] != CHANNELS:
            a = np.repeat(a[:, :1], CHANNELS, axis=1)
        if len(a) > n:
            q._left = a[n:]
            a = a[:n]
        elif len(a) < n:
            a = np.concatenate([a, np.zeros((n - len(a), CHANNELS), dtype=np.float32)])
        while q.qsize() > 10:  # a source ran ahead: drop to keep latency low
            try:
                q.get_nowait()
            except queue.Empty:
                break
        return a

    def _writer(self):
        silence = b"\x00" * (AUDIO_CHUNK * self.channels * 2)
        step = AUDIO_CHUNK / SAMPLE_RATE
        nxt = time.perf_counter()
        while not self.stop_evt.is_set():
            if np is not None and (self.game_q is not None or self.mic_q is not None):
                game = self._take(self.game_q, AUDIO_CHUNK) * self.game_vol
                if self.want_mic:
                    frame = np.concatenate([game, self._take(self.mic_q, AUDIO_CHUNK) * self.mic_vol], axis=1)
                else:
                    frame = game
                pcm = (np.clip(frame, -1, 1) * 32767).astype("<i2").tobytes()
            else:
                pcm = silence
            try:
                self.sink.write(pcm)
            except (BrokenPipeError, OSError, ValueError):
                return
            nxt += step
            delay = nxt - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
            elif delay < -0.5:  # fell far behind (PC was busy): resync
                nxt = time.perf_counter()

    def stop(self):
        self.stop_evt.set()


# ---------------------------------------------------------------- recorder

class Recorder:
    def __init__(self, settings, ffmpeg, buffer_seconds=30, target=None):
        """target: the game window to record (from winutil.foreground_game),
        used when settings['capture'] == 'window'."""
        self.s = settings
        self.ffmpeg = ffmpeg
        self.buffer_seconds = int(buffer_seconds)
        self.target = target
        self.buf_dir = Path(tempfile.gettempdir()) / "ClipDrop" / "buffer"
        self.out_dir = Path(os.path.expandvars(os.path.expanduser(settings["save_folder"])))
        self.proc = None
        self.audio = None
        self.encoder = None
        self.mode = None
        self.running = False
        self.last_error = ""
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.seg_ext = "mkv" if settings.get("video_format") == "av1" else "ts"

    # ---------- capture

    def _video_input(self, mode):
        fps = str(self.s["fps"])
        mouse = int(bool(self.s.get("show_mouse")))
        if mode == "test":  # for testing without a Windows desktop
            return ["-re", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}"]
        mon = int(self.s.get("monitor", 0))
        t = self.target
        if mode == "gfxcapture":
            return ["-f", "lavfi", "-i",
                    f"gfxcapture=hwnd={t['hwnd']}:max_framerate={fps}:capture_cursor={mouse},hwdownload,format=bgra"]
        if mode == "crop":
            x0, y0, x1, y1 = t["rect"]
            w, h = (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2
            ox, oy = x0 - t["monitor_left"], y0 - t["monitor_top"]
            return ["-f", "lavfi", "-i",
                    f"ddagrab=output_idx={t['monitor']}:framerate={fps}:draw_mouse={mouse}"
                    f":video_size={w}x{h}:offset_x={ox}:offset_y={oy},hwdownload,format=bgra"]
        if mode == "ddagrab":
            return ["-f", "lavfi", "-i",
                    f"ddagrab=output_idx={mon}:framerate={fps}:draw_mouse={mouse},hwdownload,format=bgra"]
        return ["-f", "gdigrab", "-framerate", fps, "-draw_mouse", str(mouse), "-i", "desktop"]

    def _scale_filter(self):
        h = int(self.s.get("height") or 0)
        return f"scale=-2:{h}" if h else "scale=trunc(iw/2)*2:trunc(ih/2)*2"

    def _modes(self):
        if self.s.get("test_source"):
            return ["test"]
        if self.s.get("capture") == "window" and self.target:
            return ["gfxcapture", "crop", "ddagrab", "gdigrab"]
        return ["ddagrab", "gdigrab"]

    def _launch(self, mode):
        pattern = str(self.buf_dir / f"seg_{int(time.time())}_%06d.{self.seg_ext}")
        mic = bool(self.s.get("microphone"))
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
               "-thread_queue_size", "1024"] + self._video_input(mode)
        cmd += ["-thread_queue_size", "1024", "-f", "s16le", "-ar", str(SAMPLE_RATE),
                "-ac", "4" if mic else "2", "-i", "pipe:0"]
        vf = self._scale_filter()
        if mic:
            # track 1: game + voice mixed (what your phone plays)
            # track 2: game only, track 3: voice only (for the volume sliders)
            fc = (f"[0:v]{vf}[v];[1:a]asplit=3[x][y][z];"
                  "[x]pan=stereo|c0=c0+c2|c1=c1+c3[mix];"
                  "[y]pan=stereo|c0=c0|c1=c1[game];"
                  "[z]pan=stereo|c0=c2|c1=c3[voice]")
            cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[mix]", "-map", "[game]", "-map", "[voice]"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a", "-vf", vf]
        cmd += encoder_args(self.encoder, self.s["bitrate"], self.s["fps"])
        cmd += ["-c:a", "aac", "-b:a", "192k",
                "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
                "-segment_format", "matroska" if self.seg_ext == "mkv" else "mpegts",
                "-reset_timestamps", "1", pattern]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=NO_WINDOW)
        self.audio = AudioPump(self.proc.stdin, self.s)
        self.audio.start()

    def start(self):
        shutil.rmtree(self.buf_dir, ignore_errors=True)
        self.buf_dir.mkdir(parents=True, exist_ok=True)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.encoder = pick_encoder(self.ffmpeg, self.s.get("video_format", "h264"), self.s.get("encoder", "auto"))
        log(f"Encoder: {self.encoder}")
        threading.Thread(target=self._supervise, daemon=True).start()

    def _supervise(self):
        modes = self._modes()
        mi = 0
        while not self._stop.is_set():
            mode = modes[min(mi, len(modes) - 1)]
            self.mode = mode
            what = f"window of {self.target['name']}" if mode in ("gfxcapture", "crop") else "screen"
            log(f"Recording {what} ({mode}, {self.s['fps']} fps, {self.s['bitrate']}), "
                f"keeping last {self.buffer_seconds}s")
            self._launch(mode)
            started = time.time()
            self.running = True
            while self.proc.poll() is None and not self._stop.is_set():
                self._cleanup()
                time.sleep(1)
            self.running = False
            if self.audio:
                self.audio.stop()
            if self._stop.is_set():
                break
            err = (self.proc.stderr.read() or b"").decode("utf-8", "replace").strip()
            self.last_error = err[-500:]
            log(f"FFmpeg stopped ({mode}): {self.last_error or 'no message'}")
            if time.time() - started < 10 and mi < len(modes) - 1:
                mi += 1  # failed quickly: try the next capture method
            time.sleep(2)

    def _segments(self):
        return sorted(self.buf_dir.glob(f"seg_*.{self.seg_ext}"), key=lambda p: (p.stat().st_mtime, p.name))

    def _cleanup(self):
        segs = self._segments()
        keep = self.buffer_seconds // SEGMENT_SECONDS + 3
        for p in segs[:-keep]:
            try:
                p.unlink()
            except OSError:
                pass  # still open, try next time

    # ---------- saving

    def save_clip(self, seconds=30, game=None):
        """Join the last `seconds` of the buffer into an MP4. Returns its path.
        Clips go into a subfolder named after the game, if we know it."""
        seconds = int(seconds)
        with self._lock:
            # wait for the piece being recorded right now to finish, so the
            # clip ends at the moment you pressed the key
            first = self._segments()
            deadline = time.time() + SEGMENT_SECONDS + 1.5
            while time.time() < deadline:
                now = self._segments()
                if now and first and now[-1] != first[-1]:
                    break
                time.sleep(0.1)
            segs = self._segments()[:-1]  # newest one is still being written
            if not segs:
                raise RuntimeError("Nothing recorded yet. Wait a few seconds and try again.")
            n = max(1, -(-seconds // SEGMENT_SECONDS))
            segs = segs[-n:]
            stamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            folder = self.out_dir / game if game else self.out_dir
            folder.mkdir(parents=True, exist_ok=True)
            out = folder / f"{game or 'Clip'} {stamp}.mp4"
            if out.exists():
                out = folder / f"{game or 'Clip'} {stamp} ({seconds}s).mp4"
            lst = self.buf_dir / "concat.txt"
            lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in segs), encoding="utf-8")
            r = subprocess.run(
                [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
                 "-i", str(lst), "-map", "0", "-c", "copy"] + mp4_tag(self.encoder) +
                ["-movflags", "+faststart", str(out)],
                capture_output=True, timeout=120, creationflags=NO_WINDOW)
            if r.returncode != 0 or not out.exists():
                raise RuntimeError(r.stderr.decode("utf-8", "replace")[-400:] or "FFmpeg failed")
            log(f"Saved {out.name}")
            return out

    def stop(self):
        self._stop.set()
        if self.audio:
            self.audio.stop()
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
        self.running = False

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
# No new 2-second piece for this long means the picture stopped coming in
# (the sound alone can keep a piece growing), so FFmpeg gets restarted.
STALL_SECONDS = 10
# Pieces further apart than this aren't one stretch of recording (the
# recorder was off in between), so a clip never joins across that gap.
MAX_JOIN_GAP = SEGMENT_SECONDS + 15

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
# The recorder gets a bit more CPU time than normal apps, so a busy game
# doesn't starve it of time to grab frames.
ABOVE_NORMAL = getattr(subprocess, "ABOVE_NORMAL_PRIORITY_CLASS", 0)

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


# ---------------------------------------------------------------- FFmpeg housekeeping

_job = None


def _kill_with_us(proc):
    """Windows: put FFmpeg in a job that closes when ClipDrop closes, so it can
    never keep recording on its own after ClipDrop crashes or is ended."""
    global _job
    if sys.platform != "win32":
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateJobObjectW.restype = wintypes.HANDLE
        if _job is None:
            job = k32.CreateJobObjectW(None, None)
            if not job:
                return

            class IO(ctypes.Structure):
                _fields_ = [(n, ctypes.c_ulonglong) for n in
                            ("r", "w", "o", "rb", "wb", "ob")]

            class BASIC(ctypes.Structure):
                _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                            ("PerJobUserTimeLimit", ctypes.c_longlong),
                            ("LimitFlags", wintypes.DWORD),
                            ("MinimumWorkingSetSize", ctypes.c_size_t),
                            ("MaximumWorkingSetSize", ctypes.c_size_t),
                            ("ActiveProcessLimit", wintypes.DWORD),
                            ("Affinity", ctypes.c_size_t),
                            ("PriorityClass", wintypes.DWORD),
                            ("SchedulingClass", wintypes.DWORD)]

            class EXT(ctypes.Structure):
                _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO),
                            ("ProcessMemoryLimit", ctypes.c_size_t),
                            ("JobMemoryLimit", ctypes.c_size_t),
                            ("PeakProcessMemoryUsed", ctypes.c_size_t),
                            ("PeakJobMemoryUsed", ctypes.c_size_t)]

            info = EXT()
            info.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE
            if not k32.SetInformationJobObject(wintypes.HANDLE(job), 9, ctypes.byref(info), ctypes.sizeof(info)):
                return
            _job = job
        k32.AssignProcessToJobObject(wintypes.HANDLE(_job), wintypes.HANDLE(int(proc._handle)))
    except Exception as e:
        log(f"Couldn't tie FFmpeg to ClipDrop: {e!r}")


_leftovers_checked = False


def kill_leftover_ffmpeg():
    """Stop FFmpeg recorders left running by an earlier ClipDrop (one that crashed
    or was ended). They keep writing into our buffer folder, without sound."""
    global _leftovers_checked
    if _leftovers_checked or sys.platform != "win32":
        return
    _leftovers_checked = True
    ps = ("$me = %d; Get-CimInstance Win32_Process -Filter \"Name='ffmpeg.exe'\" | "
          "Where-Object { $_.CommandLine -like '*\\ClipDrop\\buffer\\*' -and $_.ParentProcessId -ne $me } | "
          "ForEach-Object { Write-Output $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }") % os.getpid()
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                           capture_output=True, timeout=20, creationflags=NO_WINDOW)
        pids = r.stdout.decode("utf-8", "replace").split()
        if pids:
            log(f"Stopped {len(pids)} old FFmpeg recorder(s) left running: {', '.join(pids)}")
            time.sleep(0.5)  # let Windows release their files
    except Exception as e:
        log(f"Couldn't check for old FFmpeg recorders: {e!r}")


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


# Encoders that can take the picture straight from the graphics card (D3D11).
GPU_FRAME_ENCODERS = ("_nvenc", "_amf")
_gpu_cache = {}


def gpu_tail(ffmpeg, encoder, monitor=0, height=0):
    """The filters that keep the captured picture on the graphics card all the
    way into the encoder, or None if this PC/FFmpeg can't do that.

    The old way copied every frame from the graphics card to the CPU, scaled
    and converted it there, then sent it back to the card to be encoded. While
    a game is using the PC, that can't keep up and frames get dropped all the
    time. Tried once with a few real frames, then remembered."""
    if not encoder.endswith(GPU_FRAME_ENCODERS) or sys.platform != "win32":
        return None
    key = (ffmpeg, encoder, int(monitor), int(height))
    with _caps_lock:
        if key in _gpu_cache:
            return _gpu_cache[key]
    if height:
        h = int(height) // 2 * 2
        tails = [f",scale_d3d11=width=-2:height={h}", f",scale_d3d11=w=-2:h={h}", f",scale_d3d11=-2:{h}"]
    else:
        tails = [""]
    found = None
    for tail in tails:
        try:
            r = subprocess.run(
                [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                 f"ddagrab=output_idx={int(monitor)}:framerate=30{tail}", "-frames:v", "10",
                 "-c:v", encoder, "-f", "null", "-"],
                capture_output=True, timeout=20, creationflags=NO_WINDOW)
            if r.returncode == 0:
                found = tail
                break
            err = r.stderr.decode("utf-8", "replace").strip().splitlines()
            log(f"Graphics-card capture{' with scaling' if tail else ''} not available: "
                f"{err[-1] if err else 'no message'}")
        except Exception as e:
            log(f"Graphics-card capture check failed: {e!r}")
    with _caps_lock:
        _gpu_cache[key] = found
    return found


def codec_of(encoder):
    if encoder.startswith(("hevc", "libx265")):
        return "hevc"
    if encoder.startswith(("av1", "libsvtav1", "libaom")):
        return "av1"
    return "h264"


def encoder_args(enc, bitrate, fps, keyframe_seconds=SEGMENT_SECONDS, gpu_frames=False):
    """gpu_frames: the picture arrives still on the graphics card (D3D11), so
    the encoder converts the colours itself; asking for a pixel format here
    would force it back through the CPU."""
    gop = str(max(1, int(float(fps) * keyframe_seconds)))  # a keyframe every piece, so cuts are clean
    rate = ["-b:v", bitrate, "-maxrate", bitrate, "-bufsize", bitrate]
    common = ["-g", gop] + ([] if gpu_frames else ["-pix_fmt", "yuv420p"])
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
        self.thread = None
        self.last_write = time.time()

    def alive(self):
        """False if the sound feed to FFmpeg stopped (FFmpeg then can't write anything)."""
        return (self.thread is not None and self.thread.is_alive()
                and time.time() - self.last_write < 5)

    def start(self):
        if sc is None:
            log("No 'soundcard' package: clips will have no sound.")
        if self.game_q is not None:
            self._add_source(self.game_q, lambda: _find_speaker(self.speaker_name), "game sound")
        if self.mic_q is not None:
            self._add_source(self.mic_q, lambda: _find_mic(self.mic_name), "microphone")
        self.thread = threading.Thread(target=self._writer, daemon=True)
        self.thread.start()

    def _add_source(self, q, get_dev, label):
        """Read one sound device into `q` until we stop. If the device can't be
        opened, or goes away (a wireless headset turned off), keep trying every
        few seconds instead of giving up until the next restart."""
        def run():
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.ole32.CoInitializeEx(None, 0)
                except Exception:
                    pass
            last_problem = None
            told_name = None
            while not self.stop_evt.is_set():
                try:
                    dev = get_dev()
                except Exception as e:
                    dev, problem = None, f"{e!r}"
                if dev is not None:
                    if dev.name != told_name:
                        log(f"Recording {label}: {dev.name}")
                        told_name = dev.name
                    problem = self._read_soundcard(dev, q, label)
                    if problem is None:  # stopped on purpose
                        return
                    # soundcard can't open some mics (it only accepts one exact
                    # Windows sound format): use a second library for those
                    if label == "microphone" and problem.startswith("open:"):
                        sd_problem = self._read_sounddevice(dev.name, q, label)
                        if sd_problem is None:
                            return
                        problem += f"; other way: {sd_problem}"
                if problem != last_problem:
                    log(f"{label} unavailable, trying again every 5 seconds: {problem}")
                    last_problem = problem
                self.stop_evt.wait(5)

        threading.Thread(target=run, daemon=True).start()

    def _read_soundcard(self, dev, q, label):
        """Record `dev` into `q`. Returns None when stopped on purpose, else
        why it failed ("open: ..." if it never started)."""
        # Some headsets refuse stereo or our block size: try simpler setups first.
        errors = []
        for channels, blocksize in ((CHANNELS, AUDIO_CHUNK), (1, AUDIO_CHUNK), (CHANNELS, None), (1, None)):
            if self.stop_evt.is_set():
                return None
            opts = {"samplerate": SAMPLE_RATE, "channels": channels}
            if blocksize:
                opts["blocksize"] = blocksize
            started = False
            try:
                with dev.recorder(**opts) as rec:
                    started = True
                    if errors:
                        log(f"{label} works with {channels} channel(s)")
                    while not self.stop_evt.is_set():
                        data = rec.record(numframes=AUDIO_CHUNK)
                        try:
                            q.put_nowait(data)
                        except queue.Full:
                            pass
                return None
            except Exception as e:
                if started:  # it was working, then the device went away
                    return f"stopped: {e!r}"
                errors.append(f"{channels}ch/{blocksize or 'auto'}: {e!r}")
        return "open: " + "; ".join(errors)

    def _read_sounddevice(self, name, q, label):
        """Record a microphone with the 'sounddevice' package (PortAudio), which
        converts any Windows sound format. Returns None when stopped on purpose."""
        try:
            import sounddevice as sd
        except Exception:
            return "the 'sounddevice' package is missing"
        try:
            apis = sd.query_hostapis()
            wasapi = next((i for i, a in enumerate(apis) if "WASAPI" in a["name"]), None)
            found = [(i, d) for i, d in enumerate(sd.query_devices())
                     if d["max_input_channels"] > 0 and (d["name"] == name or name.startswith(d["name"])
                                                         or d["name"].startswith(name))]
            if not found:
                return f"no device called {name}"
            found.sort(key=lambda x: x[1]["hostapi"] != wasapi)  # WASAPI first
            idx, info = found[0]
            extra = sd.WasapiSettings(auto_convert=True) if info["hostapi"] == wasapi else None
            channels = min(CHANNELS, int(info["max_input_channels"]))
            with sd.InputStream(device=idx, samplerate=SAMPLE_RATE, channels=channels, dtype="float32",
                                blocksize=AUDIO_CHUNK, extra_settings=extra) as stream:
                log(f"{label} works through sounddevice ({channels} channel(s))")
                while not self.stop_evt.is_set():
                    data, _ = stream.read(AUDIO_CHUNK)
                    try:
                        q.put_nowait(data.copy())
                    except queue.Full:
                        pass
            return None
        except Exception as e:
            return repr(e)

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
        warned = False
        while not self.stop_evt.is_set():
            pcm = silence
            if np is not None and (self.game_q is not None or self.mic_q is not None):
                try:
                    game = self._take(self.game_q, AUDIO_CHUNK) * self.game_vol
                    if self.want_mic:
                        frame = np.concatenate([game, self._take(self.mic_q, AUDIO_CHUNK) * self.mic_vol], axis=1)
                    else:
                        frame = game
                    pcm = (np.clip(frame, -1, 1) * 32767).astype("<i2").tobytes()
                except Exception as e:  # never let a bad sound chunk stop the feed
                    if not warned:
                        log(f"Sound problem, using silence for now: {e!r}")
                        warned = True
            try:
                self.sink.write(pcm)
            except (BrokenPipeError, OSError, ValueError):
                return
            self.last_write = time.time()
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
    def __init__(self, settings, ffmpeg, buffer_seconds=30, target=None, keep_from=None):
        """target: the game window to record (from winutil.foreground_game),
        used when settings['capture'] == 'window'.
        keep_from: the recorder this one replaces (after a settings change).
        Its pieces are kept, so the replay buffer isn't thrown away."""
        self.s = settings
        self.ffmpeg = ffmpeg
        self.buffer_seconds = int(buffer_seconds)
        self.target = target
        self.buf_root = Path(tempfile.gettempdir()) / "ClipDrop" / "buffer"
        # Each ClipDrop gets its own folder, so pieces left over from an old
        # (crashed) ClipDrop can never end up in a clip.
        if keep_from is not None:
            self.buf_dir = keep_from.buf_dir
            self.runs = dict(keep_from.runs)
        else:
            self.buf_dir = self.buf_root / f"run_{os.getpid()}_{int(time.time() * 1000)}"
            self.runs = {}  # FFmpeg run id -> what it recorded (only matching runs are joined)
        self.proc = None
        self.audio = None
        self.encoder = None
        self.mode = None
        self.running = False
        self.last_error = ""
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.seg_ext = "mkv" if settings.get("video_format") == "av1" else "ts"
        self._tail = ""
        self._restart = threading.Event()
        self._newest = None      # name of the newest piece, and when it first showed up
        self._newest_at = 0.0

    @property
    def out_dir(self):
        return Path(os.path.expandvars(os.path.expanduser(self.s["save_folder"])))

    # ---------- capture

    def _video_input(self, mode):
        fps = str(self.s["fps"])
        mouse = int(bool(self.s.get("show_mouse")))
        if mode == "test":  # for testing without a Windows desktop
            return ["-re", "-f", "lavfi", "-i", f"testsrc2=size=1280x720:rate={fps}"]
        mon = int(self.s.get("monitor", 0))
        t = self.target
        if mode == "ddagrab_gpu":
            return ["-f", "lavfi", "-i",
                    f"ddagrab=output_idx={mon}:framerate={fps}:draw_mouse={mouse}{self._tail}"]
        if mode == "crop_gpu":
            x0, y0, x1, y1 = t["rect"]
            w, h = (x1 - x0) // 2 * 2, (y1 - y0) // 2 * 2
            ox, oy = x0 - t["monitor_left"], y0 - t["monitor_top"]
            return ["-f", "lavfi", "-i",
                    f"ddagrab=output_idx={t['monitor']}:framerate={fps}:draw_mouse={mouse}"
                    f":video_size={w}x{h}:offset_x={ox}:offset_y={oy}{self._tail}"]
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
        """Capture methods, best first. The *_gpu ones keep frames on the
        graphics card; the others copy every frame through the CPU."""
        if self.s.get("test_source"):
            return ["test"]
        gpu = (self.encoder or "").endswith(GPU_FRAME_ENCODERS)
        screen = (["ddagrab_gpu"] if gpu else []) + ["ddagrab", "gdigrab"]
        if self.s.get("capture") == "window" and self.target:
            return ["gfxcapture"] + (["crop_gpu"] if gpu else []) + ["crop"] + screen
        return screen

    def _gpu_ready(self, mode):
        """Can this PC use the graphics-card version of `mode`? Sets self._tail."""
        if mode == "crop_gpu":
            mon = int(self.target.get("monitor", 0))
        else:
            mon = int(self.s.get("monitor", 0))
        tail = gpu_tail(self.ffmpeg, self.encoder, mon, int(self.s.get("height") or 0))
        self._tail = tail or ""
        return tail is not None

    def _launch(self, mode):
        run = str(int(time.time() * 1000))
        pattern = str(self.buf_dir / f"seg_{run}_%06d.{self.seg_ext}")
        mic = bool(self.s.get("microphone"))
        # pieces can only be joined with pieces recorded the same way
        self.runs[run] = repr((self._video_input(mode), self._scale_filter(), self.encoder,
                               self.s.get("fps"), mic, self.seg_ext))
        cmd = [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
               "-thread_queue_size", "1024"] + self._video_input(mode)
        cmd += ["-thread_queue_size", "1024", "-f", "s16le", "-ar", str(SAMPLE_RATE),
                "-ac", "4" if mic else "2", "-i", "pipe:0"]
        gpu = mode.endswith("_gpu")
        vf = self._scale_filter()
        if mic:
            # track 1: game + voice mixed (what your phone plays)
            # track 2: game only, track 3: voice only (for the volume sliders)
            fc = ("[1:a]asplit=3[x][y][z];"
                  "[x]pan=stereo|c0=c0+c2|c1=c1+c3[mix];"
                  "[y]pan=stereo|c0=c0|c1=c1[game];"
                  "[z]pan=stereo|c0=c2|c1=c3[voice]")
            if gpu:
                cmd += ["-filter_complex", fc, "-map", "0:v"]
            else:
                cmd += ["-filter_complex", f"[0:v]{vf}[v];" + fc, "-map", "[v]"]
            cmd += ["-map", "[mix]", "-map", "[game]", "-map", "[voice]"]
        else:
            cmd += ["-map", "0:v", "-map", "1:a"] + ([] if gpu else ["-vf", vf])
        cmd += encoder_args(self.encoder, self.s["bitrate"], self.s["fps"], gpu_frames=gpu)
        cmd += ["-c:a", "aac", "-b:a", "192k",
                "-f", "segment", "-segment_time", str(SEGMENT_SECONDS),
                "-segment_format", "matroska" if self.seg_ext == "mkv" else "mpegts"]
        if self.seg_ext == "mkv":
            # MKV pieces are joined one by one, so each starts at zero. TS pieces
            # keep running timestamps and are joined back to back (see save_clip).
            # The piece list says exactly how long each piece's picture is,
            # so they can be joined without a gap (see _join_input).
            cmd += ["-reset_timestamps", "1", "-segment_list", str(self.buf_dir / f"list_{run}.csv"),
                    "-segment_list_type", "csv", "-segment_list_size", "300"]
        cmd += [pattern]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                                     creationflags=NO_WINDOW | ABOVE_NORMAL)
        _kill_with_us(self.proc)
        self.audio = AudioPump(self.proc.stdin, self.s)
        self.audio.start()

    def _clear_old_buffers(self):
        """Delete pieces left by earlier recordings (skips files still in use)."""
        if not self.buf_root.exists():
            return
        for p in self.buf_root.iterdir():
            if p == self.buf_dir:
                continue
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                try:
                    p.unlink()
                except OSError:
                    pass

    def start(self):
        kill_leftover_ffmpeg()
        self._clear_old_buffers()
        self.buf_dir.mkdir(parents=True, exist_ok=True)
        for p in self.buf_dir.glob("seg_*"):  # pieces in the other format (format was changed)
            if p.suffix != "." + self.seg_ext:
                try:
                    p.unlink()
                except OSError:
                    pass
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.encoder = pick_encoder(self.ffmpeg, self.s.get("video_format", "h264"), self.s.get("encoder", "auto"))
        log(f"Encoder: {self.encoder}")
        threading.Thread(target=self._supervise, daemon=True).start()

    def _supervise(self):
        modes = self._modes()
        mi = 0
        quick_fails = 0      # FFmpeg runs in a row that died within 10 s
        fell_back_at = None  # when we last moved to a slower capture method
        while not self._stop.is_set():
            mode = modes[min(mi, len(modes) - 1)]
            if mode.endswith("_gpu") and not self._gpu_ready(mode):
                mi += 1
                continue
            self.mode = mode
            what = f"window of {self.target['name']}" if mode in ("gfxcapture", "crop", "crop_gpu") else "screen"
            log(f"Recording {what} ({mode}, {self.s['fps']} fps, {self.s['bitrate']}), "
                f"keeping last {self.buffer_seconds}s")
            self._restart.clear()
            self._launch(mode)
            started = time.time()
            segs = self._segments()
            self._newest, self._newest_at = (segs[-1].name if segs else None), started
            self.running = True
            stuck = False
            while self.proc.poll() is None and not self._stop.is_set():
                self._cleanup()
                problem = self._stalled(started)
                if not problem and self._restart.is_set():
                    problem = "a clip was asked for but no new video came in"
                if problem:
                    log(f"Recording got stuck ({problem}), restarting it")
                    stuck = True
                    break
                self._stop.wait(1)
            self.running = False
            if self.audio:
                self.audio.stop()
            if self.proc.poll() is None:
                # stopped or stuck: never leave this FFmpeg running on its own
                try:
                    self.proc.kill()
                except Exception:
                    pass
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            if stuck and self._newest:
                # the piece that kept growing holds sound but no picture: drop it
                # so no clip ever includes it
                try:
                    self.proc.wait(timeout=5)
                    (self.buf_dir / self._newest).unlink()
                except Exception:
                    pass
            if self._stop.is_set():
                break
            err = (self.proc.stderr.read() or b"").decode("utf-8", "replace").strip()
            self.last_error = err[-500:]
            log(f"FFmpeg stopped ({mode}): {self.last_error or 'no message'}")
            # getting stuck counts as a failure too: if this capture keeps
            # freezing, move to a slower one that works
            if time.time() - started < 10 or stuck:
                quick_fails += 1
            else:
                quick_fails = 0
            # One hiccup is not a reason to drop to a slower method for good:
            # only move down after 3 quick failures in a row, and try the best
            # method again 5 minutes later.
            if quick_fails >= 3 and mi < len(modes) - 1:
                mi += 1
                quick_fails = 0
                fell_back_at = time.time()
                log(f"Switching to the slower {modes[mi]} capture")
            elif mi > 0 and fell_back_at and time.time() - fell_back_at > 300:
                mi = 0
                quick_fails = 0
                fell_back_at = None
                log("Trying the faster capture again")
            # wait longer after each failure in a row (2, 4, 8 ... 60 s)
            self._stop.wait(min(60, 2 ** (quick_fails + 1)) if quick_fails else 2)

    def _stalled(self, started):
        """Why the running FFmpeg looks stuck, or '' if it's fine.

        A new piece starts every 2 seconds, but only when new video arrives.
        If the capture freezes while the sound keeps coming, the newest piece
        just keeps growing (it once grew for an hour), so we watch for new
        pieces, not for the file changing."""
        if self.audio and time.time() - started > 20 and not self.audio.alive():
            return "the sound feed stopped"
        segs = self._segments()
        newest = segs[-1].name if segs else None
        now = time.time()
        if newest != self._newest:
            self._newest, self._newest_at = newest, now
            return ""
        if now - started > 15 and now - self._newest_at > STALL_SECONDS:
            return f"no new video for {int(now - self._newest_at)} seconds"
        return ""

    def _segments(self):
        out = []
        for p in self.buf_dir.glob(f"seg_*.{self.seg_ext}"):
            try:
                out.append((p.stat().st_mtime, p.name, p))
            except OSError:  # deleted just now
                pass
        return [p for _, _, p in sorted(out)]

    @staticmethod
    def _run_of(p):
        return p.name[4:].rsplit("_", 1)[0]  # seg_<run>_<n>.ext

    def _cleanup(self):
        segs = self._segments()
        keep = self.buffer_seconds // SEGMENT_SECONDS + 3
        for p in segs[:-keep]:
            try:
                p.unlink()
            except OSError:
                pass  # still open, try next time
        live = {self._run_of(p) for p in segs[-keep:]}
        for run in [r for r in self.runs if r not in live and r != max(self.runs)]:
            self.runs.pop(run, None)
            try:
                (self.buf_dir / f"list_{run}.csv").unlink(missing_ok=True)
            except OSError:
                pass

    # ---------- saving

    def save_clip(self, seconds=30, game=None):
        """Join the last `seconds` of the buffer into an MP4. Returns its path.
        Clips go into a subfolder named after the game, if we know it."""
        seconds = int(seconds)
        with self._lock:
            if not self.running:
                raise RuntimeError("Recording is restarting. Try again in a few seconds.")
            # Wait for the piece being recorded right now to finish, so the
            # clip ends at the moment you pressed the key. A new piece starts
            # every 2 seconds; if none does, the capture froze, and the pieces
            # we have are old: never hand those out as "the last minute".
            first = {p.name for p in self._segments()}
            deadline = time.time() + 2 * SEGMENT_SECONDS + 2
            rotated = False
            while time.time() < deadline:
                now = self._segments()
                if now and now[-1].name not in first:  # a brand-new piece started
                    rotated = True
                    break
                time.sleep(0.1)
            if not rotated:
                self._restart.set()
                raise RuntimeError("Recording froze, so ClipDrop is restarting it. "
                                   "Try again in a few seconds.")
            finished = self._segments()[:-1]  # the newest one is still being written
            # the piece that just finished must be from right now; if it's old,
            # the recording restarted and has nothing new yet
            try:
                fresh = bool(finished) and time.time() - finished[-1].stat().st_mtime < SEGMENT_SECONDS + 3
            except OSError:
                fresh = False
            if finished and not fresh:
                raise RuntimeError("Recording is restarting. Try again in a few seconds.")
            segs = self._clip_pieces(finished, seconds)
            if not segs:
                raise RuntimeError("Nothing recorded yet. Wait a few seconds and try again.")
            stamp = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            folder = self.out_dir / game if game else self.out_dir
            folder.mkdir(parents=True, exist_ok=True)
            out = folder / f"{game or 'Clip'} {stamp}.mp4"
            if out.exists():
                out = folder / f"{game or 'Clip'} {stamp} ({seconds}s).mp4"
            src = self._join_input(segs)

            def join(maps):
                return subprocess.run(
                    [self.ffmpeg, "-hide_banner", "-loglevel", "error", "-y"] + src + maps +
                    ["-c", "copy", "-avoid_negative_ts", "make_zero"] + mp4_tag(self.encoder) +
                    ["-movflags", "+faststart", str(out)],
                    capture_output=True, timeout=120, creationflags=NO_WINDOW, cwd=str(self.buf_dir))

            r = join(["-map", "0"])
            if r.returncode != 0 or not out.exists():
                err = r.stderr.decode("utf-8", "replace")
                # the pieces have sound tracks with no sound in them: keep the video
                if "sample rate not set" in err or "incorrect codec parameters" in err:
                    log("These pieces have no sound in them, saving the clip without sound")
                    r = join(["-map", "0:v"])
                    if r.returncode == 0 and out.exists():
                        log(f"Saved {out.name} (no sound)")
                        return out
                    err = r.stderr.decode("utf-8", "replace")
                out.unlink(missing_ok=True)
                raise RuntimeError(err[-400:] or "FFmpeg failed")
            log(f"Saved {out.name}")
            return out

    def _clip_pieces(self, segs, seconds):
        """The newest pieces that make up the last `seconds`: one unbroken
        stretch, all recorded the same way (settings can change in between)."""
        if not segs:
            return []
        want = max(1, -(-seconds // SEGMENT_SECONDS))
        kind = self.runs.get(self._run_of(segs[-1]))
        picked = [segs[-1]]
        try:
            later = segs[-1].stat().st_mtime
        except OSError:
            return []
        for p in reversed(segs[:-1]):
            if len(picked) >= want:
                break
            try:
                t = p.stat().st_mtime
            except OSError:
                break
            if later - t > MAX_JOIN_GAP or self.runs.get(self._run_of(p)) != kind:
                break
            picked.append(p)
            later = t
        return picked[::-1]

    def _piece_lengths(self):
        """MKV pieces: how long each one's picture is, from FFmpeg's piece lists."""
        out = {}
        for lst in self.buf_dir.glob("list_*.csv"):
            try:
                for line in lst.read_text(encoding="utf-8", errors="replace").splitlines():
                    name, start, end = line.rsplit(",", 2)
                    out[Path(name.strip('"')).name] = float(end) - float(start)
            except (OSError, ValueError):
                pass
        return out

    def _join_input(self, segs):
        """FFmpeg input arguments that read `segs` as one clip.

        TS pieces from the same FFmpeg run carry running timestamps, so they
        are read back to back as one stream ("concat:" protocol) and every frame
        keeps its exact time. Joining them one by one (the concat list) left a
        frame or two missing at every 2 s join, because each piece's sound runs
        a little longer than its picture. Pieces from different runs (after a
        restart) are still joined run by run with the concat list."""
        lst = self.buf_dir / "concat.txt"
        if self.seg_ext != "ts":
            # Each MKV piece starts at zero. Without the exact picture length,
            # the next piece would start after the (slightly longer) sound and
            # leave a frame-long hole at every join.
            lengths = self._piece_lengths()
            lines = []
            for p in segs:
                lines.append(f"file '{p.name}'\n")
                if lengths.get(p.name, 0) > 0:
                    lines.append(f"duration {lengths[p.name]:.6f}\n")
            lst.write_text("".join(lines), encoding="utf-8")
            return ["-f", "concat", "-safe", "0", "-i", lst.name]
        runs = []
        for p in segs:  # seg_<run>_<n>.ts
            run = self._run_of(p)
            if runs and runs[-1][0] == run:
                runs[-1][1].append(p.name)
            else:
                runs.append((run, [p.name]))
        if len(runs) == 1:
            return ["-i", "concat:" + "|".join(runs[0][1])]
        lst.write_text("".join(f"file 'concat:{'|'.join(names)}'\n" for _, names in runs), encoding="utf-8")
        return ["-protocol_whitelist", "file,concat", "-f", "concat", "-safe", "0", "-i", lst.name]

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

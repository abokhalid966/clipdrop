"""
Windows helpers: global hotkeys, finding the game you're playing, monitors,
the in-game "Clip saved" pop-up, and sounds. On other systems these quietly
do nothing, so the rest of the app can still be tested.
"""

import sys
import threading
from pathlib import Path

IS_WIN = sys.platform == "win32"

if IS_WIN:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    gdi32 = ctypes.windll.gdi32

    # Tell ctypes the real types, so 64-bit window handles aren't cut short
    def _sig(fn, res, *args):
        fn.restype = res
        fn.argtypes = list(args)

    H, HW = wintypes.HANDLE, wintypes.HWND
    _sig(user32.GetForegroundWindow, HW)
    _sig(user32.GetWindowThreadProcessId, wintypes.DWORD, HW, ctypes.POINTER(wintypes.DWORD))
    _sig(user32.GetClientRect, wintypes.BOOL, HW, ctypes.POINTER(wintypes.RECT))
    _sig(user32.ClientToScreen, wintypes.BOOL, HW, ctypes.POINTER(wintypes.POINT))
    _sig(user32.IsWindow, wintypes.BOOL, HW)
    _sig(user32.GetMonitorInfoW, wintypes.BOOL, H, ctypes.c_void_p)
    _sig(kernel32.OpenProcess, H, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _sig(kernel32.QueryFullProcessImageNameW, wintypes.BOOL, H, wintypes.DWORD, wintypes.LPWSTR,
         ctypes.POINTER(wintypes.DWORD))
    _sig(kernel32.CloseHandle, wintypes.BOOL, H)
    _sig(kernel32.GetModuleHandleW, H, wintypes.LPCWSTR)
    _sig(user32.BeginPaint, H, HW, ctypes.c_void_p)
    _sig(user32.EndPaint, wintypes.BOOL, HW, ctypes.c_void_p)
    _sig(user32.FillRect, ctypes.c_int, H, ctypes.POINTER(wintypes.RECT), H)
    _sig(user32.DrawTextW, ctypes.c_int, H, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT)
    _sig(gdi32.CreateSolidBrush, H, wintypes.DWORD)
    _sig(gdi32.DeleteObject, wintypes.BOOL, H)
    _sig(gdi32.SelectObject, H, H, H)
    _sig(gdi32.SetBkMode, ctypes.c_int, H, ctypes.c_int)
    _sig(gdi32.SetTextColor, wintypes.DWORD, H, wintypes.DWORD)
    _sig(gdi32.CreateFontW, H, *([ctypes.c_int] * 5), *([wintypes.DWORD] * 8), wintypes.LPCWSTR)
    _sig(user32.CreateWindowExW, HW, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
         ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, HW, H, H, ctypes.c_void_p)
    _sig(user32.DestroyWindow, wintypes.BOOL, HW)
    _sig(user32.ShowWindow, wintypes.BOOL, HW, ctypes.c_int)
    _sig(user32.UpdateWindow, wintypes.BOOL, HW)
    _sig(user32.SetTimer, ctypes.c_size_t, HW, ctypes.c_size_t, wintypes.UINT, ctypes.c_void_p)
    _sig(user32.SetLayeredWindowAttributes, wintypes.BOOL, HW, wintypes.DWORD, ctypes.c_ubyte, wintypes.DWORD)
    _sig(user32.SetWindowDisplayAffinity, wintypes.BOOL, HW, wintypes.DWORD)
    _sig(user32.UnregisterClassW, wintypes.BOOL, wintypes.LPCWSTR, H)
    try:
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # per-monitor v2: real pixel sizes
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

MODS = {"alt": 0x0001, "ctrl": 0x0002, "control": 0x0002, "shift": 0x0004, "win": 0x0008}
NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

# Programs that are never "the game"
NOT_GAMES = {"explorer", "chrome", "msedge", "firefox", "opera", "brave", "discord", "steam",
             "steamwebhelper", "epicgameslauncher", "battle.net", "code", "python", "pythonw",
             "windowsterminal", "cmd", "powershell", "applicationframehost", "searchhost",
             "shellexperiencehost", "startmenuexperiencehost", "obs64", "spotify", "vlc",
             "lockapp", "textinputhost", "taskmgr", "claude", "whatsapp", "telegram",
             "nvidia app", "nvcontainer", "wscript", "mpc-hc64", "photos", "systemsettings"}

KEY_NAMES = {"printscreen": 0x2C, "prtsc": 0x2C, "pause": 0x13, "home": 0x24, "end": 0x23,
             "insert": 0x2D, "delete": 0x2E, "pageup": 0x21, "pagedown": 0x22,
             "num0": 0x60, "num1": 0x61, "num2": 0x62, "num3": 0x63, "num4": 0x64,
             "num5": 0x65, "num6": 0x66, "num7": 0x67, "num8": 0x68, "num9": 0x69}


def parse_hotkey(text):
    """'ctrl+f9' -> (modifiers, virtual key code)."""
    mods, vk = 0, None
    for part in text.lower().replace(" ", "").split("+"):
        if not part:
            continue
        if part in MODS:
            mods |= MODS[part]
        elif len(part) >= 2 and part[0] == "f" and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            vk = 0x70 + int(part[1:]) - 1
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part in KEY_NAMES:
            vk = KEY_NAMES[part]
        else:
            raise ValueError(f"Unknown key: {part}")
    if vk is None:
        raise ValueError("A hotkey needs a key, like ctrl+f9")
    return mods, vk


class Hotkeys:
    """Registers several hotkeys at once. `items` is a list of (text, callback).
    They work even while a game has focus."""

    def __init__(self, items):
        self.items = items
        self.thread_id = None
        self.ok = {}      # text -> True/False
        self.errors = {}  # text -> message

    def start(self):
        if not IS_WIN:
            for text, _ in self.items:
                self.ok[text] = False
                self.errors[text] = "Hotkeys only work on Windows"
            return
        ready = threading.Event()
        threading.Thread(target=self._run, args=(ready,), daemon=True).start()
        ready.wait(2)

    def _run(self, ready):
        self.thread_id = kernel32.GetCurrentThreadId()
        callbacks = {}
        for i, (text, cb) in enumerate(self.items, start=1):
            try:
                mods, vk = parse_hotkey(text)
            except ValueError as e:
                self.ok[text], self.errors[text] = False, str(e)
                continue
            if user32.RegisterHotKey(None, i, mods | NOREPEAT, vk):
                self.ok[text] = True
                callbacks[i] = cb
            else:
                self.ok[text] = False
                self.errors[text] = f"{text} is already used by another app. Pick another one."
        ready.set()
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY and msg.wParam in callbacks:
                threading.Thread(target=callbacks[msg.wParam], daemon=True).start()
        for i in callbacks:
            user32.UnregisterHotKey(None, i)

    def stop(self):
        if IS_WIN and self.thread_id:
            user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


# ------------------------------------------------------------------ monitors

def monitors():
    """List of screens: [{'index', 'name', 'width', 'height', 'left', 'top', 'primary'}]."""
    if not IS_WIN:
        return [{"index": 0, "name": "Screen 1", "width": 1920, "height": 1080,
                 "left": 0, "top": 0, "primary": True}]
    out = []

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.c_int, wintypes.HMONITOR, wintypes.HDC,
                                         ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)

    def cb(hmon, hdc, rect, lparam):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.rcMonitor
        out.append({"handle": hmon, "width": r.right - r.left, "height": r.bottom - r.top,
                    "left": r.left, "top": r.top, "primary": bool(mi.dwFlags & 1)})
        return 1

    user32.EnumDisplayMonitors(None, None, MonitorEnumProc(cb), 0)
    # FFmpeg's screen numbers usually start with the main screen
    out.sort(key=lambda m: (not m["primary"], m["left"], m["top"]))
    for i, m in enumerate(out):
        m["index"] = i
        m["name"] = f"Screen {i + 1}" + (" (main)" if m["primary"] else "")
    return out


# ------------------------------------------------------------------ game detection

def _exe_name(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return None
        return Path(buf.value).stem
    finally:
        kernel32.CloseHandle(h)


def nice_name(exe):
    name = exe
    for suffix in ("-win64-shipping", "-win32-shipping", "_dx12", "_dx11", "_x64", "x64"):
        if name.lower().endswith(suffix) and len(name) > len(suffix):
            name = name[: -len(suffix)]
    return "".join(c for c in name if c not in '\\/:*?"<>|').strip() or None


def _client_rect_on_screen(hwnd):
    r = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, pt.x + (r.right - r.left), pt.y + (r.bottom - r.top)


def window_alive(hwnd):
    return bool(IS_WIN and hwnd and user32.IsWindow(hwnd))


def foreground_game(extra_games=(), not_games=()):
    """The game in front, or None.

    A program counts as a game if it's in `extra_games`, or if its window
    fills a whole screen (fullscreen or borderless), and it isn't a browser,
    Discord, etc.
    """
    if not IS_WIN:
        return None
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        exe = _exe_name(hwnd)
        if not exe:
            return None
        low = exe.lower()
        extra = {g.lower().removesuffix(".exe") for g in extra_games}
        never = NOT_GAMES | {g.lower().removesuffix(".exe") for g in not_games}
        if low in never and low not in extra:
            return None
        x0, y0, x1, y1 = _client_rect_on_screen(hwnd)
        mons = monitors()
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        mon = next((m for m in mons if m["left"] <= cx < m["left"] + m["width"]
                    and m["top"] <= cy < m["top"] + m["height"]), mons[0] if mons else None)
        if not mon:
            return None
        fills = (x1 - x0) >= mon["width"] - 2 and (y1 - y0) >= mon["height"] - 2
        if not fills and low not in extra:
            return None
        return {"name": nice_name(exe), "exe": exe, "hwnd": int(hwnd),
                "rect": (x0, y0, x1, y1), "monitor": mon["index"],
                "monitor_left": mon["left"], "monitor_top": mon["top"]}
    except Exception:
        return None


def foreground_app():
    """Name of whatever program is in front (used to name clips)."""
    if not IS_WIN:
        return None
    try:
        exe = _exe_name(user32.GetForegroundWindow())
        if not exe or exe.lower() in NOT_GAMES:
            return None
        return nice_name(exe)
    except Exception:
        return None


# ------------------------------------------------------------------ feedback

def ding(ok=True):
    if not IS_WIN:
        return
    try:
        import winsound
        if ok:
            winsound.Beep(880, 70)
            winsound.Beep(1320, 90)
        else:
            winsound.MessageBeep(0x10)
    except Exception:
        pass


_overlay_lock = threading.Lock()


def show_overlay(text, seconds=2.0, ok=True):
    """A small "Clip saved" bubble in the top-right corner, on top of the game.

    Works over borderless/windowed games. Games in exclusive fullscreen don't
    allow anything on top of them; there you'll only hear the sound.
    It's hidden from screen recording, so it never ends up in your clips.
    """
    if not IS_WIN:
        return
    threading.Thread(target=_overlay_thread, args=(text, seconds, ok), daemon=True).start()


def _overlay_thread(text, seconds, ok):
    if not _overlay_lock.acquire(blocking=False):
        return  # one at a time
    try:
        _overlay(text, seconds, ok)
    except Exception:
        pass
    finally:
        _overlay_lock.release()


def _overlay(text, seconds, ok):
    WS_POPUP = 0x80000000
    WS_EX = 0x00000008 | 0x00080000 | 0x00000020 | 0x00000080 | 0x08000000  # topmost|layered|transparent|toolwindow|noactivate
    LWA_ALPHA = 0x2
    WM_PAINT, WM_DESTROY, WM_TIMER = 0x000F, 0x0002, 0x0113
    SW_SHOWNOACTIVATE = 4
    W, HGT = 360, 64

    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    user32.DefWindowProcW.restype = LRESULT
    user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]

    class PAINTSTRUCT(ctypes.Structure):
        _fields_ = [("hdc", wintypes.HDC), ("fErase", wintypes.BOOL), ("rcPaint", wintypes.RECT),
                    ("fRestore", wintypes.BOOL), ("fIncUpdate", wintypes.BOOL), ("rgbReserved", ctypes.c_byte * 32)]

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HINSTANCE), ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    accent = 0x9AF27C if ok else 0x6B6BFF  # BGR: green / red
    bg = 0x13100E

    def wndproc(hwnd, msg, wp, lp):
        if msg == WM_PAINT:
            ps = PAINTSTRUCT()
            hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
            rc = wintypes.RECT(0, 0, W, HGT)
            brush = gdi32.CreateSolidBrush(bg)
            user32.FillRect(hdc, ctypes.byref(rc), brush)
            gdi32.DeleteObject(brush)
            bar = gdi32.CreateSolidBrush(accent)
            user32.FillRect(hdc, ctypes.byref(wintypes.RECT(0, 0, 6, HGT)), bar)
            gdi32.DeleteObject(bar)
            font = gdi32.CreateFontW(-20, 0, 0, 0, 600, 0, 0, 0, 0, 0, 0, 5, 0, "Segoe UI")
            old = gdi32.SelectObject(hdc, font)
            gdi32.SetBkMode(hdc, 1)
            gdi32.SetTextColor(hdc, 0xFFFFFF)
            tr = wintypes.RECT(22, 0, W - 10, HGT)
            flags = 0x24 | 0x20 | 0x8000  # vcenter|singleline|ellipsis
            if any("\u0600" <= ch <= "\u06ff" for ch in text):
                flags |= 0x20000 | 0x2  # right-to-left, right aligned (Arabic)
            user32.DrawTextW(hdc, text, -1, ctypes.byref(tr), flags)
            gdi32.SelectObject(hdc, old)
            gdi32.DeleteObject(font)
            user32.EndPaint(hwnd, ctypes.byref(ps))
            return 0
        if msg == WM_TIMER:
            user32.DestroyWindow(hwnd)
            return 0
        if msg == WM_DESTROY:
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wp, lp)

    proc = WNDPROC(wndproc)
    hinst = kernel32.GetModuleHandleW(None)
    cls = f"ClipDropOverlay{threading.get_ident()}"
    wc = WNDCLASSW(0, proc, 0, 0, hinst, None, None, None, None, cls)
    user32.RegisterClassW(ctypes.byref(wc))
    mons = monitors()
    mon = next((m for m in mons if m["primary"]), mons[0])
    x = mon["left"] + mon["width"] - W - 24
    y = mon["top"] + 24
    user32.CreateWindowExW.restype = wintypes.HWND
    hwnd = user32.CreateWindowExW(WS_EX, cls, "ClipDrop", WS_POPUP, x, y, W, HGT, None, None, hinst, None)
    if not hwnd:
        return
    try:
        user32.SetWindowDisplayAffinity(hwnd, 0x11)  # keep it out of recordings
    except Exception:
        pass
    user32.SetLayeredWindowAttributes(hwnd, 0, 235, LWA_ALPHA)
    user32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)
    user32.UpdateWindow(hwnd)
    user32.SetTimer(hwnd, 1, int(seconds * 1000), None)
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
    user32.UnregisterClassW(cls, hinst)


def open_app_window(url):
    """Open the ClipDrop page in its own window (Edge app mode), else the browser."""
    import os
    import subprocess
    import webbrowser
    if IS_WIN:
        for base in (os.environ.get("ProgramFiles(x86)", ""), os.environ.get("ProgramFiles", ""),
                     os.environ.get("LOCALAPPDATA", "")):
            for exe in (Path(base) / "Microsoft/Edge/Application/msedge.exe",
                        Path(base) / "Google/Chrome/Application/chrome.exe"):
                if base and exe.exists():
                    subprocess.Popen([str(exe), f"--app={url}", "--window-size=1200,820"])
                    return
    webbrowser.open(url)

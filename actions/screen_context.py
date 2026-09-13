"""
Accio Screen Context Understander - Background Screen & Active Window Lens
==========================================================================
WHAT THIS FILE DOES (Simple English):
  This module acts as the "eyes and spatial awareness" of Accio.
  Whenever the user asks a question about their current screen (e.g. "What's on my screen?",
  "Summarize this page", "What does this error mean?", "Explain what I am looking at"),
  this module inspects the currently focused application (e.g. Chrome, VS Code, Word, Terminal),
  reads the window title, captures a lightweight in-memory visual snapshot, and provides
  rich context to the Accio intelligence layer so it can answer immediately through voice.

SENIOR ARCHITECTURE & PRIVACY PRINCIPLES:
  - On-Demand Capture: Snapshots are taken ONLY when the user asks a screen-related question.
    No background screen recording or passive video streaming.
  - Zero Disk Footprint: Screen snapshots are compressed and kept in RAM as base64 JPEG bytes;
    nothing is ever written to the hard drive, protecting privacy and disk hygiene.
  - Crash-Resilient: Every Win32 handle and screenshot call is defensively wrapped with multi-tier
    fallbacks (Active Window -> Full Primary Screen -> Process Metadata).

  - Multi-Strategy Capture:
      When running from a subprocess context (e.g. Antigravity IDE terminal), the standard
      GetForegroundWindow() and ImageGrab.grab() often return hwnd=0 / black images because the
      subprocess doesn't own the interactive desktop's GDI context.
      We solve this with a three-tier strategy:
        Tier 1: Standard GetForegroundWindow + ImageGrab (works when run natively)
        Tier 2: EnumWindows / GetWindow chain to find the topmost titled window
        Tier 3: psutil process enumeration with command-line parsing for rich metadata
                 (e.g. VS Code's open file paths, Chrome's tab titles)
      For screenshots:
        Tier 1: PIL ImageGrab.grab()
        Tier 2: mss (python-mss) GPU-aware capture
        Tier 3: Black-screen detection + metadata-only context (no hallucinated screenshot)
"""

import io
import re
import base64
import ctypes
import subprocess
import statistics
from typing import Dict, Any, Optional, List, Tuple

try:
    import win32gui
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from PIL import Image, ImageGrab, ImageStat
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import mss as mss_module
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

# Mapping process executables to friendly user-facing application names
FRIENDLY_APP_NAMES = {
    "chrome.exe": "Google Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Mozilla Firefox",
    "code.exe": "Visual Studio Code",
    "notepad.exe": "Notepad",
    "notepad++.exe": "Notepad++",
    "wordpad.exe": "WordPad",
    "winword.exe": "Microsoft Word",
    "excel.exe": "Microsoft Excel",
    "powerpnt.exe": "Microsoft PowerPoint",
    "explorer.exe": "File Explorer",
    "windowsterminal.exe": "Windows Terminal",
    "powershell.exe": "PowerShell",
    "cmd.exe": "Command Prompt",
    "whatsapp.exe": "WhatsApp",
    "slack.exe": "Slack",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "acrobat.exe": "Adobe Acrobat",
    "electron.exe": "Accio Desktop",
    "devenv.exe": "Visual Studio",
    "idea64.exe": "IntelliJ IDEA",
    "pycharm64.exe": "PyCharm",
    "postman.exe": "Postman",
    "figma.exe": "Figma",
    "teams.exe": "Microsoft Teams",
    "outlook.exe": "Microsoft Outlook",
    "onenote.exe": "OneNote",
}

# GUI applications that indicate the user is actively working
GUI_APP_EXECUTABLES = set(FRIENDLY_APP_NAMES.keys()) | {
    "javaw.exe", "node.exe", "python.exe", "python3.exe",
    "photoshop.exe", "illustrator.exe", "premiere.exe",
    "obs64.exe", "vlc.exe", "mspaint.exe",
}


def _set_dpi_awareness():
    """Set DPI awareness to PER_MONITOR_DPI_AWARE for accurate screen metrics."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _enumerate_visible_windows() -> List[Dict[str, Any]]:
    """
    Enumerate all visible top-level windows with titles using GetWindow chain.
    This works even from subprocess contexts where EnumWindows may fail.
    Returns list of window info dicts sorted by Z-order (topmost first).
    """
    windows = []
    if not HAS_WIN32:
        return windows

    try:
        desktop = win32gui.GetDesktopWindow()
        child = win32gui.GetWindow(desktop, 5)  # GW_CHILD
        limit = 100  # Safety limit

        while child and limit > 0:
            limit -= 1
            try:
                if win32gui.IsWindowVisible(child):
                    title = win32gui.GetWindowText(child)
                    if title and title.strip():
                        win_info = {
                            "hwnd": child,
                            "title": title.strip(),
                            "process_name": "",
                            "friendly_name": "Desktop Application",
                        }
                        try:
                            _, raw_pid = win32process.GetWindowThreadProcessId(child)
                            pid = ctypes.c_ulong(raw_pid).value
                            if HAS_PSUTIL and pid > 0:
                                proc = psutil.Process(pid)
                                pname = proc.name().lower()
                                win_info["process_name"] = pname
                                win_info["friendly_name"] = FRIENDLY_APP_NAMES.get(
                                    pname, pname.replace('.exe', '').capitalize()
                                )
                        except Exception:
                            pass
                        windows.append(win_info)
            except Exception:
                pass
            try:
                child = win32gui.GetWindow(child, 2)  # GW_HWNDNEXT
            except Exception:
                break

    except Exception:
        pass

    return windows


def _get_running_gui_apps() -> List[Dict[str, str]]:
    """
    Fallback: Use psutil to enumerate currently running GUI applications
    with their command-line arguments (to extract open files, URLs, etc.).
    Works even when window handle enumeration fails completely.
    """
    apps = []
    if not HAS_PSUTIL:
        return apps

    try:
        for proc in psutil.process_iter(['name', 'pid', 'cmdline', 'status']):
            try:
                info = proc.info
                pname = (info.get('name') or '').lower()
                if pname in GUI_APP_EXECUTABLES:
                    friendly = FRIENDLY_APP_NAMES.get(pname, pname.replace('.exe', '').capitalize())
                    cmdline = info.get('cmdline') or []

                    # Extract useful context from command line arguments
                    context_hint = ""
                    if pname == 'code.exe' and len(cmdline) > 1:
                        # VS Code: command line often has workspace/folder paths
                        for arg in cmdline[1:]:
                            if not arg.startswith('-') and ('\\' in arg or '/' in arg):
                                context_hint = f"editing: {arg}"
                                break
                    elif pname in ('chrome.exe', 'msedge.exe', 'firefox.exe') and len(cmdline) > 1:
                        for arg in cmdline[1:]:
                            if arg.startswith('http') or arg.startswith('www'):
                                context_hint = f"browsing: {arg}"
                                break

                    apps.append({
                        "process_name": pname,
                        "friendly_name": friendly,
                        "context_hint": context_hint,
                        "pid": str(info.get('pid', ''))
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception:
        pass

    # Deduplicate by process name, keeping the one with context
    seen = {}
    for app in apps:
        key = app["process_name"]
        if key not in seen or (app["context_hint"] and not seen[key]["context_hint"]):
            seen[key] = app
    return list(seen.values())


def _get_window_titles_via_powershell() -> List[Dict[str, str]]:
    """
    Last-resort fallback: Use PowerShell to get processes with main window titles.
    This bypasses Win32 API limitations in subprocess contexts.
    """
    try:
        ps_cmd = (
            'Get-Process | Where-Object {$_.MainWindowTitle -ne ""} | '
            'ForEach-Object { "$($_.ProcessName)|$($_.MainWindowTitle)" }'
        )
        result = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_cmd],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            windows = []
            for line in result.stdout.strip().split('\n'):
                line = line.strip()
                if '|' in line:
                    parts = line.split('|', 1)
                    pname = parts[0].strip().lower()
                    title = parts[1].strip()
                    if title:
                        exe_name = pname + '.exe' if not pname.endswith('.exe') else pname
                        windows.append({
                            "process_name": exe_name,
                            "friendly_name": FRIENDLY_APP_NAMES.get(exe_name, pname.capitalize()),
                            "title": title,
                        })
            return windows
    except Exception:
        pass
    return []


def get_active_window_context() -> Dict[str, Any]:
    """
    Safely inspects the current foreground window on Windows using multi-tier strategies.
    Tier 1: GetForegroundWindow (standard Win32)
    Tier 2: EnumWindows / GetWindow chain (finds topmost titled window)
    Tier 3: psutil process scan + PowerShell window title extraction
    Returns process name, friendly app name, window title, and window bounding coordinates.
    """
    context = {
        "title": "",
        "process_name": "",
        "friendly_name": "Desktop Application",
        "hwnd": 0,
        "rect": None,
        "is_valid": False,
        "running_apps": [],  # List of other detected running GUI apps
    }

    # ---- Tier 1: Standard GetForegroundWindow ----
    if HAS_WIN32:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd and win32gui.IsWindow(hwnd):
                title = win32gui.GetWindowText(hwnd).strip()
                if title:
                    context["hwnd"] = hwnd
                    context["title"] = title

                    _, raw_pid = win32process.GetWindowThreadProcessId(hwnd)
                    pid = ctypes.c_ulong(raw_pid).value
                    if HAS_PSUTIL and pid > 0:
                        try:
                            proc = psutil.Process(pid)
                            pname = proc.name().lower()
                            context["process_name"] = pname
                            context["friendly_name"] = FRIENDLY_APP_NAMES.get(
                                pname, pname.replace('.exe', '').capitalize()
                            )
                        except Exception:
                            pass

                    try:
                        rect = win32gui.GetWindowRect(hwnd)
                        if rect and rect[2] > rect[0] and rect[3] > rect[1]:
                            context["rect"] = {
                                "left": rect[0], "top": rect[1],
                                "width": rect[2] - rect[0], "height": rect[3] - rect[1]
                            }
                    except Exception:
                        pass

                    context["is_valid"] = True
        except Exception:
            pass

    # ---- Tier 2: Window enumeration via GetWindow chain ----
    if not context["is_valid"] and HAS_WIN32:
        windows = _enumerate_visible_windows()
        if windows:
            # Pick the first (topmost in Z-order) window that is a known GUI app
            best = None
            for w in windows:
                pname = w.get("process_name", "")
                if pname in GUI_APP_EXECUTABLES:
                    best = w
                    break
            if not best and windows:
                best = windows[0]  # Fallback to first visible window

            if best:
                context["title"] = best.get("title", "")
                context["process_name"] = best.get("process_name", "")
                context["friendly_name"] = best.get("friendly_name", "Desktop Application")
                context["hwnd"] = best.get("hwnd", 0)
                context["is_valid"] = True

    # ---- Tier 3: psutil + PowerShell fallback ----
    if not context["is_valid"]:
        # Try PowerShell window title extraction
        ps_windows = _get_window_titles_via_powershell()
        if ps_windows:
            # Pick the most relevant (first known GUI app or first titled window)
            best = None
            for w in ps_windows:
                if w["process_name"] in GUI_APP_EXECUTABLES:
                    best = w
                    break
            if not best:
                best = ps_windows[0]

            if best:
                context["title"] = best.get("title", "")
                context["process_name"] = best.get("process_name", "")
                context["friendly_name"] = best.get("friendly_name", "Desktop Application")
                context["is_valid"] = True

        # If still no window title, at least detect running GUI apps
        if not context["is_valid"]:
            gui_apps = _get_running_gui_apps()
            if gui_apps:
                # Pick the most likely foreground app (prefer code editors, browsers)
                priority_apps = ['code.exe', 'chrome.exe', 'msedge.exe', 'firefox.exe']
                best_app = None
                for prio in priority_apps:
                    for app in gui_apps:
                        if app["process_name"] == prio:
                            best_app = app
                            break
                    if best_app:
                        break
                if not best_app:
                    best_app = gui_apps[0]

                context["process_name"] = best_app["process_name"]
                context["friendly_name"] = best_app["friendly_name"]
                if best_app.get("context_hint"):
                    context["title"] = best_app["context_hint"]
                context["is_valid"] = True
                context["running_apps"] = gui_apps

    # Always populate running apps list for richer LLM context
    if not context["running_apps"]:
        context["running_apps"] = _get_running_gui_apps()

    return context


def _is_image_black(img: 'Image.Image', threshold: float = 5.0) -> bool:
    """Check if a captured image is effectively all-black (GPU compositing failure)."""
    try:
        stat = ImageStat.Stat(img)
        mean_brightness = statistics.mean(stat.mean)
        return mean_brightness < threshold
    except Exception:
        return True


def capture_screen_snapshot(active_window_only: bool = False, max_width: int = 1024) -> Optional[str]:
    """
    Captures a lightweight visual screenshot with multi-tier fallback.
    Tier 1: PIL ImageGrab.grab() (standard GDI)
    Tier 2: python-mss (alternative GDI path)
    Tier 3: Returns None if all methods produce black images (GPU compositing block)

    Detects black screenshots and returns None instead of sending useless black images
    to the LLM (which causes it to hallucinate about an "empty/blank screen").

    Returns base64 JPEG string or None.
    """
    if not HAS_PIL:
        return None

    # Set DPI awareness before any capture
    _set_dpi_awareness()

    captured_img = None

    # ---- Tier 1: PIL ImageGrab ----
    try:
        bbox = None
        if active_window_only and HAS_WIN32:
            win_ctx = get_active_window_context()
            if win_ctx.get("rect"):
                r = win_ctx["rect"]
                if r["width"] > 80 and r["height"] > 80:
                    bbox = (r["left"], r["top"], r["left"] + r["width"], r["top"] + r["height"])

        try:
            img = ImageGrab.grab(bbox=bbox)
        except Exception:
            img = ImageGrab.grab()

        if img is not None:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            if not _is_image_black(img):
                captured_img = img
    except Exception:
        pass

    # ---- Tier 2: python-mss ----
    if captured_img is None and HAS_MSS:
        try:
            with mss_module.MSS() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(monitor)
                img = Image.frombytes('RGB', (shot.width, shot.height), shot.rgb)
                if not _is_image_black(img):
                    captured_img = img
        except Exception:
            pass

    # ---- If still no valid capture, return None (don't send black image) ----
    if captured_img is None:
        return None

    # Downscale proportionally if wider than max_width
    w, h = captured_img.size
    if w > max_width:
        new_h = max(1, int(h * (max_width / float(w))))
        captured_img = captured_img.resize((max_width, new_h), Image.Resampling.LANCZOS)

    # Compress to in-memory JPEG bytes
    buf = io.BytesIO()
    captured_img.save(buf, format='JPEG', quality=75, optimize=True)
    img_bytes = buf.getvalue()

    return base64.b64encode(img_bytes).decode('utf-8')


def get_clipboard_text_snippet(max_length: int = 800) -> str:
    """Safely retrieves current text in Windows clipboard with credential masking."""
    try:
        import tkinter as tk
        r = tk.Tk()
        r.withdraw()
        clip = r.clipboard_get()
        r.destroy()
        if isinstance(clip, str):
            clean = ' '.join(clip.split()).strip()
            # Security guardrail: Redact API keys, tokens, or private secrets
            clean = re.sub(
                r'\b(?:sk-[a-zA-Z0-9\-_]{16,}|ghp_[a-zA-Z0-9]{16,}|Bearer\s+[a-zA-Z0-9\.\-_]{16,})\b',
                '[REDACTED_SECRET]', clean
            )
            return clean[:max_length]
    except Exception:
        pass
    return ""


def collect_screen_context() -> Dict[str, Any]:
    """
    Collects a unified, comprehensive screen context payload combining
    window metadata, running app detection, clipboard text, and visual snapshot.

    When screenshot capture fails (GPU compositing block), this function enriches
    the context with detailed process metadata so the LLM can still provide
    intelligent answers based on what apps are running and their window titles.
    """
    win_ctx = get_active_window_context()
    b64_image = capture_screen_snapshot(active_window_only=False, max_width=960)
    clip_snippet = get_clipboard_text_snippet()

    # Build a summary of all running GUI apps for richer context
    running_apps = win_ctx.get("running_apps", [])
    running_apps_summary = ""
    if running_apps:
        app_names = [app["friendly_name"] for app in running_apps]
        running_apps_summary = ", ".join(app_names)

    return {
        "app_name": win_ctx.get("friendly_name", "Desktop Application"),
        "process_name": win_ctx.get("process_name", ""),
        "window_title": win_ctx.get("title", ""),
        "window_bounds": win_ctx.get("rect"),
        "clipboard_snippet": clip_snippet,
        "has_image": bool(b64_image),
        "image_base64": b64_image,
        "running_apps": running_apps_summary,
        "screenshot_available": bool(b64_image),
    }

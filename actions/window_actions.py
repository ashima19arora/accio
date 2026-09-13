"""
Accio Window Actions Module - Native OS Window & Virtual Desktop Management
===========================================================================
WHAT THIS FILE DOES (Simple English):
  This module controls your computer's visual workspace. It lets users close active windows,
  minimize, maximize, show the desktop, switch between running apps (`Alt+Tab`), snap windows
  to the left or right half of the screen, open Task View, and switch between virtual desktops
  using simple spoken voice commands in English or Hindi.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - pyautogui:
      * What it does: Sends native operating system shortcut hotkeys (`Win+Down`, `Win+Up`,
        `Win+Left`, `Win+Tab`, `Alt+Tab`, `Alt+F4`).
      * Why we use it: Directly triggers Windows shell window management commands without needing
        complex Windows C++ win32 APIs.
"""

import time
import pyautogui
from .feedback import speak, notify

pyautogui.FAILSAFE = False

def close_window(lang: str = 'en') -> bool:
    """
    Closes the currently active window using Alt+F4.
    """
    notify("Closing active window")
    speak("विंडो बंद कर दी है" if lang == 'hi' else "Closing window", lang=lang)
    pyautogui.hotkey('alt', 'f4')
    return True

def minimize_window(lang: str = 'en') -> bool:
    """
    Minimizes the currently active window.
    """
    notify("Minimizing window")
    speak("विंडो मिनिमाइज़ कर दी है" if lang == 'hi' else "Minimizing", lang=lang)
    pyautogui.hotkey('win', 'down')
    return True

def maximize_window(lang: str = 'en') -> bool:
    """
    Maximizes or restores the active window.
    """
    notify("Maximizing window")
    speak("विंडो मैक्सिमाइज़ कर दी है" if lang == 'hi' else "Maximizing", lang=lang)
    pyautogui.hotkey('win', 'up')
    return True

def show_desktop(lang: str = 'en') -> bool:
    """
    Toggles showing the desktop (minimizes all windows).
    """
    notify("Showing desktop")
    speak("डेस्कटॉप दिखा रहा हूँ" if lang == 'hi' else "Showing desktop", lang=lang)
    pyautogui.hotkey('win', 'd')
    return True

def switch_window() -> bool:
    """
    Switches to the next application window via Alt+Tab.
    """
    notify("Switching window")
    speak("Switching window")
    pyautogui.keyDown('alt')
    pyautogui.press('tab')
    time.sleep(0.1)
    pyautogui.keyUp('alt')
    return True

def snap_window(direction: str = 'left', lang: str = 'en') -> bool:
    """
    Snaps active window to the left or right side of the screen.
    """
    clean_dir = direction.lower().strip()
    if clean_dir in ('left', 'right'):
        notify(f"Snapping window {clean_dir}")
        speak(f"विंडो को {clean_dir} में स्नैप कर रहा हूँ" if lang == 'hi' else f"Snapping window {clean_dir}", lang=lang)
        pyautogui.hotkey('win', clean_dir)
        return True
    return False

def snap_left(lang: str = 'en') -> bool:
    """
    Snaps active window to the left half of the screen.
    """
    return snap_window('left', lang=lang)

def snap_right(lang: str = 'en') -> bool:
    """
    Snaps active window to the right half of the screen.
    """
    return snap_window('right', lang=lang)

def open_task_view(lang: str = 'en') -> bool:
    """
    Opens Windows Task View (Win+Tab).
    """
    notify("Opening Windows Task View (Win+Tab)")
    speak("टास्क व्यू खोल रहा हूँ" if lang == 'hi' else "Opening task view", lang=lang)
    pyautogui.hotkey('win', 'tab')
    return True

def switch_desktop(direction: str = 'next', lang: str = 'en') -> bool:
    """
    Switches virtual desktops (Win+Ctrl+Left/Right).
    """
    is_next = direction.lower().strip() in ('next', 'right', 'forward')
    arrow = 'right' if is_next else 'left'
    notify(f"Switching virtual desktop ({'next' if is_next else 'previous'})")
    speak("वर्चुअल डेस्कटॉप बदल रहा हूँ" if lang == 'hi' else "Switching virtual desktop", lang=lang)
    pyautogui.hotkey('win', 'ctrl', arrow)
    return True

def new_desktop(lang: str = 'en') -> bool:
    """
    Creates a new virtual desktop (Win+Ctrl+D).
    """
    notify("Creating new virtual desktop")
    speak("नया वर्चुअल डेस्कटॉप बना रहा हूँ" if lang == 'hi' else "Creating new virtual desktop", lang=lang)
    pyautogui.hotkey('win', 'ctrl', 'd')
    return True

def close_desktop(lang: str = 'en') -> bool:
    """
    Closes the current virtual desktop (Win+Ctrl+F4).
    """
    notify("Closing current virtual desktop")
    speak("वर्चुअल डेस्कटॉप बंद कर रहा हूँ" if lang == 'hi' else "Closing virtual desktop", lang=lang)
    pyautogui.hotkey('win', 'ctrl', 'f4')
    return True

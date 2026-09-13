"""
Accio Form Actions Module - Hands-Free Form Filling & Accessibility Navigation
==============================================================================
WHAT THIS FILE DOES (Simple English):
  This is one of the most important accessibility modules in Accio. For individuals with
  low motor control or visual impairments, filling out online government portals, job
  applications, or survey forms with a physical keyboard and mouse is difficult or impossible.
  This module allows users to speak commands like "press tab", "next field", "fill field with John",
  "toggle checkbox", "select all", "copy", "paste", "undo", and "submit form", giving them full
  digital independence.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - pyautogui:
      * What it does: Automates low-level keyboard strokes (`Tab`, `Shift+Tab`, `Space`, `Enter`).
      * Why we use it: Provides universal hardware-level input across any browser, web form, or desktop app.
  - pyperclip (Clipboard Injection):
      * What it does: Cross-platform clipboard text copying and pasting.
      * Why we use it: When filling text into fields, pasting from clipboard via `Ctrl+V` is 100x faster
        and more reliable than typing individual keystrokes, completely preventing dropped characters.
"""

import time
import pyautogui
from .feedback import speak, notify

pyautogui.FAILSAFE = False

def press_tab(steps: int = 1, lang: str = 'en') -> bool:
    """
    Navigates forward through form fields using Tab.
    """
    notify(f"Moving to next field (Tab x{steps})")
    speak(f"अगला फील्ड" if lang == 'hi' else f"Next field", lang=lang)
    for _ in range(steps):
        pyautogui.press('tab')
        time.sleep(0.05)
    return True

def previous_field(steps: int = 1, lang: str = 'en') -> bool:
    """
    Navigates backward through form fields using Shift+Tab.
    """
    notify(f"Moving to previous field (Shift+Tab x{steps})")
    speak(f"पिछला फील्ड" if lang == 'hi' else f"Previous field", lang=lang)
    for _ in range(steps):
        pyautogui.hotkey('shift', 'tab')
        time.sleep(0.05)
    return True

def press_enter(lang: str = 'en') -> bool:
    """
    Submits a form or triggers the focused button using Enter.
    """
    notify("Submitting form / Pressing Enter")
    speak("फॉर्म सबमिट कर रहा हूँ" if lang == 'hi' else "Submitting form", lang=lang)
    pyautogui.press('enter')
    return True

def press_space(lang: str = 'en') -> bool:
    """
    Toggles a checkbox or selects an option using Space.
    """
    notify("Toggling checkbox / Space")
    speak("चेकबॉक्स सेलेक्ट कर रहा हूँ" if lang == 'hi' else "Selecting option", lang=lang)
    pyautogui.press('space')
    return True

def select_all(lang: str = 'en') -> bool:
    """
    Selects all text in the active input field or document using Ctrl+A.
    """
    notify("Selecting all text (Ctrl+A)")
    speak("सभी टेक्स्ट सेलेक्ट कर लिया" if lang == 'hi' else "Selected all", lang=lang)
    pyautogui.hotkey('ctrl', 'a')
    return True

def clear_field(lang: str = 'en') -> bool:
    """
    Clears the active input field by selecting all and deleting.
    """
    notify("Clearing field")
    speak("फील्ड खाली कर दी है" if lang == 'hi' else "Cleared field", lang=lang)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.05)
    pyautogui.press('backspace')
    return True

def copy_text(lang: str = 'en') -> bool:
    """
    Copies selected text to the clipboard using Ctrl+C.
    """
    notify("Copying to clipboard (Ctrl+C)")
    speak("कॉपी कर लिया" if lang == 'hi' else "Copied", lang=lang)
    pyautogui.hotkey('ctrl', 'c')
    return True

def paste_text(lang: str = 'en') -> bool:
    """
    Pastes text from the clipboard into the active field using Ctrl+V.
    """
    notify("Pasting from clipboard (Ctrl+V)")
    speak("पेस्ट कर दिया" if lang == 'hi' else "Pasted", lang=lang)
    pyautogui.hotkey('ctrl', 'v')
    return True

def undo_action(lang: str = 'en') -> bool:
    """
    Undoes the last text edit or action using Ctrl+Z.
    """
    notify("Undoing last action (Ctrl+Z)")
    speak("अनडू कर दिया" if lang == 'hi' else "Undone", lang=lang)
    pyautogui.hotkey('ctrl', 'z')
    return True

def fill_field(text: str, press_tab_after: bool = False, press_enter_after: bool = False, lang: str = 'en') -> bool:
    """
    Fills text into the active field via clipboard injection and optionally navigates to next field.
    """
    clean_text = text.strip()
    if not clean_text:
        return False

    notify(f"Filling field with: '{clean_text}'")
    try:
        import pyperclip
        pyperclip.copy(clean_text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
    except Exception:
        pyautogui.write(clean_text, interval=0.02)

    if press_tab_after:
        time.sleep(0.1)
        pyautogui.press('tab')
    elif press_enter_after:
        time.sleep(0.1)
        pyautogui.press('enter')

    speak(f"'{clean_text}' दर्ज कर दिया" if lang == 'hi' else f"Entered text", lang=lang)
    return True

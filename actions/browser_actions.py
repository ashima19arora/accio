"""
Accio Browser Actions Module - Web & Browser Automation
========================================================
WHAT THIS FILE DOES (Simple English):
  This module gives users full hands-free control over their web browser (Chrome, Edge, Firefox).
  It lets users open websites, search Google, open and close tabs, scroll up and down web pages,
  zoom in and out, find words on the page (`Ctrl+F`), open downloads and history, and bookmark pages,
  all without touching the mouse or keyboard.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - webbrowser:
      * What it does: Native Python standard library interface to launch URLs in the default browser.
      * Why we use it: Works seamlessly across all Windows browsers without requiring webdriver binaries (like ChromeDriver).
  - pyautogui:
      * What it does: Cross-platform programmatic keyboard shortcut automation.
      * Why we use it: Executes universal browser shortcuts (`Ctrl+T` new tab, `Ctrl+W` close tab,
        `PageDown` scroll down, `Ctrl +` zoom in, `Ctrl+F` find on page) with instantaneous response.
  - urllib.parse:
      * What it does: URL encoding and decoding.
      * Why we use it: Safely encodes search queries so special characters never cause browser errors.
"""

import time
import urllib.parse
import webbrowser
import pyautogui
from .feedback import speak, notify

# Disable fail-safe on corner cursor for pure keyboard shortcuts
pyautogui.FAILSAFE = False

COMMON_SITES = {
    'google': 'https://www.google.com',
    'youtube': 'https://www.youtube.com',
    'github': 'https://www.github.com',
    'gmail': 'https://mail.google.com',
    'reddit': 'https://www.reddit.com',
    'wikipedia': 'https://www.wikipedia.org',
    'twitter': 'https://www.x.com',
    'x': 'https://www.x.com',
    'linkedin': 'https://www.linkedin.com',
    'chatgpt': 'https://chatgpt.com',
    'netflix': 'https://www.netflix.com',
    'amazon': 'https://www.amazon.com',
    'maps': 'https://maps.google.com',
    'news': 'https://news.google.com',
    'whatsapp': 'https://web.whatsapp.com',
    'whatsapp web': 'https://web.whatsapp.com',
}

def search_web(query: str, engine: str = 'google', lang: str = 'en') -> bool:
    """
    Performs a web search in the user's default browser after sanitizing input.
    """
    from .security.sanitizer import sanitize_search_query
    ok, clean_query, reason = sanitize_search_query(query)
    if not ok:
        notify(f"Search blocked: {reason}", success=False)
        return False

    encoded = urllib.parse.quote_plus(clean_query)
    url = f"https://www.google.com/search?q={encoded}"
    
    notify(f"Searching web for: '{clean_query}'")
    if lang == 'hi':
        speak(f"{clean_query} के बारे में सर्च कर रहा हूँ", lang=lang)
    else:
        speak(f"Searching for {clean_query}", lang=lang)
    webbrowser.open(url)
    return True

def open_url(target: str, lang: str = 'en') -> bool:
    """
    Opens a website by common name or direct URL after security validation.
    """
    from .security.sanitizer import sanitize_url
    target_clean = target.strip().lower()
    if not target_clean:
        return False

    # Check common shortcuts
    if target_clean in COMMON_SITES:
        url = COMMON_SITES[target_clean]
        site_name = target_clean.capitalize()
    elif '.' in target_clean and not target_clean.startswith(('http://', 'https://')):
        url = f"https://{target_clean}"
        site_name = target_clean
    elif target_clean.startswith(('http://', 'https://')):
        url = target_clean
        site_name = target_clean
    else:
        # Fallback to web search if target is not a recognized URL
        return search_web(target, lang=lang)

    # Validate against security policy (block file://, loopback, private IP, .exe downloads)
    is_safe, safe_url, reason = sanitize_url(url)
    if not is_safe:
        notify(f"Security Alert: {reason}", success=False)
        speak("सुरक्षा नीति के तहत नेविगेशन ब्लॉक किया गया है।" if lang == 'hi' else "Navigation blocked by security policy.", lang=lang)
        return False

    notify(f"Opening website: {safe_url}")
    speak(f"{site_name} खोल रहा हूँ" if lang == 'hi' else f"Opening {site_name}", lang=lang)
    webbrowser.open(safe_url)
    return True

def new_tab(url: str = None) -> bool:
    """
    Opens a new tab in the active browser window with optional sanitized URL.
    """
    notify("Opening new tab")
    speak("Opening new tab")
    pyautogui.hotkey('ctrl', 't')
    if url:
        from .security.sanitizer import sanitize_url
        is_safe, safe_url, _ = sanitize_url(url)
        if is_safe:
            time.sleep(0.3)
            pyautogui.write(safe_url, interval=0.02)
            pyautogui.press('enter')
    return True

def close_tab() -> bool:
    """
    Closes the currently active browser tab.
    """
    notify("Closing current tab")
    speak("Closing tab")
    pyautogui.hotkey('ctrl', 'w')
    return True

def switch_tab(direction: str = 'next') -> bool:
    """
    Switches to the next or previous browser tab.
    """
    if direction == 'previous' or direction == 'prev':
        notify("Switching to previous tab")
        pyautogui.hotkey('ctrl', 'shift', 'tab')
    else:
        notify("Switching to next tab")
        pyautogui.hotkey('ctrl', 'tab')
    return True

def refresh_page() -> bool:
    """
    Reloads the active browser page.
    """
    notify("Refreshing page")
    speak("Refreshing")
    pyautogui.hotkey('ctrl', 'r')
    return True

def reopen_tab() -> bool:
    """
    Reopens the last closed browser tab.
    """
    notify("Reopening last closed tab")
    speak("Reopening tab")
    pyautogui.hotkey('ctrl', 'shift', 't')
    return True

def scroll_down(steps: int = 1, lang: str = 'en') -> bool:
    """
    Scrolls down the active web page.
    """
    notify(f"Scrolling down ({steps} steps)")
    speak("नीचे स्क्रॉल कर रहा हूँ" if lang == 'hi' else "Scrolling down", lang=lang)
    for _ in range(steps):
        pyautogui.press('pagedown')
        time.sleep(0.08)
    return True

def scroll_up(steps: int = 1, lang: str = 'en') -> bool:
    """
    Scrolls up the active web page.
    """
    notify(f"Scrolling up ({steps} steps)")
    speak("ऊपर स्क्रॉल कर रहा हूँ" if lang == 'hi' else "Scrolling up", lang=lang)
    for _ in range(steps):
        pyautogui.press('pageup')
        time.sleep(0.08)
    return True

def scroll_top(lang: str = 'en') -> bool:
    """
    Scrolls to the top of the active page.
    """
    notify("Scrolling to top of page")
    speak("पेज के सबसे ऊपर जा रहा हूँ" if lang == 'hi' else "Scrolling to top", lang=lang)
    pyautogui.press('home')
    return True

def scroll_bottom(lang: str = 'en') -> bool:
    """
    Scrolls to the bottom of the active page.
    """
    notify("Scrolling to bottom of page")
    speak("पेज के सबसे नीचे जा रहा हूँ" if lang == 'hi' else "Scrolling to bottom", lang=lang)
    pyautogui.press('end')
    return True

def zoom_in(lang: str = 'en') -> bool:
    """
    Zooms into the active web page.
    """
    notify("Zooming in (Ctrl +)")
    speak("ज़ूम इन कर रहा हूँ" if lang == 'hi' else "Zooming in", lang=lang)
    pyautogui.hotkey('ctrl', '=')
    return True

def zoom_out(lang: str = 'en') -> bool:
    """
    Zooms out of the active web page.
    """
    notify("Zooming out (Ctrl -)")
    speak("ज़ूम आउट कर रहा हूँ" if lang == 'hi' else "Zooming out", lang=lang)
    pyautogui.hotkey('ctrl', '-')
    return True

def reset_zoom(lang: str = 'en') -> bool:
    """
    Resets web page zoom to default 100%.
    """
    notify("Resetting zoom (Ctrl 0)")
    speak("ज़ूम रीसेट कर दिया" if lang == 'hi' else "Zoom reset", lang=lang)
    pyautogui.hotkey('ctrl', '0')
    return True

def go_back(lang: str = 'en') -> bool:
    """
    Navigates to the previous page in history.
    """
    notify("Going back in history")
    speak("पीछे जा रहा हूँ" if lang == 'hi' else "Going back", lang=lang)
    pyautogui.hotkey('alt', 'left')
    return True

def go_forward(lang: str = 'en') -> bool:
    """
    Navigates forward in history.
    """
    notify("Going forward in history")
    speak("आगे जा रहा हूँ" if lang == 'hi' else "Going forward", lang=lang)
    pyautogui.hotkey('alt', 'right')
    return True

def open_history(lang: str = 'en') -> bool:
    """
    Opens the browser history page.
    """
    notify("Opening browser history")
    speak("ब्राउज़र हिस्ट्री खोल रहा हूँ" if lang == 'hi' else "Opening history", lang=lang)
    pyautogui.hotkey('ctrl', 'h')
    return True

def open_downloads(lang: str = 'en') -> bool:
    """
    Opens the browser downloads page.
    """
    notify("Opening browser downloads")
    speak("डाउनलोड्स खोल रहा हूँ" if lang == 'hi' else "Opening downloads", lang=lang)
    pyautogui.hotkey('ctrl', 'j')
    return True

def bookmark_page(lang: str = 'en') -> bool:
    """
    Bookmarks current page and hits enter to save.
    """
    notify("Bookmarking active page")
    speak("पेज बुकमार्क कर रहा हूँ" if lang == 'hi' else "Bookmarking page", lang=lang)
    pyautogui.hotkey('ctrl', 'd')
    time.sleep(0.3)
    pyautogui.press('enter')
    return True

def toggle_fullscreen(lang: str = 'en') -> bool:
    """
    Toggles fullscreen mode in the browser (F11).
    """
    notify("Toggling fullscreen")
    speak("फुलस्क्रीन टॉगल कर रहा हूँ" if lang == 'hi' else "Toggling fullscreen", lang=lang)
    pyautogui.press('f11')
    return True

def find_on_page(query: str, lang: str = 'en') -> bool:
    """
    Opens browser Find on Page (Ctrl+F) and searches for the target string.
    """
    clean_query = query.strip()
    if not clean_query:
        return False

    notify(f"Finding on page: '{clean_query}'")
    speak(f"पेज पर खोज रहा हूँ: {clean_query}" if lang == 'hi' else f"Searching page for {clean_query}", lang=lang)
    pyautogui.hotkey('ctrl', 'f')
    time.sleep(0.25)
    try:
        import pyperclip
        pyperclip.copy(clean_query)
        pyautogui.hotkey('ctrl', 'v')
    except Exception:
        pyautogui.write(clean_query, interval=0.02)
    pyautogui.press('enter')
    return True

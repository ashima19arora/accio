"""
Accio File Actions Module - Safe Hands-Free File & Note Creation
================================================================
WHAT THIS FILE DOES (Simple English):
  This module allows users with low motor control to create text files, notes, and documents
  directly on their Desktop or Documents folder using speech (e.g., "create a txt file on desktop named Myank Important").
  It creates the file safely, ensures no executable scripts can be created, avoids overwriting
  existing files, speaks an audio confirmation, and opens the new file in Notepad so the user
  can immediately view and use it.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - os & pathlib:
      * What it does: Native operating system path and directory resolution.
      * Why we use it: Automatically resolves active Windows Desktop locations (including OneDrive Desktop).
  - os.startfile:
      * What it does: Native Windows shell document launcher.
      * Why we use it: Immediately pops open the newly created text file in the default text editor (Notepad).
"""

import os
import re
from typing import Tuple
from .feedback import speak, notify

FORBIDDEN_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.ps1', '.vbs', '.msi', '.scr',
    '.jar', '.iso', '.dll', '.reg', '.com', '.pif', '.hta', '.py', '.sh'
}

def get_target_directory(location: str = "desktop") -> str:
    """
    Resolves the user's Desktop or Documents directory, taking OneDrive into account.
    """
    home = os.path.expanduser("~")
    clean_loc = location.lower().strip()

    if clean_loc in ("documents", "docs", "doc"):
        onedrive_docs = os.path.join(home, "OneDrive", "Documents")
        standard_docs = os.path.join(home, "Documents")
        if os.path.exists(onedrive_docs):
            return onedrive_docs
        if os.path.exists(standard_docs):
            return standard_docs
        return home

    # Default: Desktop
    onedrive_desktop = os.path.join(home, "OneDrive", "Desktop")
    standard_desktop = os.path.join(home, "Desktop")
    if os.path.exists(onedrive_desktop):
        return onedrive_desktop
    if os.path.exists(standard_desktop):
        return standard_desktop
    return home

def sanitize_file_name(raw_name: str) -> str:
    """
    Cleans filename to conform to Windows filesystem rules and enforces safe text extensions.
    """
    clean = raw_name.strip()
    # Strip phrases like "named ", "called "
    clean = re.sub(r'^(?:named|called)\s+', '', clean, flags=re.IGNORECASE).strip()
    # Strip illegal Windows filename characters
    clean = re.sub(r'[\\/:*?"<>|]+', '', clean).strip()

    if not clean:
        clean = "New Note"

    # Inspect extension
    base, ext = os.path.splitext(clean)
    ext_lower = ext.lower()

    if ext_lower in FORBIDDEN_EXTENSIONS:
        # Neutralize forbidden executable extension
        clean = f"{base}_note.txt"
    elif not ext:
        # Default to standard text file
        clean = f"{clean}.txt"
    elif ext_lower not in ('.txt', '.note', '.md', '.log'):
        clean = f"{clean}.txt"

    return clean

def create_file(
    filename: str,
    content: str = "",
    location: str = "desktop",
    open_after: bool = True,
    lang: str = 'en'
) -> bool:
    """
    Creates a new safe text file or note on the user's Desktop or Documents folder.
    """
    safe_name = sanitize_file_name(filename)
    target_dir = get_target_directory(location)
    os.makedirs(target_dir, exist_ok=True)

    base, ext = os.path.splitext(safe_name)
    filepath = os.path.join(target_dir, safe_name)

    # Avoid overwriting existing files: append (1), (2), etc.
    counter = 1
    while os.path.exists(filepath):
        safe_name = f"{base} ({counter}){ext}"
        filepath = os.path.join(target_dir, safe_name)
        counter += 1

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            if content:
                f.write(content)
            else:
                f.write("")

        loc_label = "Desktop" if "desktop" in location.lower() else "Documents"
        notify(f"Created file '{safe_name}' on {loc_label}")

        if lang == 'hi':
            speak(f"डेस्कटॉप पर {safe_name} फाइल बना दी गई है।", lang=lang)
        else:
            speak(f"Created {safe_name} on your {loc_label}.", lang=lang)

        # Open in Notepad so the user sees immediate visual confirmation
        if open_after and hasattr(os, 'startfile'):
            try:
                os.startfile(filepath)
            except Exception:
                pass

        return True
    except Exception as e:
        notify(f"Failed to create file: {e}", success=False)
        return False

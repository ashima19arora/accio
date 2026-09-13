"""
Accio Native Actions Package - Public API & Automation Gateway
==============================================================
WHAT THIS FILE DOES (Simple English):
  This is the main "front door" of the actions package. When the assistant hears your
  speech, it calls `actions.execute_command(text)`. This file brings together all the
  individual action tools—browser controls, form filling, window management, system diagnostics,
  instant Q&A, and bilingual speech—into one clean, unified interface.

GREAT TECH & PACKAGES USED ACROSS THIS PACKAGE:
  - pyautogui & pyperclip: Universal keyboard, mouse, and clipboard automation across all Windows apps.
  - psutil: Hardware status inspection (RAM, CPU, Battery charge).
  - requests: Fast instant knowledge retrieval from Wikipedia REST and DuckDuckGo APIs.
  - pyttsx3 & gTTS: Dual-engine Text-to-Speech for fluent English and authentic Hindi voice feedback.
"""

from .registry import execute_command, ActionResult, INTENT_HANDLERS
from .intent_parser import parse_intent, Intent
from .feedback import speak, notify, wait_until_speech_finishes, is_speaking, notify_desktop_orb
from .voice_bridge import start_voice_bridge
from . import browser_actions
from . import window_actions
from . import system_actions
from . import form_actions
from . import knowledge_actions
from . import file_actions
from . import voice_bridge

__all__ = [
    "execute_command",
    "parse_intent",
    "ActionResult",
    "INTENT_HANDLERS",
    "speak",
    "notify",
    "wait_until_speech_finishes",
    "is_speaking",
    "notify_desktop_orb",
    "start_voice_bridge",
    "voice_bridge",
    "browser_actions",
    "window_actions",
    "system_actions",
    "form_actions",
    "knowledge_actions",
    "file_actions",
]

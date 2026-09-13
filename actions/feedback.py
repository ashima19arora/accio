"""
Accio Feedback Module - Auditory & Visual Feedback System
=========================================================
WHAT THIS FILE DOES (Simple English):
  This file is the "voice" and "screen announcer" of Accio. Whenever Accio completes
  a task, needs to answer a question, or warns the user, this module speaks the answer
  out loud through the computer speakers and prints a clear message on the screen.
  It speaks in both English and Hindi naturally.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - pyttsx3:
      * What it does: Offline Text-to-Speech synthesizer using native Windows SAPI5 voices.
      * Why we use it: Works 100% offline with zero latency and zero internet requirement.
      * Benefit: Essential for visually impaired users who need instantaneous spoken responses.
  - gTTS (Google Text-to-Speech):
      * What it does: Converts Hindi and Indian English text into natural, human-sounding speech.
      * Why we use it: Standard Windows English TTS voices often pronounce Hindi words incorrectly.
        gTTS provides authentic, fluent Hindi pronunciation.
  - pygame.mixer:
      * What it does: Low-latency audio playback engine.
      * Why we use it: Plays gTTS audio directly from memory (RAM) via io.BytesIO without ever
        creating temporary MP3 files on disk. This keeps the disk clean and playback fast.
  - threading.Lock:
      * What it does: Thread synchronization lock.
      * Why we use it: Prevents multiple speech threads from talking over each other simultaneously.
"""

import sys
import threading
import time
import io
import re

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

_tts_lock = threading.Lock()
_engine = None
_tts_available = True

def clean_for_speech(text: str) -> str:
    """
    Cleans text so Text-to-Speech speaks naturally without pronouncing code or markdown artifacts.
    Strips markdown formatting, URLs, asterisks, brackets, and extra spaces.
    """
    if not text:
        return ""
    # Replace markdown links [title](url) with just title
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    # Remove markdown styling: bold, italic, headers, backticks
    cleaned = re.sub(r'[\*_#`~]', '', cleaned)
    # Remove bracketed citation tags like [1], [2], [citation needed]
    cleaned = re.sub(r'\[\d+\]', '', cleaned)
    # Remove phonetic pronunciation guides inside slashes like /.../
    cleaned = re.sub(r'\/[^\/]{2,}\/', '', cleaned)
    # Collapse multiple whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def _get_tts_engine():
    global _engine, _tts_available
    if not _tts_available:
        return None
    if _engine is None:
        try:
            import pyttsx3
            _engine = pyttsx3.init()
            # Configure a calm, natural speech rate (approx 170 words per minute)
            _engine.setProperty('rate', 170)
            voices = _engine.getProperty('voices')
            if voices:
                # Prefer Indian English voice if installed on Windows (Heera, Ravi, Neerja, Veena),
                # otherwise standard natural voice (Zira, David)
                selected_voice = None
                for voice in voices:
                    v_name = voice.name.lower()
                    if any(name in v_name for name in ['heera', 'ravi', 'neerja', 'veena', 'india']):
                        selected_voice = voice.id
                        break
                    if 'zira' in v_name:
                        selected_voice = voice.id
                if selected_voice:
                    _engine.setProperty('voice', selected_voice)
        except Exception as e:
            print(f"[Feedback] Local TTS engine initialization skipped: {e}")
            _tts_available = False
            _engine = None
    return _engine

def _play_gtts_audio(text: str, lang: str = 'hi') -> bool:
    """
    Synthesizes and plays back natural audio in memory using gTTS and pygame.
    Used for fluent Hindi and accented Indian speech.
    """
    try:
        from gtts import gTTS
        import pygame

        fp = io.BytesIO()
        tld = 'co.in' if lang == 'en' else 'com'
        tts = gTTS(text=text, lang=lang, tld=tld)
        tts.write_to_fp(fp)
        fp.seek(0)

        if not pygame.mixer.get_init():
            pygame.mixer.init()

        pygame.mixer.music.load(fp)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        return True
    except Exception as e:
        return False

_speaking_active = threading.Event()

def is_speaking() -> bool:
    """
    Returns True if Text-to-Speech audio is currently playing.
    """
    return _speaking_active.is_set() or _tts_lock.locked()

def wait_until_speech_finishes(timeout: float = 8.0) -> None:
    """
    Waits until speech audio finishes playing through speakers.
    Prevents the microphone from recording the computer's own voice (acoustic feedback).
    """
    start = time.time()
    time.sleep(0.08)
    while is_speaking() and (time.time() - start < timeout):
        time.sleep(0.05)
    # Brief buffer for acoustic room echo decay
    time.sleep(0.15)

import urllib.request
import urllib.parse

def notify_desktop_orb(state: str, text: str = "", message: str = ""):
    """Notify the floating desktop orb of voice activity, live transcription, and conversational feedback."""
    try:
        params = urllib.parse.urlencode({
            "state": state,
            "text": text[:100] if text else "",
            "message": message[:100] if message else "",
        })
        req = urllib.request.Request(
            f"http://127.0.0.1:48123/state?{params}",
            headers={"User-Agent": "AccioVoice/1.0"}
        )
        urllib.request.urlopen(req, timeout=0.15)
    except Exception:
        pass

def speak(text: str, lang: str = 'auto', asynchronous: bool = True):
    """
    Speaks the given text in English or Hindi based on language detection or parameter.
    By default runs asynchronously in a daemon thread so it doesn't block OS actions.
    """
    clean_spoken = clean_for_speech(text)
    if not clean_spoken:
        return

    # Auto-detect language if requested
    if lang == 'auto':
        from .languages import detect_language
        lang = detect_language(clean_spoken)

    try:
        print(f"\033[92m[Accio Voice ({lang.upper()})]\033[0m {clean_spoken}")
    except Exception:
        safe_text = clean_spoken.encode('ascii', errors='replace').decode('ascii')
        print(f"[Accio Voice ({lang.upper()})] {safe_text}")

    def _run():
        _speaking_active.set()
        notify_desktop_orb("speaking", message=clean_spoken)
        try:
            with _tts_lock:
                # 1. For Hindi, use gTTS for authentic native Hindi pronunciation
                if lang == 'hi':
                    success = _play_gtts_audio(clean_spoken, lang='hi')
                    if success:
                        return

                # 2. For English (or offline fallback), use local pyttsx3
                try:
                    engine = _get_tts_engine()
                    if engine is not None:
                        engine.say(clean_spoken)
                        engine.runAndWait()
                except Exception:
                    pass
        finally:
            _speaking_active.clear()
            notify_desktop_orb("idle")

    if asynchronous:
        t = threading.Thread(target=_run, daemon=True)
        t.start()
    else:
        _run()

def notify(message: str, success: bool = True):
    """
    Prints a formatted notification to the console.
    """
    color = "\033[96m" if success else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[Accio Action]{reset} {message}")

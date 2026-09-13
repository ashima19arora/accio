"""
Accio Language & Multilingual Localization Module
=================================================
WHAT THIS FILE DOES (Simple English):
  This module allows Accio to seamlessly understand both English and Hindi/Hinglish.
  If you speak in English ("open YouTube"), Accio detects English and speaks back in English.
  If you speak in Hindi ("YouTube kholo" or "RAM kitna use ho raha hai"), Accio automatically
  detects Hindi and responds in natural Hindi.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - Lexical Token Classifier:
      * What it does: Matches words against a curated dictionary of Romanized Hindi/Hinglish tokens
        and Devanagari Unicode scripts (`\u0900-\u097F`).
      * Why we use it: Zero-latency language identification running locally without needing any
        heavy neural network models.
  - Localization Mapping Dictionary:
      * What it does: Stores authentic, culturally natural spoken phrases for both languages.
"""

import re
from typing import Dict, Any, Tuple

# Comprehensive lexicon of common Romanized Hindi / Hinglish tokens
HINDI_HINGLISH_WORDS = {
    # Question words & relative pronouns
    'kya', 'kyun', 'kaun', 'kaise', 'kahan', 'kab', 'kitna', 'kitni', 'kitne',
    'kisko', 'kiska', 'kiski', 'kiske', 'jaisa', 'jaise', 'jahan', 'jab',
    # Pronouns
    'main', 'mujhe', 'mera', 'meri', 'mere', 'hum', 'humein', 'hamara', 'hamari', 'hamare',
    'aap', 'aapko', 'aapka', 'aapki', 'aapke', 'tum', 'tumhe', 'tumhara', 'tumhari', 'tumhare',
    'ye', 'yeh', 'wo', 'woh', 'inhe', 'unhe', 'iska', 'iski', 'iske', 'uska', 'uski', 'uske',
    # Postpositions & particles
    'ke', 'ki', 'ka', 'ko', 'se', 'mein', 'me', 'par', 'pe', 'ne', 'bhi', 'to', 'toh',
    'aur', 'ya', 'lekin', 'parantu', 'magar', 'liye', 'baare', 'bare', 'sabse',
    # Verbs & Auxiliary
    'hai', 'hain', 'ho', 'hoon', 'hun', 'tha', 'thi', 'the', 'hoga', 'hogi', 'honge',
    'karo', 'karna', 'kariye', 'kijiye', 'karta', 'karti', 'karte',
    'kholo', 'khol', 'kholna', 'chalao', 'chala', 'chalaana',
    'batao', 'bata', 'bataiye', 'dikhao', 'dikhana', 'dekh', 'dekho',
    'lo', 'le', 'lena', 'liya', 'do', 'de', 'dena', 'diya',
    'raha', 'rahi', 'rahe', 'raho', 'suno', 'sunna', 'bolo', 'bolna',
    'dhoondo', 'khojo', 'badhao', 'kam', 'tez', 'dheeme', 'band', 'hatao',
    # Common Hindi conversational nouns / adjectives
    'samay', 'taareekh', 'aawaz', 'awaz', 'madad', 'sahayata', 'cheez', 'cheese', 'namaste', 'namaskar', 'alvida'
}

def detect_language(transcription: str) -> str:
    """
    Detects whether the transcription is Hindi/Hinglish or English.
    Returns: 'hi' or 'en'
    """
    if not transcription or not transcription.strip():
        return 'en'

    text = transcription.lower().strip()

    # 1. Direct Devanagari script detection
    if re.search(r'[\u0900-\u097F]', text):
        return 'hi'

    # 2. Tokenize and count Hindi/Hinglish word matches
    words = re.findall(r'\b[a-z]+\b', text)
    if not words:
        return 'en'

    hindi_match_count = sum(1 for w in words if w in HINDI_HINGLISH_WORDS)

    # If at least 2 Hindi tokens are present, or >= 25% of tokens match Hindi lexicon
    ratio = hindi_match_count / len(words)
    if hindi_match_count >= 2 or (hindi_match_count >= 1 and ratio >= 0.25):
        return 'hi'

    # Specific single-word Hindi greetings or commands
    if words and words[0] in {'namaste', 'namaskar', 'alvida', 'kholo', 'batao'}:
        return 'hi'

    return 'en'

def get_localized_message(intent: str, lang: str, **kwargs) -> str:
    """
    Returns a natural localized spoken message for a given intent and language ('en' or 'hi').
    """
    target = kwargs.get("target", "")
    query = kwargs.get("query", "")
    app_name = kwargs.get("app_name", "")

    if lang == 'hi':
        messages = {
            "GREETING": "नमस्ते! मैं ऐक्सियो हूँ, आपका डिजिटल वॉइस साथी। मैं वेब सर्च कर सकता हूँ, ऐप्स और विंडोज़ कंट्रोल कर सकता हूँ।",
            "SEARCH_WEB": f"{query} के बारे में सर्च कर रहा हूँ",
            "OPEN_WEBSITE": f"{target.capitalize()} खोल रहा हूँ",
            "OPEN_APP": f"{app_name.capitalize()} ओपन कर रहा हूँ",
            "BROWSER_NEW_TAB": "नया टैब खोल दिया है",
            "BROWSER_CLOSE_TAB": "टैब बंद कर दिया है",
            "BROWSER_SWITCH_TAB": "टैब बदल दिया है",
            "BROWSER_REFRESH": "पेज रीफ्रेश कर दिया है",
            "WINDOW_CLOSE": "विंडो बंद कर दी है",
            "WINDOW_MINIMIZE": "विंडो मिनिमाइज़ कर दी है",
            "WINDOW_MAXIMIZE": "विंडो मैक्सिमाइज़ कर दी है",
            "SHOW_DESKTOP": "डेस्कटॉप दिखा रहा हूँ",
            "VOLUME_UP": "आवाज़ बढ़ा दी गई है",
            "VOLUME_DOWN": "आवाज़ कम कर दी गई है",
            "VOLUME_MUTE": "आवाज़ म्यूट कर दी गई है",
            "SCREENSHOT": "स्क्रीनशॉट ले लिया गया है",
            "MEDIA_PLAY_PAUSE": "मीडिया प्ले पॉज़ कर दिया है",
            "LOCK_SCREEN": "कंप्यूटर लॉक कर दिया गया है",
            "EXIT_ASSISTANT": "अलविदा! ऐक्सियो वॉइस असिस्टेंट अब बंद हो रहा है।",
            "SECURITY_BLOCKED": "सुरक्षा चेतावनी: यह कमांड आपके सिस्टम की सुरक्षा के लिए प्रतिबंधित है।",
            "UNKNOWN": "मैंने आपकी बात सुनी, लेकिन मुझे समझ नहीं आया। आप 'यूट्यूब खोलो', 'सर्च करो', या 'रैम चेक करो' बोल सकते हैं।",
            "FORM_SUBMIT": "फॉर्म सबमिट कर दिया गया है",
            "SEND_MESSAGE": "संदेश भेज दिया गया है",
            "KNOWLEDGE_QUERY": f"{query} के बारे में जानकारी ढूंढ रहा हूँ"
        }
        return messages.get(intent, kwargs.get("fallback", "काम पूरा हो गया है।"))

    # Default English
    messages = {
        "GREETING": "Hello! I am Accio, your digital accessibility companion. I can search the web, manage windows, switch tabs, control volume, or check system stats.",
        "SEARCH_WEB": f"Searching for {query}",
        "OPEN_WEBSITE": f"Opening {target.capitalize()}",
        "OPEN_APP": f"Opening {app_name.capitalize()}",
        "BROWSER_NEW_TAB": "Opening new tab",
        "BROWSER_CLOSE_TAB": "Closing tab",
        "BROWSER_SWITCH_TAB": "Switching tab",
        "BROWSER_REFRESH": "Refreshing page",
        "WINDOW_CLOSE": "Closing active window",
        "WINDOW_MINIMIZE": "Minimizing window",
        "WINDOW_MAXIMIZE": "Maximizing window",
        "SHOW_DESKTOP": "Showing desktop",
        "VOLUME_UP": "Increasing volume",
        "VOLUME_DOWN": "Decreasing volume",
        "VOLUME_MUTE": "Toggling volume mute",
        "SCREENSHOT": "Taking screenshot",
        "MEDIA_PLAY_PAUSE": "Toggled media playback",
        "LOCK_SCREEN": "Locking computer",
        "EXIT_ASSISTANT": "Goodbye! Accio voice assistant is shutting down.",
        "SECURITY_BLOCKED": "Security Alert: That command is restricted to protect your system.",
        "UNKNOWN": "I heard you, but I'm not sure how to do that yet. Try saying search for, open, check RAM, or close window.",
        "FORM_SUBMIT": "Form submitted.",
        "SEND_MESSAGE": "Message sent.",
        "KNOWLEDGE_QUERY": f"Searching knowledge base for {query}."
    }
    return messages.get(intent, kwargs.get("fallback", "Action completed."))

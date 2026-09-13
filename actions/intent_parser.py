"""
Accio Intent Parser Module - Natural Language Understanding (NLU)
=================================================================
WHAT THIS FILE DOES (Simple English):
  When you talk to Accio, you might say things casually like "Could you please open YouTube?",
  "Neeche scroll karo", or "Tell me about Albert Einstein". This file acts as the "brain interpreter":
  it cleans up polite filler words (like "please", "can you"), detects what action you want to perform,
  extracts key information (like website names, search topics, or message text), and labels it with an intent.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - Python Regular Expressions (re module):
      * What it does: Pattern matching engine with compiled regex rules for English and Hindi/Hinglish.
      * Why we use it: Executes in sub-millisecond time (< 0.1ms) with zero cloud LLM cost or network lag.
  - Dataclasses:
      * What it does: Strongly typed container (`Intent`) holding the intent name, parameters, and confidence.
"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class Intent:
    name: str
    params: Dict[str, Any]
    confidence: float = 1.0
    raw_text: str = ""

# Wake words, assistant greetings, and polite command prefixes
WAKE_PREFIX_REGEX = (
    r'^(?:hey\s+accio|ok\s+accio|hello\s+accio|accio|akio|echo|'
    r'wake\s*up(?:\s+(?:up|wake\s*up|now|please))?|'
    r'start(?:\s+(?:assistant|listening|up))?|'
    r'hey(?:\s+there)?|'
    r'can\s+you(?:\s+please)?|could\s+you(?:\s+please)?|would\s+you(?:\s+please)?|'
    r'please(?:\s+tell\s+me)?|tell\s+me(?:\s+like)?|tell\s+me|'
    r'show\s+me(?:\s+like)?|show\s+me)\b[,\s]*'
)

def clean_speech_text(text: str) -> str:
    """
    Normalizes transcript text by lowercasing, stripping punctuation, and removing wake prefixes iteratively.
    """
    cleaned = text.lower().strip()
    # Strip common leading/trailing punctuation
    cleaned = re.sub(r'^[^\w]+', '', cleaned)
    cleaned = re.sub(r'[^\w\s]+$', '', cleaned)

    # Iteratively strip compound prefixes like "Could you please...", "Can you please tell me like..."
    while True:
        prev = cleaned
        temp = re.sub(WAKE_PREFIX_REGEX, '', cleaned, flags=re.IGNORECASE).strip()
        temp = re.sub(r'^(?:like\s+(?:w\s+)?)+', '', temp).strip()
        # Clean conversational hesitation fillers: "uh", "um", "ah", "er"
        temp = re.sub(r'\b(?:uh+|um+|er+|ah+)\b', '', temp, flags=re.IGNORECASE).strip()
        temp = re.sub(r'\s+', ' ', temp).strip()

        # If stripping left a non-empty remainder (e.g. "open youtube"), adopt it.
        # If stripping emptied it out, it means the entire phrase was a greeting / wake phrase
        # (e.g. "hey", "hello accio", "wake up"). In that case, preserve `cleaned` for GREETING matching.
        if temp:
            cleaned = temp
        else:
            break

        if cleaned == prev:
            break

    return cleaned

def parse_intent(transcription: str) -> Intent:
    """
    Identifies the user's intent and parameters from the transcribed voice string.
    """
    text = clean_speech_text(transcription)
    if not text:
        return Intent(name="UNKNOWN", params={}, confidence=0.0, raw_text=transcription)

    # 1. System Hardware & Diagnostic Queries
    # RAM / Memory status (English & Hindi)
    if re.search(r'\b(?:how\s+much\s+)?(?:ram|memory)\s*(?:is\s+)?(?:occupied|used|free|available|left|consumed|in\s+my\s+laptop|in\s+my\s+pc|status)\b', text) or \
       re.search(r'\b(?:check\s+ram|ram\s+usage|memory\s+usage|check\s+memory|ram\s+kitna|memory\s+kitni|ram\s+kitni)\b', text):
        return Intent(name="SYSTEM_RAM", params={}, raw_text=transcription)

    # Battery status (English & Hindi)
    if re.search(r'\b(?:how\s+much\s+)?(?:battery|power)\s*(?:percentage|status|level|remaining|life|is\s+left|kitni|kitna|bachi)\b', text):
        return Intent(name="SYSTEM_BATTERY", params={}, raw_text=transcription)

    # CPU usage (English & Hindi)
    if re.search(r'\b(?:cpu|processor)\s*(?:usage|utilization|load|percentage|status|kitna|load\s+kitna)\b', text):
        return Intent(name="SYSTEM_CPU", params={}, raw_text=transcription)

    # Current Time (English & Hindi)
    if re.search(r'\b(?:what\s+time\s+is\s+it|what\s+is\s+the\s+time|current\s+time|tell\s+me\s+the\s+time|time\s+kya|samay\s+kya|waqt\s+kya)\b', text):
        return Intent(name="SYSTEM_TIME", params={}, raw_text=transcription)

    # Current Date (English & Hindi)
    if re.search(r'\b(?:what\s+is\s+(?:today\'?s?\s+)?date|what\s+day\s+is\s+it|today\'?s?\s+date|date\s+kya|taareekh\s+kya)\b', text):
        return Intent(name="SYSTEM_DATE", params={}, raw_text=transcription)

    # 2. File & Note Creation (English & Hindi)
    # e.g., "create a txt file on desktop named Myank Important", "make a text file called Notes on documents", "desktop par file banao"
    # Location specified first: "create a txt file on desktop named Myank Important"
    create_file_match1 = re.search(
        r'^(?:create|make|save|write)\s+(?:a\s+)?(?:new\s+)?(?:txt\s+|text\s+)?(?:file|note|document)\s+'
        r'(?:(?:on|in)\s+(?:the\s+)?(desktop|documents)\s+)'
        r'(?:named|called|with\s+(?:the\s+)?name)\s+(.+)$',
        text,
        re.IGNORECASE
    )
    if create_file_match1:
        loc = create_file_match1.group(1).strip()
        fname = create_file_match1.group(2).strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": loc}, raw_text=transcription)

    # Location specified last: "make a text file called Project Plan on documents"
    create_file_match2 = re.search(
        r'^(?:create|make|save|write)\s+(?:a\s+)?(?:new\s+)?(?:txt\s+|text\s+)?(?:file|note|document)\s+'
        r'(?:named|called|with\s+(?:the\s+)?name)\s+(.+?)\s+(?:on|in)\s+(?:the\s+)?(desktop|documents)$',
        text,
        re.IGNORECASE
    )
    if create_file_match2:
        fname = create_file_match2.group(1).strip()
        loc = create_file_match2.group(2).strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": loc}, raw_text=transcription)

    # No location specified: "create a txt file named Myank Important" -> defaults to desktop
    create_file_match3 = re.search(
        r'^(?:create|make|save|write)\s+(?:a\s+)?(?:new\s+)?(?:txt\s+|text\s+)?(?:file|note|document)\s+'
        r'(?:named|called|with\s+(?:the\s+)?name)\s+(.+)$',
        text,
        re.IGNORECASE
    )
    if create_file_match3:
        fname = create_file_match3.group(1).strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": "desktop"}, raw_text=transcription)

    # Simple form with location at end: "create note shopping list on desktop"
    create_file_simple_loc = re.search(
        r'^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:txt\s+|text\s+)?(?:file|note)\s+([a-zA-Z0-9_\-\.\s]+?)\s+(?:on|in)\s+(?:the\s+)?(desktop|documents)$',
        text,
        re.IGNORECASE
    )
    if create_file_simple_loc and not text.startswith(('create tab', 'create desktop')):
        fname = create_file_simple_loc.group(1).strip()
        loc = create_file_simple_loc.group(2).strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": loc}, raw_text=transcription)

    # Simple form default to desktop: "create note shopping list"
    create_file_simple = re.search(
        r'^(?:create|make)\s+(?:a\s+)?(?:new\s+)?(?:txt\s+|text\s+)?(?:file|note)\s+([a-zA-Z0-9_\-\.\s]+?)$',
        text,
        re.IGNORECASE
    )
    if create_file_simple and not text.startswith(('create tab', 'create desktop')):
        fname = create_file_simple.group(1).strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": "desktop"}, raw_text=transcription)

    hi_create_file = re.search(
        r'^(?:desktop\s+par\s+)?(?:file|note)\s+banao\s*(?:naam\s+)?(.+)?$',
        text,
        re.IGNORECASE
    )
    if hi_create_file:
        fname = (hi_create_file.group(1) or "New Note").strip()
        return Intent(name="CREATE_FILE", params={"filename": fname, "location": "desktop"}, raw_text=transcription)

    # 3. Form Filling & Text Navigation
    fill_field_match = re.search(
        r'^(?:fill\s+(?:in\s+)?(?:field|input|box)(?:\s+with)?|enter\s+(?:text\s+)?)\s+(.+?)(?:\s+(?:in\s+(?:the\s+)?(?:field|input|box)))?$',
        text,
        re.IGNORECASE
    )
    if fill_field_match and not text.startswith(('enter text', 'enter')):
        return Intent(name="FORM_FILL_FIELD", params={"text": fill_field_match.group(1).strip()}, raw_text=transcription)

    # Tab navigation (English & Hindi)
    if re.search(r'\b(press\s+tab|next\s+field|next\s+input|tab\s+key|agla\s+field|tab\s+dabao)\b', text) or text == 'tab':
        return Intent(name="FORM_NEXT_FIELD", params={}, raw_text=transcription)

    # Previous field navigation (Shift+Tab)
    if re.search(r'\b(previous\s+field|prev\s+field|shift\s+tab|back\s+field|pichla\s+field)\b', text):
        return Intent(name="FORM_PREV_FIELD", params={}, raw_text=transcription)

    # Submit form / Press enter
    if re.search(r'\b(submit\s+form|submit|press\s+enter|hit\s+enter|enter\s+dabao|form\s+submit\s+karo)\b', text) or text == 'enter':
        return Intent(name="FORM_SUBMIT", params={}, raw_text=transcription)

    # Toggle checkbox / Space
    if re.search(r'\b(toggle\s+checkbox|check\s+box|press\s+space|hit\s+space|space\s+dabao|select\s+checkbox|checkbox\s+se?lect)\b', text) or text == 'space':
        return Intent(name="FORM_TOGGLE_CHECKBOX", params={}, raw_text=transcription)

    # Select all text (Ctrl+A)
    if re.search(r'\b(select\s+all(?:\s+text)?|highlight\s+all|sab\s+select\s+karo)\b', text):
        return Intent(name="SELECT_ALL", params={}, raw_text=transcription)

    # Clear field
    if re.search(r'\b(clear\s+(?:the\s+)?(?:field|input|text|box)|erase\s+(?:the\s+)?(?:field|input|text)|field\s+khali\s+karo)\b', text):
        return Intent(name="CLEAR_FIELD", params={}, raw_text=transcription)

    # Clipboard: Copy, Paste, Undo
    if re.search(r'\b(copy(?:\s+this|\s+that|\s+text)?|copy\s+karo)\b', text) and not text.startswith(('copy to', 'copy file')):
        return Intent(name="COPY_TEXT", params={}, raw_text=transcription)

    if re.search(r'\b(paste(?:\s+this|\s+that|\s+text|\s+here)?|paste\s+karo)\b', text):
        return Intent(name="PASTE_TEXT", params={}, raw_text=transcription)

    if re.search(r'\b(undo(?:\s+that|\s+last\s+action|\s+edit)?|undo\s+karo)\b', text):
        return Intent(name="UNDO_ACTION", params={}, raw_text=transcription)

    # 3. Messaging Automation
    type_and_send_match = re.search(
        r'^(?:(?:type|text|send\s+message|write)\s+)(.+?)\s+(?:and\s+send(?:\s+it)?|aur\s+bhej\s+do)$',
        text,
        re.IGNORECASE
    )
    if type_and_send_match:
        return Intent(name="TYPE_AND_SEND", params={"text": type_and_send_match.group(1).strip()}, raw_text=transcription)

    if re.search(r'\b(send\s+message|send\s+it|message\s+bhej\s+do|send\s+karo)\b', text):
        return Intent(name="SEND_MESSAGE", params={}, raw_text=transcription)

    # 4. Compound Commands: "open X and type/text Y"
    compound_type_match = re.search(
        r'^(open\s+.+?)\s+(?:and\s+)(?:then\s+)?(?:type|write|say|send|text|message|msg)\s+(.+)$',
        text,
        re.IGNORECASE
    )
    if compound_type_match:
        open_tgt = compound_type_match.group(1).strip()
        # Clean phrases like "open whatsapp web on edge browser" -> "open whatsapp web"
        open_tgt = re.sub(r'\b(?:on\s+(?:the\s+)?(?:edge|chrome|browser|web)|in\s+(?:the\s+)?(?:edge|chrome|browser|web))\b', '', open_tgt).strip()
        return Intent(
            name="COMPOUND_OPEN_AND_TYPE",
            params={
                "open_target": open_tgt,
                "text_to_type": compound_type_match.group(2).strip()
            },
            raw_text=transcription
        )

    # 5. Direct Typing / Dictation
    type_match = re.search(r'^(?:type|write|enter\s+text)\s+(.+)$', text, re.IGNORECASE)
    if type_match:
        return Intent(name="TYPE_TEXT", params={"text": type_match.group(1).strip()}, raw_text=transcription)

    # 6. Browser Scrolling, Zoom, and In-Page Search
    # Find on page (Ctrl+F)
    find_match = re.search(
        r'^(?:find\s+on\s+page|search\s+on\s+page|find\s+in\s+page|search\s+page\s+for|page\s+par\s+dhoondo)\s+(.+)$',
        text,
        re.IGNORECASE
    )
    if find_match:
        return Intent(name="BROWSER_FIND_ON_PAGE", params={"query": find_match.group(1).strip()}, raw_text=transcription)

    # Scroll down / up / top / bottom
    if re.search(r'\b(scroll\s+down|page\s+down|neeche\s+scroll(?:\s+karo)?|neeche\s+jao)\b', text):
        return Intent(name="BROWSER_SCROLL_DOWN", params={"steps": 1}, raw_text=transcription)

    if re.search(r'\b(scroll\s+up|page\s+up|upar\s+scroll(?:\s+karo)?|upar\s+jao)\b', text):
        return Intent(name="BROWSER_SCROLL_UP", params={"steps": 1}, raw_text=transcription)

    if re.search(r'\b(scroll\s+to\s+top|go\s+to\s+top|top\s+of\s+page|sabse\s+upar\s+jao)\b', text):
        return Intent(name="BROWSER_SCROLL_TOP", params={}, raw_text=transcription)

    if re.search(r'\b(scroll\s+to\s+bottom|go\s+to\s+bottom|bottom\s+of\s+page|sabse\s+neeche\s+jao)\b', text):
        return Intent(name="BROWSER_SCROLL_BOTTOM", params={}, raw_text=transcription)

    # Zoom controls
    if re.search(r'\b(zoom\s+in(?:\s+browser)?|zoom\s+badao|bada\s+dikhao)\b', text):
        return Intent(name="BROWSER_ZOOM_IN", params={}, raw_text=transcription)

    if re.search(r'\b(zoom\s+out(?:\s+browser)?|zoom\s+kam\s+karo|chhota\s+dikhao)\b', text):
        return Intent(name="BROWSER_ZOOM_OUT", params={}, raw_text=transcription)

    if re.search(r'\b(reset\s+zoom|normal\s+zoom|default\s+zoom|zoom\s+reset(?:\s+karo)?)\b', text):
        return Intent(name="BROWSER_ZOOM_RESET", params={}, raw_text=transcription)

    # Browser History & Downloads & Bookmarks
    if re.search(r'\b(open\s+history|browser\s+history|show\s+history|history\s+dikhao|history\s+kholo)\b', text):
        return Intent(name="BROWSER_OPEN_HISTORY", params={}, raw_text=transcription)

    if re.search(r'\b(open\s+downloads|browser\s+downloads|show\s+downloads|downloads\s+dikhao|downloads\s+kholo)\b', text):
        return Intent(name="BROWSER_OPEN_DOWNLOADS", params={}, raw_text=transcription)

    if re.search(r'\b(bookmark\s+page|bookmark\s+this(?:\s+page)?|page\s+bookmark\s+karo)\b', text):
        return Intent(name="BROWSER_BOOKMARK", params={}, raw_text=transcription)

    # Browser Back / Forward
    if re.search(r'\b(go\s+back|back\s+page|previous\s+page|peeche\s+jao)\b', text):
        return Intent(name="BROWSER_GO_BACK", params={}, raw_text=transcription)

    if re.search(r'\b(go\s+forward|forward\s+page|next\s+page\s+history|aage\s+jao)\b', text):
        return Intent(name="BROWSER_GO_FORWARD", params={}, raw_text=transcription)

    # Fullscreen mode (F11)
    if re.search(r'\b(toggle\s+fullscreen|fullscreen\s+mode|full\s+screen\s+browser)\b', text):
        return Intent(name="BROWSER_FULLSCREEN", params={}, raw_text=transcription)

    # 7. Web Search
    search_match = re.search(
        r'^(?:search(?:\s+for|\s+on\s+the\s+web\s+for|\s+the\s+web\s+for)?|google|look\s+up)\s+(.+)$',
        text
    )
    if search_match:
        query = search_match.group(1).strip()
        query = re.sub(r'[\?!.]+$', '', query)
        return Intent(name="SEARCH_WEB", params={"query": query}, raw_text=transcription)

    # 8. Open Website by Name or URL (handles "open youtube", "open whatsapp web", etc.)
    site_match = re.search(
        r'^(?:(?:open|go\s+to|launch|navigate\s+to|kholo|chalao)\s+)?(?:the\s+)?(youtube|whatsapp(?:\s+web)?|github|gmail|reddit|wikipedia|twitter|x|netflix|amazon|maps|chatgpt|linkedin|google)(?:\.com|\.org)?(?:\s+(?:on|in)\s+(?:the\s+)?(?:web|browser|edge|chrome)(?:\s+browser)?)?(?:\s+(?:kholo|chalao|open\s+karo))?$',
        text
    )
    if site_match:
        target = site_match.group(1)
        if "whatsapp" in target and ("web" in text or "browser" in text):
            target = "whatsapp web"
        return Intent(name="OPEN_WEBSITE", params={"target": target}, raw_text=transcription)

    url_match = re.search(r'^(?:open|go\s+to)\s+([a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s]*)?)$', text)
    if url_match:
        return Intent(name="OPEN_WEBSITE", params={"target": url_match.group(1)}, raw_text=transcription)

    # 9. Browser Tab Controls
    if re.search(r'\b(new\s+tab|open\s+(?:a\s+)?new\s+tab|create\s+tab|naya\s+tab)\b', text):
        return Intent(name="BROWSER_NEW_TAB", params={}, raw_text=transcription)

    if re.search(r'\b(close\s+(?:this\s+)?tab|shut\s+tab|exit\s+tab|tab\s+band\s+karo)\b', text):
        return Intent(name="BROWSER_CLOSE_TAB", params={}, raw_text=transcription)

    if re.search(r'\b(reopen\s+tab|restore\s+tab|undo\s+close\s+tab)\b', text):
        return Intent(name="BROWSER_REOPEN_TAB", params={}, raw_text=transcription)

    if re.search(r'\b(next\s+tab|switch\s+tab|switch\s+to\s+next\s+tab|agla\s+tab)\b', text):
        return Intent(name="BROWSER_SWITCH_TAB", params={"direction": "next"}, raw_text=transcription)

    if re.search(r'\b(previous\s+tab|prev\s+tab|switch\s+to\s+previous\s+tab|pichla\s+tab)\b', text):
        return Intent(name="BROWSER_SWITCH_TAB", params={"direction": "prev"}, raw_text=transcription)

    if re.search(r'\b(refresh|reload|refresh\s+page|reload\s+page)\b', text):
        return Intent(name="BROWSER_REFRESH", params={}, raw_text=transcription)

    # 10. Window Controls & Snapping & Virtual Desktops
    if re.search(r'\b(snap\s+(?:window\s+)?left|left\s+snap(?:\s+karo)?)\b', text):
        return Intent(name="WINDOW_SNAP_LEFT", params={}, raw_text=transcription)

    if re.search(r'\b(snap\s+(?:window\s+)?right|right\s+snap(?:\s+karo)?)\b', text):
        return Intent(name="WINDOW_SNAP_RIGHT", params={}, raw_text=transcription)

    if re.search(r'\b(task\s+view|open\s+task\s+view|show\s+tasks|task\s+view\s+dikhao)\b', text):
        return Intent(name="WINDOW_TASK_VIEW", params={}, raw_text=transcription)

    if re.search(r'\b(next\s+desktop|switch\s+(?:to\s+)?next\s+desktop|agla\s+desktop)\b', text):
        return Intent(name="DESKTOP_SWITCH", params={"direction": "next"}, raw_text=transcription)

    if re.search(r'\b(previous\s+desktop|prev\s+desktop|switch\s+(?:to\s+)?prev(?:ious)?\s+desktop|pichla\s+desktop)\b', text):
        return Intent(name="DESKTOP_SWITCH", params={"direction": "prev"}, raw_text=transcription)

    if re.search(r'\b(new\s+desktop|create\s+desktop|naya\s+desktop)\b', text):
        return Intent(name="DESKTOP_NEW", params={}, raw_text=transcription)

    if re.search(r'\b(close\s+desktop|delete\s+desktop|desktop\s+band\s+karo)\b', text):
        return Intent(name="DESKTOP_CLOSE", params={}, raw_text=transcription)

    if re.search(r'\b(close\s+(?:this\s+)?window|exit\s+window|quit\s+window|shut\s+window|window\s+band\s+karo|ise\s+band\s+karo)\b', text):
        return Intent(name="WINDOW_CLOSE", params={}, raw_text=transcription)

    if re.search(r'\b(minimize\s+window|minimize|hide\s+window)\b', text):
        return Intent(name="WINDOW_MINIMIZE", params={}, raw_text=transcription)

    if re.search(r'\b(maximize\s+window|maximize|full\s+screen)\b', text):
        return Intent(name="WINDOW_MAXIMIZE", params={}, raw_text=transcription)

    if re.search(r'\b(show\s+desktop|go\s+to\s+desktop|minimize\s+all|desktop\s+dikhao)\b', text):
        return Intent(name="SHOW_DESKTOP", params={}, raw_text=transcription)

    if re.search(r'\b(switch\s+window|switch\s+app|alt\s+tab|next\s+window)\b', text):
        return Intent(name="WINDOW_SWITCH", params={}, raw_text=transcription)

    # 11. Volume Controls (English & Hindi)
    if re.search(r'\b(volume\s+up|increase\s+volume|raise\s+volume|turn\s+up\s+volume|louder|aawaz\s+badhao|awaz\s+badhao|volume\s+badhao|aawaz\s+tez\s+karo)\b', text):
        return Intent(name="VOLUME_UP", params={"steps": 3}, raw_text=transcription)

    if re.search(r'\b(volume\s+down|decrease\s+volume|lower\s+volume|turn\s+down\s+volume|softer|quieter|aawaz\s+kam\s+karo|awaz\s+kam\s+karo|volume\s+kam\s+karo)\b', text):
        return Intent(name="VOLUME_DOWN", params={"steps": 3}, raw_text=transcription)

    if re.search(r'\b(mute|unmute|mute\s+volume|silence\s+audio|aawaz\s+band\s+karo|awaz\s+band\s+karo|mute\s+karo)\b', text):
        return Intent(name="VOLUME_MUTE", params={}, raw_text=transcription)

    # 12. Screenshot (English & Hindi)
    if re.search(r'\b(take\s+(?:a\s+)?screenshot|capture\s+(?:the\s+)?screen|screenshot|screenshot\s+lo|screenshot\s+kheencho)\b', text):
        return Intent(name="SCREENSHOT", params={}, raw_text=transcription)

    # 13. Desktop Application Launching
    app_match = re.search(
        r'^(?:open|launch|start|chalao|kholo)\s+(?:app\s+|application\s+)?(notepad|calculator|calc|terminal|command\s+prompt|cmd|explorer|files|file\s+explorer|paint|settings|whatsapp)\b',
        text
    )
    if app_match:
        return Intent(name="OPEN_APP", params={"app_name": app_match.group(1)}, raw_text=transcription)

    app_explicit_match = re.search(r'^(?:open|launch|start)\s+(?:app|application)\s+([a-zA-Z0-9_\-\.]+)', text)
    if app_explicit_match:
        return Intent(name="OPEN_APP", params={"app_name": app_explicit_match.group(1)}, raw_text=transcription)

    # 14. Media Playback Controls
    if re.search(r'\b(play\s+music|pause\s+music|pause|resume\s+playback|play\s+media|gana\s+bajao|gana\s+roko)\b', text):
        return Intent(name="MEDIA_PLAY_PAUSE", params={}, raw_text=transcription)

    # 15. Lock Workstation
    if re.search(r'\b(lock\s+computer|lock\s+screen|lock\s+workstation|lock\s+pc|computer\s+lock\s+karo)\b', text):
        return Intent(name="LOCK_SCREEN", params={}, raw_text=transcription)

    # 16. Greetings & Identity (English & Hindi)
    if re.search(r'^(?:hello|hi|hey|wake\s*up(?:\s+(?:up|wake\s*up|now))?|start|good\s+morning|good\s+afternoon|good\s+evening|namaste|namaskar|pranam)(?:\s+accio)?$', text) or \
       re.search(r'^(?:who\s+are\s+you|what\s+can\s+you\s+do|how\s+are\s+you(?:\s+doing)?|help(?:\s+me)?|aap\s+kaun\s+ho|tum\s+kaun\s+ho)$', text):
        return Intent(name="GREETING", params={"original": text}, raw_text=transcription)

    # 17. Exit / Shutdown Assistant (English & Hindi)
    if re.search(r'\b(exit|quit|stop\s+listening|goodbye|bye|alvida|band\s+karo\s+accio)\b', text):
        return Intent(name="EXIT_ASSISTANT", params={}, raw_text=transcription)

    # 18. Factual & Knowledge Q&A Queries ("who is X", "what is X", "tell me about X", "explain X", Hindi: "X kya hai", "X ke baare mein batao")
    # Matches informational queries to retrieve direct spoken answers
    en_question_match = re.search(
        r'^(?:what\s+is|who\s+is|where\s+is|why\s+is|how\s+does|tell\s+me\s+about|about|explain|define)\s+(.+)$',
        text,
        re.IGNORECASE
    )
    if en_question_match:
        subject = en_question_match.group(1).strip()
        # Clean trailing question mark and leading articles
        subject = re.sub(r'[\?!.]+$', '', subject)
        subject = re.sub(r'^(?:the|a|an)\s+', '', subject).strip()
        return Intent(name="KNOWLEDGE_QUERY", params={"query": subject, "full_text": text}, raw_text=transcription)

    hi_question_match = re.search(
        r'^(.+?)\s+(?:kya\s+hai|kaun\s+hai|kahan\s+hai|ke\s+baare\s+mein\s+batao|batao)$',
        text,
        re.IGNORECASE
    )
    if hi_question_match and len(text.split()) >= 2:
        subject = hi_question_match.group(1).strip()
        return Intent(name="KNOWLEDGE_QUERY", params={"query": subject, "full_text": text}, raw_text=transcription)

    # 19. Fallback: If starts with "open" followed by arbitrary words
    open_fallback = re.search(r'^(?:open|launch)\s+(.+)$', text)
    if open_fallback:
        target = open_fallback.group(1).strip()
        return Intent(name="OPEN_WEBSITE", params={"target": target}, confidence=0.7, raw_text=transcription)

    # 20. Conversational Search Fallback for multi-word queries
    words = text.split()
    if len(words) >= 3 and not text.startswith(('exit', 'quit', 'bye')):
        return Intent(name="SEARCH_WEB", params={"query": text}, confidence=0.6, raw_text=transcription)

    return Intent(name="UNKNOWN", params={"raw": text}, confidence=0.0, raw_text=transcription)

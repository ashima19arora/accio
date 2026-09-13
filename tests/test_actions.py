"""
Unit Tests for Accio Native Actions, Intent Parser, and Automation Controls
"""

import sys
import unittest
from actions.intent_parser import parse_intent, clean_speech_text

class TestAccioActions(unittest.TestCase):

    def test_clean_speech_text(self):
        self.assertEqual(clean_speech_text("Accio, search for SpaceX"), "search for spacex")
        self.assertEqual(clean_speech_text("Hey Accio, please open YouTube!"), "open youtube")
        self.assertEqual(clean_speech_text("Could you please close this window?"), "close this window")
        self.assertEqual(clean_speech_text("Can you please tell me like how much RAM is used?"), "how much ram is used")

    def test_search_intents(self):
        intent1 = parse_intent("search for weather in Mumbai")
        self.assertEqual(intent1.name, "SEARCH_WEB")
        self.assertEqual(intent1.params.get("query").lower(), "weather in mumbai")

        intent2 = parse_intent("google latest news today")
        self.assertEqual(intent2.name, "SEARCH_WEB")
        self.assertEqual(intent2.params.get("query").lower(), "latest news today")

    def test_knowledge_qna_intents(self):
        # Factual knowledge queries route to KNOWLEDGE_QUERY
        intent1 = parse_intent("what is quantum computing")
        self.assertEqual(intent1.name, "KNOWLEDGE_QUERY")
        self.assertEqual(intent1.params.get("query").lower(), "quantum computing")

        intent2 = parse_intent("who is Albert Einstein")
        self.assertEqual(intent2.name, "KNOWLEDGE_QUERY")
        self.assertEqual(intent2.params.get("query").lower(), "albert einstein")

        intent3 = parse_intent("tell me about Mars")
        self.assertEqual(intent3.name, "KNOWLEDGE_QUERY")
        self.assertEqual(intent3.params.get("query").lower(), "mars")

        intent4 = parse_intent("photosynthesis kya hai")
        self.assertEqual(intent4.name, "KNOWLEDGE_QUERY")
        self.assertEqual(intent4.params.get("query").lower(), "photosynthesis")

    def test_website_intents(self):
        intent1 = parse_intent("open youtube")
        self.assertEqual(intent1.name, "OPEN_WEBSITE")
        self.assertEqual(intent1.params.get("target"), "youtube")

        intent2 = parse_intent("Can you please open the YouTube?")
        self.assertEqual(intent2.name, "OPEN_WEBSITE")
        self.assertEqual(intent2.params.get("target"), "youtube")

        intent3 = parse_intent("open whatsapp")
        self.assertEqual(intent3.name, "OPEN_WEBSITE")
        self.assertEqual(intent3.params.get("target"), "whatsapp")

        intent4 = parse_intent("go to github.com")
        self.assertEqual(intent4.name, "OPEN_WEBSITE")
        self.assertEqual(intent4.params.get("target"), "github")

    def test_browser_tab_intents(self):
        self.assertEqual(parse_intent("open a new tab").name, "BROWSER_NEW_TAB")
        self.assertEqual(parse_intent("close this tab").name, "BROWSER_CLOSE_TAB")
        self.assertEqual(parse_intent("next tab").name, "BROWSER_SWITCH_TAB")
        self.assertEqual(parse_intent("refresh the page").name, "BROWSER_REFRESH")
        self.assertEqual(parse_intent("reopen tab").name, "BROWSER_REOPEN_TAB")

    def test_browser_scroll_and_zoom_intents(self):
        self.assertEqual(parse_intent("scroll down").name, "BROWSER_SCROLL_DOWN")
        self.assertEqual(parse_intent("scroll up").name, "BROWSER_SCROLL_UP")
        self.assertEqual(parse_intent("scroll to top").name, "BROWSER_SCROLL_TOP")
        self.assertEqual(parse_intent("scroll to bottom").name, "BROWSER_SCROLL_BOTTOM")
        self.assertEqual(parse_intent("zoom in").name, "BROWSER_ZOOM_IN")
        self.assertEqual(parse_intent("zoom out").name, "BROWSER_ZOOM_OUT")
        self.assertEqual(parse_intent("reset zoom").name, "BROWSER_ZOOM_RESET")
        self.assertEqual(parse_intent("go back").name, "BROWSER_GO_BACK")
        self.assertEqual(parse_intent("go forward").name, "BROWSER_GO_FORWARD")
        self.assertEqual(parse_intent("open history").name, "BROWSER_OPEN_HISTORY")
        self.assertEqual(parse_intent("open downloads").name, "BROWSER_OPEN_DOWNLOADS")
        self.assertEqual(parse_intent("bookmark page").name, "BROWSER_BOOKMARK")
        self.assertEqual(parse_intent("toggle fullscreen").name, "BROWSER_FULLSCREEN")

        find_intent = parse_intent("find on page quantum physics")
        self.assertEqual(find_intent.name, "BROWSER_FIND_ON_PAGE")
        self.assertEqual(find_intent.params.get("query"), "quantum physics")

    def test_form_filling_and_navigation_intents(self):
        self.assertEqual(parse_intent("press tab").name, "FORM_NEXT_FIELD")
        self.assertEqual(parse_intent("next field").name, "FORM_NEXT_FIELD")
        self.assertEqual(parse_intent("previous field").name, "FORM_PREV_FIELD")
        self.assertEqual(parse_intent("shift tab").name, "FORM_PREV_FIELD")
        self.assertEqual(parse_intent("submit form").name, "FORM_SUBMIT")
        self.assertEqual(parse_intent("press enter").name, "FORM_SUBMIT")
        self.assertEqual(parse_intent("toggle checkbox").name, "FORM_TOGGLE_CHECKBOX")
        self.assertEqual(parse_intent("press space").name, "FORM_TOGGLE_CHECKBOX")
        self.assertEqual(parse_intent("select all text").name, "SELECT_ALL")
        self.assertEqual(parse_intent("clear field").name, "CLEAR_FIELD")
        self.assertEqual(parse_intent("copy text").name, "COPY_TEXT")
        self.assertEqual(parse_intent("paste text").name, "PASTE_TEXT")
        self.assertEqual(parse_intent("undo").name, "UNDO_ACTION")

        fill_intent = parse_intent("fill field with John Doe")
        self.assertEqual(fill_intent.name, "FORM_FILL_FIELD")
        self.assertEqual(fill_intent.params.get("text").lower(), "john doe")

    def test_messaging_intents(self):
        self.assertEqual(parse_intent("send message").name, "SEND_MESSAGE")

        msg_intent = parse_intent("type Hello everyone and send")
        self.assertEqual(msg_intent.name, "TYPE_AND_SEND")
        self.assertEqual(msg_intent.params.get("text").lower(), "hello everyone")

    def test_window_snapping_and_desktop_intents(self):
        self.assertEqual(parse_intent("snap window left").name, "WINDOW_SNAP_LEFT")
        self.assertEqual(parse_intent("snap window right").name, "WINDOW_SNAP_RIGHT")
        self.assertEqual(parse_intent("open task view").name, "WINDOW_TASK_VIEW")
        self.assertEqual(parse_intent("next desktop").name, "DESKTOP_SWITCH")
        self.assertEqual(parse_intent("previous desktop").name, "DESKTOP_SWITCH")
        self.assertEqual(parse_intent("new desktop").name, "DESKTOP_NEW")
        self.assertEqual(parse_intent("close desktop").name, "DESKTOP_CLOSE")

        self.assertEqual(parse_intent("close window").name, "WINDOW_CLOSE")
        self.assertEqual(parse_intent("minimize window").name, "WINDOW_MINIMIZE")
        self.assertEqual(parse_intent("maximize window").name, "WINDOW_MAXIMIZE")
        self.assertEqual(parse_intent("show desktop").name, "SHOW_DESKTOP")
        self.assertEqual(parse_intent("switch window").name, "WINDOW_SWITCH")

    def test_bilingual_hindi_commands(self):
        self.assertEqual(parse_intent("agla field").name, "FORM_NEXT_FIELD")
        self.assertEqual(parse_intent("tab dabao").name, "FORM_NEXT_FIELD")
        self.assertEqual(parse_intent("pichla field").name, "FORM_PREV_FIELD")
        self.assertEqual(parse_intent("form submit karo").name, "FORM_SUBMIT")
        self.assertEqual(parse_intent("field khali karo").name, "CLEAR_FIELD")
        self.assertEqual(parse_intent("neeche scroll karo").name, "BROWSER_SCROLL_DOWN")
        self.assertEqual(parse_intent("upar scroll karo").name, "BROWSER_SCROLL_UP")
        self.assertEqual(parse_intent("bada dikhao").name, "BROWSER_ZOOM_IN")
        self.assertEqual(parse_intent("chhota dikhao").name, "BROWSER_ZOOM_OUT")
        self.assertEqual(parse_intent("history dikhao").name, "BROWSER_OPEN_HISTORY")
        self.assertEqual(parse_intent("downloads dikhao").name, "BROWSER_OPEN_DOWNLOADS")
        self.assertEqual(parse_intent("left snap karo").name, "WINDOW_SNAP_LEFT")
        self.assertEqual(parse_intent("right snap karo").name, "WINDOW_SNAP_RIGHT")
        self.assertEqual(parse_intent("aawaz badhao").name, "VOLUME_UP")
        self.assertEqual(parse_intent("aawaz kam karo").name, "VOLUME_DOWN")
        self.assertEqual(parse_intent("aawaz band karo").name, "VOLUME_MUTE")

    def test_volume_intents(self):
        self.assertEqual(parse_intent("turn volume up").name, "VOLUME_UP")
        self.assertEqual(parse_intent("decrease volume").name, "VOLUME_DOWN")
        self.assertEqual(parse_intent("mute audio").name, "VOLUME_MUTE")

    def test_app_intents(self):
        intent1 = parse_intent("open notepad")
        self.assertEqual(intent1.name, "OPEN_APP")
        self.assertEqual(intent1.params.get("app_name"), "notepad")

        intent2 = parse_intent("launch calculator")
        self.assertEqual(intent2.name, "OPEN_APP")
        self.assertEqual(intent2.params.get("app_name"), "calculator")

    def test_system_diagnostics_intents(self):
        intent1 = parse_intent("Can you please tell me like w how much RAM is occupied in my laptop?")
        self.assertEqual(intent1.name, "SYSTEM_RAM")

        intent2 = parse_intent("check ram usage")
        self.assertEqual(intent2.name, "SYSTEM_RAM")

        intent3 = parse_intent("how much battery is left")
        self.assertEqual(intent3.name, "SYSTEM_BATTERY")

        intent4 = parse_intent("what time is it")
        self.assertEqual(intent4.name, "SYSTEM_TIME")

        intent5 = parse_intent("what is today's date")
        self.assertEqual(intent5.name, "SYSTEM_DATE")

    def test_compound_and_typing_intents(self):
        intent1 = parse_intent("Can you open WhatsApp and type Hashima Aurora or hello?")
        self.assertEqual(intent1.name, "COMPOUND_OPEN_AND_TYPE")
        self.assertIn("whatsapp", intent1.params.get("open_target", "").lower())
        self.assertIn("hello", intent1.params.get("text_to_type", "").lower())

        intent2 = parse_intent("type Hello World")
        self.assertEqual(intent2.name, "TYPE_TEXT")
        self.assertEqual(intent2.params.get("text").lower(), "hello world")

    def test_system_intents(self):
        self.assertEqual(parse_intent("take a screenshot").name, "SCREENSHOT")
        self.assertEqual(parse_intent("lock computer").name, "LOCK_SCREEN")
        self.assertEqual(parse_intent("play music").name, "MEDIA_PLAY_PAUSE")

    def test_assistant_control_intents(self):
        self.assertEqual(parse_intent("hello accio").name, "GREETING")
        self.assertEqual(parse_intent("stop listening").name, "EXIT_ASSISTANT")
        self.assertEqual(parse_intent("goodbye").name, "EXIT_ASSISTANT")

    def test_create_file_intents(self):
        # Exact utterance from user with hesitation fillers
        intent1 = parse_intent("Can you please uh create a txt file on desktop named Myank Important?")
        self.assertEqual(intent1.name, "CREATE_FILE")
        self.assertEqual(intent1.params.get("filename").lower(), "myank important")
        self.assertEqual(intent1.params.get("location").lower(), "desktop")

        intent2 = parse_intent("make a text file called Project Plan on documents")
        self.assertEqual(intent2.name, "CREATE_FILE")
        self.assertEqual(intent2.params.get("filename").lower(), "project plan")
        self.assertEqual(intent2.params.get("location").lower(), "documents")

        intent3 = parse_intent("desktop par file banao Meeting Notes")
        self.assertEqual(intent3.name, "CREATE_FILE")
        self.assertEqual(intent3.params.get("filename").lower(), "meeting notes")
        self.assertEqual(intent3.params.get("location").lower(), "desktop")

    def test_wake_words_and_prefixes(self):
        # Standalone wake phrases
        self.assertEqual(parse_intent("hey").name, "GREETING")
        self.assertEqual(parse_intent("wake up").name, "GREETING")
        self.assertEqual(parse_intent("wake up up").name, "GREETING")
        self.assertEqual(parse_intent("start").name, "GREETING")
        self.assertEqual(parse_intent("hello").name, "GREETING")
        self.assertEqual(parse_intent("hey lets start").name, "GREETING")
        self.assertEqual(parse_intent("activate").name, "GREETING")
        self.assertEqual(parse_intent("begin").name, "GREETING")

        # Wake phrases chained with commands
        intent1 = parse_intent("hey open youtube")
        self.assertEqual(intent1.name, "OPEN_WEBSITE")
        self.assertEqual(intent1.params.get("target"), "youtube")

        intent2 = parse_intent("wake up scroll down")
        self.assertEqual(intent2.name, "BROWSER_SCROLL_DOWN")

        intent3 = parse_intent("wake up up create a txt file on desktop named Myank Important")
        self.assertEqual(intent3.name, "CREATE_FILE")
        self.assertEqual(intent3.params.get("filename").lower(), "myank important")

        intent4 = parse_intent("start open notepad")
        self.assertEqual(intent4.name, "OPEN_APP")
        self.assertEqual(intent4.params.get("app_name").lower(), "notepad")

        intent5 = parse_intent("hey lets start open notepad")
        self.assertEqual(intent5.name, "OPEN_APP")
        self.assertEqual(intent5.params.get("app_name").lower(), "notepad")

        intent6 = parse_intent("activate volume up")
        self.assertEqual(intent6.name, "VOLUME_UP")

        intent7 = parse_intent("begin scroll down")
        self.assertEqual(intent7.name, "BROWSER_SCROLL_DOWN")

    def test_execute_delimiter(self):
        # Trailing 'execute' delimiters
        intent1 = parse_intent("open notepad execute")
        self.assertEqual(intent1.name, "OPEN_APP")
        self.assertEqual(intent1.params.get("app_name").lower(), "notepad")

        intent2 = parse_intent("volume up please execute")
        self.assertEqual(intent2.name, "VOLUME_UP")

        intent3 = parse_intent("scroll down execute")
        self.assertEqual(intent3.name, "BROWSER_SCROLL_DOWN")

        # Full hands-free: wake phrase + command + execute delimiter
        intent4 = parse_intent("hey lets start open notepad execute")
        self.assertEqual(intent4.name, "OPEN_APP")
        self.assertEqual(intent4.params.get("app_name").lower(), "notepad")

        intent5 = parse_intent("activate volume up execute")
        self.assertEqual(intent5.name, "VOLUME_UP")

        intent6 = parse_intent("begin search for SpaceX execute")
        self.assertEqual(intent6.name, "SEARCH_WEB")
        self.assertEqual(intent6.params.get("query").lower(), "spacex")

    def test_unknown_or_search_fallback(self):
        # Short gibberish
        intent1 = parse_intent("xyz")
        self.assertEqual(intent1.name, "UNKNOWN")

        # Descriptive multi-word informational query routes to KNOWLEDGE_QUERY for direct spoken answers
        intent2 = parse_intent("compare quantum computing and classical computers")
        self.assertEqual(intent2.name, "KNOWLEDGE_QUERY")

        # Conversational questions route to dedicated conversational or knowledge handlers
        intent3 = parse_intent("Hello, how are you?")
        self.assertEqual(intent3.name, "WELLBEING_QUERY")

        # Explicit search only when search/google keyword is provided
        intent4 = parse_intent("search for quantum computing")
        self.assertEqual(intent4.name, "SEARCH_WEB")

if __name__ == "__main__":
    unittest.main()

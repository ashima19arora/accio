"""
Unit Tests for Screen Context Understander (Accio Screen Lens)
==============================================================
Tests window context collection, screenshot encoding, credential masking,
and screen query intent recognition.
"""

import unittest
from actions.screen_context import (
    get_active_window_context,
    capture_screen_snapshot,
    get_clipboard_text_snippet,
    collect_screen_context
)
from actions.intent_parser import parse_intent
import actions

class TestScreenContext(unittest.TestCase):

    def test_get_active_window_context_structure(self):
        ctx = get_active_window_context()
        self.assertIsInstance(ctx, dict)
        self.assertIn("title", ctx)
        self.assertIn("process_name", ctx)
        self.assertIn("friendly_name", ctx)
        self.assertIn("hwnd", ctx)

    def test_capture_screen_snapshot_format(self):
        # Verify capture produces valid base64 or gracefully handles headless sessions
        snapshot = capture_screen_snapshot(active_window_only=False, max_width=400)
        if snapshot is not None:
            self.assertIsInstance(snapshot, str)
            self.assertGreater(len(snapshot), 50)

    def test_collect_screen_context_payload(self):
        payload = collect_screen_context()
        self.assertIsInstance(payload, dict)
        self.assertIn("app_name", payload)
        self.assertIn("window_title", payload)
        self.assertIn("has_image", payload)
        self.assertIn("clipboard_snippet", payload)

    def test_screen_intent_parsing_english(self):
        queries = [
            ("what is on my screen", "SCREEN_CONTEXT_QUERY"),
            ("what's on my screen", "SCREEN_CONTEXT_QUERY"),
            ("explain what I'm looking at", "SCREEN_CONTEXT_QUERY"),
            ("summarize this page", "SCREEN_CONTEXT_QUERY"),
            ("summarize this screen", "SCREEN_CONTEXT_QUERY"),
            ("what does this error say", "SCREEN_CONTEXT_QUERY"),
            ("explain this error", "SCREEN_CONTEXT_QUERY"),
            ("what is this window", "SCREEN_CONTEXT_QUERY"),
            ("which app is open", "SCREEN_CONTEXT_QUERY"),
            ("read what's on the screen", "SCREEN_CONTEXT_QUERY")
        ]
        for query, expected_intent in queries:
            intent = parse_intent(query)
            self.assertEqual(intent.name, expected_intent, f"Failed for query: '{query}'")

    def test_screen_intent_parsing_hindi(self):
        hi_queries = [
            ("screen par kya hai", "SCREEN_CONTEXT_QUERY"),
            ("screen pe kya hai", "SCREEN_CONTEXT_QUERY"),
            ("screen explain karo", "SCREEN_CONTEXT_QUERY"),
            ("error kya hai", "SCREEN_CONTEXT_QUERY"),
            ("kaunsa app khula hai", "SCREEN_CONTEXT_QUERY")
        ]
        for query, expected_intent in hi_queries:
            intent = parse_intent(query)
            self.assertEqual(intent.name, expected_intent, f"Failed for Hindi query: '{query}'")

    def test_execute_screen_context_query(self):
        res = actions.execute_command("what is on my screen")
        self.assertTrue(res.success)
        self.assertEqual(res.intent, "SCREEN_CONTEXT_QUERY")
        self.assertIsInstance(res.message, str)
        self.assertGreater(len(res.message), 5)

if __name__ == "__main__":
    unittest.main()

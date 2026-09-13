"""
Unit Tests for OpenRouter Multi-Key Failover and LLM Client
============================================================
Tests key failover rotation, speech output sanitization, and in-memory caching.
"""

import unittest
from unittest.mock import patch, MagicMock
from actions.llm_client import KeyFailoverManager, clean_for_speech_output, ask_accio_llm

class TestLLMClient(unittest.TestCase):

    def test_key_failover_cooldown(self):
        keys = ["key-1", "key-2", "key-3"]
        manager = KeyFailoverManager(keys, cooldown_seconds=20.0)

        # Initially all keys are healthy and in order
        self.assertEqual(manager.get_candidate_keys(), ["key-1", "key-2", "key-3"])

        # Simulate key-1 receiving a 429 rate limit
        manager.mark_failure("key-1", status_code=429)

        # key-1 should be moved to the back (cooling down), with key-2 and key-3 prioritized
        candidates = manager.get_candidate_keys()
        self.assertEqual(candidates[0], "key-2")
        self.assertEqual(candidates[1], "key-3")
        self.assertEqual(candidates[2], "key-1")

        # Simulate key-2 succeeding
        manager.mark_success("key-2")
        self.assertNotIn("key-2", manager.key_cooldowns)

    def test_clean_for_speech_output(self):
        # 1. Reasoning blocks
        raw_think = "<think>The user asks what gravity is...</think>Gravity pulls objects together."
        self.assertEqual(clean_for_speech_output(raw_think), "Gravity pulls objects together.")

        # 2. Markdown headers, bold, and italics
        raw_md = "### Gravity\n**Gravity** is *fundamental*."
        self.assertEqual(clean_for_speech_output(raw_md), "Gravity is fundamental.")

        # 3. Bullet points and citations
        raw_list = "- Earth pulls objects [1].\n- Moon orbits Earth [2]."
        self.assertEqual(clean_for_speech_output(raw_list), "Earth pulls objects. Moon orbits Earth.")

        # 4. Code blocks
        raw_code = "Here is an example: ```python print('hi') ``` and done."
        self.assertEqual(clean_for_speech_output(raw_code), "Here is an example: and done.")

    @patch("requests.post")
    def test_ask_accio_llm_and_cache(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Gravity is the fundamental force that attracts objects together."}}
            ]
        }
        mock_post.return_value = mock_response

        # Verify asking a question works and returns clean string
        ans1 = ask_accio_llm("what is quantum test gravity query", lang="en")
        self.assertIsNotNone(ans1)
        self.assertIsInstance(ans1, str)
        self.assertGreater(len(ans1), 10)

        # Verify second call is served from cache without triggering another API call
        call_count_before = mock_post.call_count
        ans2 = ask_accio_llm("what is quantum test gravity query", lang="en")
        self.assertEqual(ans1, ans2)
        self.assertEqual(mock_post.call_count, call_count_before)

if __name__ == "__main__":
    unittest.main()


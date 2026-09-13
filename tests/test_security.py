"""
Unit Tests for Accio Multi-Layer Security Architecture
Verifies threat detection, application whitelisting, URL protocol isolation,
dictation sanitization, policy evaluation, and security audit logging.
"""

import os
import unittest
from actions.security.threat_detector import analyze_threat
from actions.security.sanitizer import (
    sanitize_url,
    sanitize_app_target,
    sanitize_typed_text,
    sanitize_search_query
)
from actions.security.policy import RiskTier, evaluate_policy
from actions.security.audit_logger import get_recent_audit_events
from actions.intent_parser import Intent
from actions.registry import execute_command

class TestAccioSecurity(unittest.TestCase):

    def test_destructive_os_threats_blocked(self):
        """Ensures commands attempting to damage the OS or disks are flagged as CRITICAL threats."""
        threats = [
            "delete the operating system",
            "delete my os",
            "destroy windows",
            "format c drive",
            "format drive c",
            "format disk",
            "wipe windows",
            "clean all diskpart",
            "delete system32",
        ]
        for utterance in threats:
            assessment = analyze_threat(utterance)
            self.assertTrue(
                assessment.is_threat,
                f"Failed to flag destructive command: '{utterance}'"
            )
            self.assertEqual(assessment.severity, "CRITICAL")

    def test_file_deletion_threats_blocked(self):
        """Ensures mass deletion or file removal is intercepted."""
        threats = [
            "delete all my files",
            "remove all documents",
            "erase my data",
            "delete folder",
            "rm -rf /",
            "del /f /s C:\\*",
            "rmdir /s myfolder",
            "remove file passwords.txt",
        ]
        for utterance in threats:
            assessment = analyze_threat(utterance)
            self.assertTrue(
                assessment.is_threat,
                f"Failed to flag file deletion threat: '{utterance}'"
            )

    def test_shell_injection_threats_blocked(self):
        """Ensures arbitrary shell and privilege alteration commands are flagged."""
        threats = [
            "cmd.exe /c del important.txt",
            "powershell -encodedcommand aabbcc",
            "reg delete HKLM\\Software",
            "takeown /f C:\\Windows",
            "net user hacker Password123 /add",
        ]
        for utterance in threats:
            assessment = analyze_threat(utterance)
            self.assertTrue(
                assessment.is_threat,
                f"Failed to flag shell injection: '{utterance}'"
            )

    def test_legitimate_queries_pass_threat_detector(self):
        """Ensures regular user accessibility queries are not falsely flagged."""
        safe_queries = [
            "Can you please open the YouTube?",
            "Can you open WhatsApp and type Hashima Aurora or hello?",
            "Can you please tell me like w how much RAM is occupied in my laptop?",
            "what is the time",
            "volume up",
            "take a screenshot",
            "open notepad",
            "search for weather forecast",
            "minimize window",
        ]
        for utterance in safe_queries:
            assessment = analyze_threat(utterance)
            self.assertFalse(
                assessment.is_threat,
                f"Safe query falsely flagged as threat: '{utterance}'"
            )

    def test_application_whitelist_enforcement(self):
        """Ensures only approved applications can be launched."""
        # Safe applications
        ok, target, _ = sanitize_app_target("notepad")
        self.assertTrue(ok)
        self.assertEqual(target, "notepad.exe")

        ok, target, _ = sanitize_app_target("calculator")
        self.assertTrue(ok)
        self.assertEqual(target, "calc.exe")

        ok, target, _ = sanitize_app_target("whatsapp")
        self.assertTrue(ok)
        self.assertEqual(target, "whatsapp:")

        # Dangerous or unapproved apps
        ok, _, reason = sanitize_app_target("malware_launcher.exe")
        self.assertFalse(ok)
        self.assertIn("whitelist", reason.lower())

        ok, _, reason = sanitize_app_target("cmd.exe")
        self.assertFalse(ok)

        ok, _, reason = sanitize_app_target("powershell")
        self.assertFalse(ok)

    def test_url_protocol_and_sandbox_isolation(self):
        """Ensures local file schemes, loopback IPs, and executable downloads are blocked."""
        # Safe URLs
        ok, url, _ = sanitize_url("https://www.youtube.com")
        self.assertTrue(ok)

        ok, url, _ = sanitize_url("github.com")
        self.assertTrue(ok)
        self.assertTrue(url.startswith("https://"))

        # Blocked: file scheme
        ok, _, reason = sanitize_url("file:///C:/Windows/System32/cmd.exe")
        self.assertFalse(ok)
        self.assertIn("forbidden url scheme", reason.lower())

        # Blocked: javascript scheme
        ok, _, reason = sanitize_url("javascript:alert('pwned')")
        self.assertFalse(ok)

        # Blocked: local loopback
        ok, _, reason = sanitize_url("http://127.0.0.1:8080/admin")
        self.assertFalse(ok)
        self.assertIn("restricted", reason.lower())

        ok, _, reason = sanitize_url("http://localhost:3000")
        self.assertFalse(ok)

        # Blocked: private subnet IP
        ok, _, reason = sanitize_url("http://192.168.1.1")
        self.assertFalse(ok)

        # Blocked: executable payload download
        ok, _, reason = sanitize_url("https://example.com/trojan.exe")
        self.assertFalse(ok)
        self.assertIn("executable file download", reason.lower())

    def test_dictation_typing_sanitization(self):
        """Ensures dangerous terminal command strings cannot be typed into active apps."""
        # Safe dictation
        ok, text, _ = sanitize_typed_text("Hello Hashima, let's meet at 5pm!")
        self.assertTrue(ok)
        self.assertEqual(text, "Hello Hashima, let's meet at 5pm!")

        # Destructive script injection
        ok, _, reason = sanitize_typed_text("rm -rf /")
        self.assertFalse(ok)
        self.assertIn("hazardous shell", reason.lower())

        ok, _, reason = sanitize_typed_text("del /f /s C:\\*")
        self.assertFalse(ok)

    def test_end_to_end_execute_command_security_interception(self):
        """Verifies that execute_command blocks malicious requests and returns SECURITY_BLOCKED."""
        # OS destruction attempt
        res1 = execute_command("delete the operating system")
        self.assertFalse(res1.success)
        self.assertEqual(res1.intent, "SECURITY_BLOCKED")
        self.assertIn("security policy", res1.message.lower())

        # File deletion attempt
        res2 = execute_command("delete all my files")
        self.assertFalse(res2.success)
        self.assertEqual(res2.intent, "SECURITY_BLOCKED")

        # Unapproved app launch attempt
        res3 = execute_command("open app hacker_tool")
        self.assertFalse(res3.success)
        self.assertEqual(res3.intent, "SECURITY_BLOCKED")

        # Safe command should proceed normally
        res4 = execute_command("Can you please tell me like w how much RAM is occupied in my laptop?")
        self.assertTrue(res4.success)
        self.assertEqual(res4.intent, "SYSTEM_RAM")

    def test_security_audit_log_recorded(self):
        """Verifies that security audit records are logged in memory for intercepted commands."""
        events = get_recent_audit_events()
        self.assertTrue(any(e.get("outcome") == "BLOCKED" and "delete the operating system" in e.get("utterance", "") for e in events))

if __name__ == "__main__":
    unittest.main()

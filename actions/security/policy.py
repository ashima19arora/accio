"""
Accio Security Layer - Multi-Tier Risk & Permission Policy Engine
=================================================================
WHAT THIS FILE DOES (Simple English):
  This module assigns a risk level to every single action in Accio and decides whether
  the action is permitted or denied:
  - Tier 0 (Safe): Read-only status checks (RAM, Battery, Time, Date, Q&A, Volume).
  - Tier 1 (Standard): Safe web navigation, tab switching, page scrolling, and desktop controls.
  - Tier 2 (Caution): Window closing, tab closing, clipboard pasting, typing, and approved app opening.
  - Tier 3 (Elevated): Shutting down the assistant session.
  - Tier 4 (Forbidden): Destructive OS actions, file deletions, disk formatting, and shell injection.

GREAT TECH & ARCHITECTURE IN THIS FILE:
  - Risk Classification Enumeration (`RiskTier`):
      * What it does: Strict categorical tiers providing defense-in-depth before any action runs.
  - Policy Decision Engine (`evaluate_policy`):
      * What it does: Central decision function returning an immutable `PolicyDecision` object with
        cleared/sanitized parameters or an explicit denial reason.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Tuple
from .threat_detector import ThreatAssessment
from .sanitizer import (
    sanitize_url, 
    sanitize_app_target, 
    sanitize_typed_text, 
    sanitize_search_query
)

class RiskTier(Enum):
    TIER_0_SAFE = "SAFE"                 # Read-only queries, diagnostic info, volume
    TIER_1_STANDARD = "STANDARD"         # Safe web navigation, search, media control
    TIER_2_CAUTION = "CAUTION"           # Tab/window close, safe app launch, typing
    TIER_3_ELEVATED = "ELEVATED"         # Assistant termination, power/session actions
    TIER_4_FORBIDDEN = "FORBIDDEN"       # Destructive file/OS actions, shell injection

INTENT_TIERS: Dict[str, RiskTier] = {
    # Tier 0: Safe & Read-Only / Diagnostic / Knowledge
    "SYSTEM_RAM": RiskTier.TIER_0_SAFE,
    "SYSTEM_BATTERY": RiskTier.TIER_0_SAFE,
    "SYSTEM_CPU": RiskTier.TIER_0_SAFE,
    "SYSTEM_TIME": RiskTier.TIER_0_SAFE,
    "SYSTEM_DATE": RiskTier.TIER_0_SAFE,
    "VOLUME_UP": RiskTier.TIER_0_SAFE,
    "VOLUME_DOWN": RiskTier.TIER_0_SAFE,
    "VOLUME_MUTE": RiskTier.TIER_0_SAFE,
    "GREETING": RiskTier.TIER_0_SAFE,
    "WELLBEING_QUERY": RiskTier.TIER_0_SAFE,
    "IDENTITY_QUERY": RiskTier.TIER_0_SAFE,
    "CAPABILITIES_QUERY": RiskTier.TIER_0_SAFE,
    "KNOWLEDGE_QUERY": RiskTier.TIER_0_SAFE,
    "SCREEN_CONTEXT_QUERY": RiskTier.TIER_0_SAFE,

    # Tier 1: Standard Navigation & Controls
    "SEARCH_WEB": RiskTier.TIER_1_STANDARD,
    "OPEN_WEBSITE": RiskTier.TIER_1_STANDARD,
    "BROWSER_NEW_TAB": RiskTier.TIER_1_STANDARD,
    "BROWSER_SWITCH_TAB": RiskTier.TIER_1_STANDARD,
    "BROWSER_REFRESH": RiskTier.TIER_1_STANDARD,
    "BROWSER_REOPEN_TAB": RiskTier.TIER_1_STANDARD,
    "BROWSER_SCROLL_DOWN": RiskTier.TIER_1_STANDARD,
    "BROWSER_SCROLL_UP": RiskTier.TIER_1_STANDARD,
    "BROWSER_SCROLL_TOP": RiskTier.TIER_1_STANDARD,
    "BROWSER_SCROLL_BOTTOM": RiskTier.TIER_1_STANDARD,
    "BROWSER_ZOOM_IN": RiskTier.TIER_1_STANDARD,
    "BROWSER_ZOOM_OUT": RiskTier.TIER_1_STANDARD,
    "BROWSER_ZOOM_RESET": RiskTier.TIER_1_STANDARD,
    "BROWSER_GO_BACK": RiskTier.TIER_1_STANDARD,
    "BROWSER_GO_FORWARD": RiskTier.TIER_1_STANDARD,
    "BROWSER_OPEN_HISTORY": RiskTier.TIER_1_STANDARD,
    "BROWSER_OPEN_DOWNLOADS": RiskTier.TIER_1_STANDARD,
    "BROWSER_BOOKMARK": RiskTier.TIER_1_STANDARD,
    "BROWSER_FULLSCREEN": RiskTier.TIER_1_STANDARD,
    "BROWSER_FIND_ON_PAGE": RiskTier.TIER_1_STANDARD,
    "SHOW_DESKTOP": RiskTier.TIER_1_STANDARD,
    "WINDOW_MINIMIZE": RiskTier.TIER_1_STANDARD,
    "WINDOW_MAXIMIZE": RiskTier.TIER_1_STANDARD,
    "WINDOW_SWITCH": RiskTier.TIER_1_STANDARD,
    "WINDOW_SNAP_LEFT": RiskTier.TIER_1_STANDARD,
    "WINDOW_SNAP_RIGHT": RiskTier.TIER_1_STANDARD,
    "WINDOW_TASK_VIEW": RiskTier.TIER_1_STANDARD,
    "DESKTOP_SWITCH": RiskTier.TIER_1_STANDARD,
    "DESKTOP_NEW": RiskTier.TIER_1_STANDARD,
    "MEDIA_PLAY_PAUSE": RiskTier.TIER_1_STANDARD,
    "FORM_NEXT_FIELD": RiskTier.TIER_1_STANDARD,
    "FORM_PREV_FIELD": RiskTier.TIER_1_STANDARD,
    "FORM_TOGGLE_CHECKBOX": RiskTier.TIER_1_STANDARD,
    "SELECT_ALL": RiskTier.TIER_1_STANDARD,
    "COPY_TEXT": RiskTier.TIER_1_STANDARD,

    # Tier 2: Caution & State Altering
    "BROWSER_CLOSE_TAB": RiskTier.TIER_2_CAUTION,
    "WINDOW_CLOSE": RiskTier.TIER_2_CAUTION,
    "DESKTOP_CLOSE": RiskTier.TIER_2_CAUTION,
    "SCREENSHOT": RiskTier.TIER_2_CAUTION,
    "LOCK_SCREEN": RiskTier.TIER_2_CAUTION,
    "OPEN_APP": RiskTier.TIER_2_CAUTION,
    "TYPE_TEXT": RiskTier.TIER_2_CAUTION,
    "FORM_FILL_FIELD": RiskTier.TIER_2_CAUTION,
    "FORM_SUBMIT": RiskTier.TIER_2_CAUTION,
    "CLEAR_FIELD": RiskTier.TIER_2_CAUTION,
    "PASTE_TEXT": RiskTier.TIER_2_CAUTION,
    "UNDO_ACTION": RiskTier.TIER_2_CAUTION,
    "SEND_MESSAGE": RiskTier.TIER_2_CAUTION,
    "TYPE_AND_SEND": RiskTier.TIER_2_CAUTION,
    "CREATE_FILE": RiskTier.TIER_2_CAUTION,
    "COMPOUND_OPEN_AND_TYPE": RiskTier.TIER_2_CAUTION,

    # Tier 3: Elevated
    "EXIT_ASSISTANT": RiskTier.TIER_3_ELEVATED,
}

@dataclass
class PolicyDecision:
    allowed: bool
    risk_tier: RiskTier
    reason: str
    sanitized_params: Dict[str, Any]

def evaluate_policy(intent_name: str, params: Dict[str, Any], threat: ThreatAssessment) -> PolicyDecision:
    """
    Evaluates system policy against the intent, sanitized parameters, and threat level.
    """
    # 1. Immediate Interception if Lexical Threat Detected
    if threat.is_threat:
        return PolicyDecision(
            allowed=False,
            risk_tier=RiskTier.TIER_4_FORBIDDEN,
            reason=f"Restricted by Threat Guardrail: {threat.reason}",
            sanitized_params=params
        )

    # 2. Unknown or Unregistered Intent
    if intent_name == "UNKNOWN":
        return PolicyDecision(
            allowed=False,
            risk_tier=RiskTier.TIER_0_SAFE,
            reason="Unrecognized command.",
            sanitized_params=params
        )

    tier = INTENT_TIERS.get(intent_name, RiskTier.TIER_2_CAUTION)
    sanitized = dict(params)

    # 3. Intent-Specific Parameter Validation & Sanitization

    # Application Launching
    if intent_name == "OPEN_APP":
        app_name = sanitized.get("app_name", "")
        ok, verified_target, reason = sanitize_app_target(app_name)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["verified_target"] = verified_target

    # Web Navigation
    elif intent_name == "OPEN_WEBSITE":
        target = sanitized.get("target", "")
        ok, safe_url, reason = sanitize_url(target)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["target"] = safe_url

    # Web Searching
    elif intent_name == "SEARCH_WEB":
        query = sanitized.get("query", "")
        ok, clean_query, reason = sanitize_search_query(query)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["query"] = clean_query

    # Text Dictation
    elif intent_name == "TYPE_TEXT":
        text_val = sanitized.get("text", "")
        ok, clean_text, reason = sanitize_typed_text(text_val)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["text"] = clean_text

    # Compound Open and Type
    elif intent_name == "COMPOUND_OPEN_AND_TYPE":
        text_val = sanitized.get("text_to_type", "")
        ok, clean_text, reason = sanitize_typed_text(text_val)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["text_to_type"] = clean_text

    # Form Filling & Type and Send
    elif intent_name in ("FORM_FILL_FIELD", "TYPE_AND_SEND"):
        text_val = sanitized.get("text", "")
        ok, clean_text, reason = sanitize_typed_text(text_val)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["text"] = clean_text

    # Find on Page & Knowledge Query
    elif intent_name in ("BROWSER_FIND_ON_PAGE", "KNOWLEDGE_QUERY"):
        query_val = sanitized.get("query", "")
        ok, clean_query, reason = sanitize_search_query(query_val)
        if not ok:
            return PolicyDecision(
                allowed=False,
                risk_tier=RiskTier.TIER_4_FORBIDDEN,
                reason=reason,
                sanitized_params=sanitized
            )
        sanitized["query"] = clean_query

    # File Creation Parameter Sanitization
    elif intent_name == "CREATE_FILE":
        from ..file_actions import sanitize_file_name
        raw_fname = sanitized.get("filename", "New Note")
        safe_fname = sanitize_file_name(raw_fname)
        sanitized["filename"] = safe_fname
        sanitized["location"] = sanitized.get("location", "desktop").lower()

    # Action is permitted under its risk tier
    return PolicyDecision(
        allowed=True,
        risk_tier=tier,
        reason=f"Action cleared policy verification under {tier.value} tier.",
        sanitized_params=sanitized
    )

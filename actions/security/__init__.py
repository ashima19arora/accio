"""
Accio Security Guardrail Package - Multi-Layer Defense System
=============================================================
WHAT THIS FILE DOES (Simple English):
  This is the security "firewall" and gatekeeper of Accio. Before any command touches
  your operating system, browser, or files, it passes through this unified gatekeeper.
  It screens for harmful words (like "delete windows", "format drive", "wipe files"),
  validates that requested apps are on the safety whitelist, blocks unsafe URL protocols,
  and records an in-memory safety log. If a command is dangerous, Accio blocks it immediately
  and warns you out loud.

GREAT TECH & CONCEPTS IN THIS PACKAGE:
  - Multi-Tier Risk Evaluation (Tiers 0 to 4):
      * What it does: Classifies commands into Safe, Standard, Caution, Elevated, or Forbidden.
  - Parameter Sandboxing:
      * What it does: Validates that inputs cannot break out of their intended sandbox.
"""

from typing import Tuple, Dict, Any
from .threat_detector import analyze_threat, ThreatAssessment
from .sanitizer import (
    sanitize_url, 
    sanitize_app_target, 
    sanitize_typed_text, 
    sanitize_search_query,
    APPROVED_APPLICATIONS,
    BLOCKED_SCHEMES,
)
from .policy import RiskTier, PolicyDecision, evaluate_policy
from .audit_logger import log_security_event

def verify_action_security(transcription: str, parsed_intent: Any) -> Tuple[bool, str, Dict[str, Any], str]:
    """
    Unified end-to-end security gatekeeper.
    Performs:
    1. Lexical Threat Assessment on raw transcript
    2. Policy & Risk Tier Evaluation
    3. Parameter Sandboxing (URLs, Apps, Dictation text)
    4. Immutable Security Audit Logging
    
    Returns:
        (is_allowed, risk_tier, sanitized_params, reason)
    """
    # 1. Threat Analysis
    threat = analyze_threat(transcription)

    # 2. Policy Evaluation & Parameter Sanitization
    intent_name = getattr(parsed_intent, "name", "UNKNOWN")
    raw_params = getattr(parsed_intent, "params", {})

    decision = evaluate_policy(intent_name, raw_params, threat)

    outcome = "ALLOWED" if decision.allowed else "BLOCKED"
    tier_str = decision.risk_tier.value

    # 3. Log to Security Audit Trail
    log_security_event(
        transcription=transcription,
        intent=intent_name,
        risk_tier=tier_str,
        outcome=outcome,
        reason=decision.reason,
        details={"threat_detected": threat.is_threat, "severity": threat.severity}
    )

    return decision.allowed, tier_str, decision.sanitized_params, decision.reason

__all__ = [
    "analyze_threat",
    "ThreatAssessment",
    "sanitize_url",
    "sanitize_app_target",
    "sanitize_typed_text",
    "sanitize_search_query",
    "APPROVED_APPLICATIONS",
    "BLOCKED_SCHEMES",
    "RiskTier",
    "PolicyDecision",
    "evaluate_policy",
    "log_security_event",
    "verify_action_security",
]

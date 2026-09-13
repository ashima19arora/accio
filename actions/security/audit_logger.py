"""
Accio Security Layer - In-Memory Security Audit Logger
======================================================
WHAT THIS FILE DOES (Simple English):
  This module keeps a record of all security decisions (which commands were permitted
  and which were blocked as hazardous). To keep your project directory clean and lightweight,
  it stores events in an in-memory buffer (`RECENT_AUDIT_EVENTS`) without writing files to disk.
  If an enterprise administrator ever needs persistent file logs, they can easily set the
  `ACCIO_AUDIT_LOG_FILE` environment variable.

GREAT TECH & PATTERNS IN THIS FILE:
  - In-Memory Circular Buffer:
      * What it does: Retains the latest 100 security events in RAM.
      * Why we use it: Zero disk I/O overhead, zero project clutter, and fast inspection for tests.
  - Python Logging Framework:
      * What it does: Standard Python `logging.Logger` with `NullHandler` by default.
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

# In-memory circular event buffer (zero disk clutter)
MAX_AUDIT_EVENTS = 100
RECENT_AUDIT_EVENTS: List[Dict[str, Any]] = []

AUDIT_LOG_FILE: Optional[str] = os.environ.get("ACCIO_AUDIT_LOG_FILE", None)

def _get_logger() -> logging.Logger:
    logger = logging.getLogger("AccioSecurityAudit")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        # If an explicit log file path is configured via environment variable, write to it
        if AUDIT_LOG_FILE:
            log_dir = os.path.dirname(AUDIT_LOG_FILE)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handler = logging.FileHandler(AUDIT_LOG_FILE, encoding="utf-8")
            formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        else:
            logger.addHandler(logging.NullHandler())
    return logger

def log_security_event(
    transcription: str,
    intent: str,
    risk_tier: str,
    outcome: str,  # "ALLOWED", "BLOCKED", "FLAGGED"
    reason: str,
    details: Optional[dict] = None
) -> None:
    """
    Records a structured security audit entry in memory and to optional log stream.
    """
    try:
        event = {
            "timestamp": datetime.now().isoformat(),
            "utterance": transcription,
            "intent": intent,
            "tier": risk_tier,
            "outcome": outcome,
            "reason": reason,
        }
        if details:
            event["details"] = details

        # Record in memory
        RECENT_AUDIT_EVENTS.append(event)
        if len(RECENT_AUDIT_EVENTS) > MAX_AUDIT_EVENTS:
            RECENT_AUDIT_EVENTS.pop(0)

        # Log via standard logging
        logger = _get_logger()
        line = json.dumps(event, ensure_ascii=False)
        if outcome == "BLOCKED":
            logger.warning(line)
        else:
            logger.info(line)
    except Exception as e:
        print(f"[Audit Log Warning] Could not record security event: {e}")

def get_recent_audit_events() -> List[Dict[str, Any]]:
    """
    Returns a copy of recorded security events.
    """
    return list(RECENT_AUDIT_EVENTS)

def clear_audit_events() -> None:
    """
    Clears recorded security events (primarily for testing).
    """
    RECENT_AUDIT_EVENTS.clear()

"""
Accio Security Layer - Lexical Threat & Destruction Detector
============================================================
WHAT THIS FILE DOES (Simple English):
  This is Accio's "early-warning radar". When a user speaks, this module scans the raw
  speech for hazardous or destructive patterns (like "format C:", "delete windows",
  "erase all my files", "rm -rf", or shell injection attacks). If a threat pattern is
  detected, it immediately stops the request before it can ever reach the computer's OS.

GREAT TECH & PATTERNS IN THIS FILE:
  - Lexical Threat Heuristics:
      * What it does: Fast compiled regular expressions matching known system destruction syntax.
      * Why we use it: Catches accidental or malicious speech instructions with 0 latency.
"""

import re
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ThreatAssessment:
    is_threat: bool
    category: Optional[str] = None
    severity: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None

# High-risk destructive commands and keywords that are permanently forbidden
DESTRUCTIVE_OS_PATTERNS = [
    # OS & System destruction
    r'\b(?:delete|destroy|wipe|erase|remove|kill)\s+(?:(?:the|my|this)\s+)?(?:os|operating\s+system|windows|system32|hard\s*drive|partition|disk)\b',
    r'\b(?:format|zero|clean)\s+(?:(?:the|my|this)\s+)?(?:c(?::|\s+drive)?|drive\s+c|disk|hard\s*drive|volume|partition)\b',
    r'\b(?:format-volume|diskpart|clean\s+all)\b',

    # File and directory mass deletion
    r'\b(?:delete|remove|erase|wipe|destroy|shred|unlink)\s+(?:all\s+)?(?:my\s+)?(?:files|documents|folders|directory|directories|data|desktop|user\s+data|pictures|downloads)\b',
    r'\b(?:del|erase)\s+(?:/[a-zA-Z\s]+)?[\*\\/]',
    r'\b(?:rmdir|rd)\s+(?:/[a-zA-Z\s]+)?',
    r'\brm\s+-(?:r|f|rf|fr)\b',
    r'\bremove-item\s+(?:-recurse|-force)\b',

    # Arbitrary shell execution and privilege tampering
    r'\b(?:cmd(?:\.exe)?|powershell(?:\.exe)?|pwsh)\s+(?:/c|/k|-c|-command|-enc|-encodedcommand)\b',
    r'\b(?:reg\s+(?:delete|add)|regedit)\b',
    r'\b(?:takeown|icacls|cacls)\b',
    r'\b(?:net\s+(?:user|localgroup|stop))\b',
    r'\b(?:taskkill|tskill)\s+(?:/f|/im|/pid)\b',
    r'\b(?:rundll32|mshta|certutil|bitsadmin)\b',
    r'\b(?:curl|wget)\s+.*\b(?:\|\s*(?:bash|sh|cmd|powershell))\b',

    # Fork bombs and severe denial of service
    r':\(\)\s*\{\s*:\|:&\s*\};:',
    r'%\d+\s*\|\s*%\d+',
]

# File tampering keywords
FILE_TAMPER_PATTERNS = [
    r'\b(?:delete|remove|erase|wipe|trash)\s+(?:the\s+)?(?:file|folder|dir|item|document|script)\b',
    r'\b(?:delete|remove)\s+[a-zA-Z0-9_\-\.]+\.(?:exe|dll|sys|bat|cmd|ps1|ini|cfg|env|txt|doc|pdf)\b',
]

def analyze_threat(transcription: str) -> ThreatAssessment:
    """
    Performs deep lexical and pattern-based analysis of the input utterance.
    Returns a ThreatAssessment detailing if the request is safe or hazardous.
    """
    if not transcription or not transcription.strip():
        return ThreatAssessment(is_threat=False, severity="LOW")

    text = transcription.lower().strip()

    # 1. Critical OS & Storage Destruction Check
    for pattern in DESTRUCTIVE_OS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return ThreatAssessment(
                is_threat=True,
                category="CRITICAL_DESTRUCTION",
                severity="CRITICAL",
                reason="Destructive OS, partition, or shell execution detected.",
                matched_pattern=match.group(0)
            )

    # 2. File & Folder Tampering Check
    for pattern in FILE_TAMPER_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return ThreatAssessment(
                is_threat=True,
                category="FILE_MODIFICATION",
                severity="HIGH",
                reason="File or directory deletion instruction detected.",
                matched_pattern=match.group(0)
            )

    return ThreatAssessment(
        is_threat=False,
        severity="LOW",
        reason="Clean utterance passing all lexical threat filters."
    )

"""
Accio Security Layer - Parameter & Sandbox Sanitizer
====================================================
WHAT THIS FILE DOES (Simple English):
  This module enforces strict safety boundaries on parameters passed to Accio:
  1. Application Whitelisting: Accio can ONLY launch approved applications (Notepad, Calculator,
     Paint, Explorer, WhatsApp, standard browsers). Launching arbitrary binaries or shell prompts (cmd, powershell) is permanently blocked.
  2. Web URL Isolation: Blocks dangerous URL protocols (`file://`, `javascript:`, `res:`), prevents
     navigation to private local IP ranges (`127.0.0.1`, `192.168.x.x`), and blocks executable downloads (`.exe`, `.bat`, `.vbs`).
  3. Dictation Sanitization: Ensures that dictated text does not inject destructive terminal scripts.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - ipaddress:
      * What it does: Validates IP address types (loopback, private, reserved, link-local).
      * Why we use it: Prevents Server-Side Request Forgery (SSRF) and local router tampering.
  - urllib.parse:
      * What it does: Standard URL syntax parsing and protocol verification.
"""

import re
import ipaddress
import urllib.parse
from typing import Tuple, Dict

# Strict whitelist of approved applications that Accio is permitted to launch
APPROVED_APPLICATIONS: Dict[str, str] = {
    'notepad': 'notepad.exe',
    'calculator': 'calc.exe',
    'calc': 'calc.exe',
    'paint': 'mspaint.exe',
    'mspaint': 'mspaint.exe',
    'explorer': 'explorer.exe',
    'files': 'explorer.exe',
    'file explorer': 'explorer.exe',
    'settings': 'ms-settings:',
    'whatsapp': 'whatsapp:',
    'chrome': 'chrome.exe',
    'google chrome': 'chrome.exe',
    'edge': 'msedge.exe',
    'microsoft edge': 'msedge.exe',
    'firefox': 'firefox.exe',
    'spotify': 'spotify.exe',
    'word': 'winword.exe',
    'excel': 'excel.exe',
    'powerpoint': 'powerpnt.exe',
}

# Blocked protocol schemes that could trigger local code execution or data leakage
BLOCKED_SCHEMES = {
    'file', 'javascript', 'data', 'vbscript', 'about', 'blob', 
    'shell', 'res', 'ms-appinstaller', 'disk'
}

# Blocked file download extensions in URLs
DANGEROUS_DOWNLOAD_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.ps1', '.vbs', '.msi', '.scr',
    '.jar', '.iso', '.dll', '.reg', '.com', '.pif', '.hta'
}

# Blocked script execution patterns inside dictated text
DANGEROUS_TYPING_PATTERNS = [
    r'\b(?:rm\s+-(?:r|f|rf|fr)|del\s+.*?\*|del\s+/[a-zA-Z\s]+|format\s+[a-zA-Z]:|rmdir\s+/s)\b',
    r'\b(?:powershell(?:\.exe)?|cmd(?:\.exe)?)\s+(?:/c|-c|-enc)\b',
    r'\b(?:Remove-Item\s+-Recurse|Stop-Computer|Restart-Computer)\b',
    r'\b(?:DROP\s+DATABASE|DROP\s+TABLE|DELETE\s+FROM)\b',
]

COMMON_WEB_SITES = {
    'google': 'https://www.google.com',
    'youtube': 'https://www.youtube.com',
    'github': 'https://www.github.com',
    'gmail': 'https://mail.google.com',
    'reddit': 'https://www.reddit.com',
    'wikipedia': 'https://www.wikipedia.org',
    'twitter': 'https://www.x.com',
    'x': 'https://www.x.com',
    'linkedin': 'https://www.linkedin.com',
    'chatgpt': 'https://chatgpt.com',
    'netflix': 'https://www.netflix.com',
    'amazon': 'https://www.amazon.com',
    'maps': 'https://maps.google.com',
    'news': 'https://news.google.com',
    'whatsapp': 'https://web.whatsapp.com',
    'whatsapp web': 'https://web.whatsapp.com',
}

def sanitize_url(raw_url: str) -> Tuple[bool, str, str]:
    """
    Validates and sanitizes a URL before browser navigation.
    Resolves common site names, enforces HTTPS, and prevents protocol/host exploits.
    Returns: (is_safe, sanitized_url, reason)
    """
    if not raw_url or not raw_url.strip():
        return False, "", "Empty URL provided."

    cleaned = raw_url.strip()

    # Resolve common site names (e.g. 'youtube', 'whatsapp web')
    target_key = cleaned.lower()
    # Strip optional "the " prefix
    if target_key.startswith("the "):
        target_key = target_key[4:].strip()

    if target_key in COMMON_WEB_SITES:
        cleaned = COMMON_WEB_SITES[target_key]
    elif not cleaned.startswith(('http://', 'https://', 'file://', 'javascript:')):
        if '.' in cleaned and not cleaned.startswith('/'):
            cleaned = f"https://{cleaned}"
        elif re.match(r'^[a-zA-Z0-9_\-]+$', cleaned):
            cleaned = f"https://www.{cleaned}.com"
        else:
            # Multi-word query intended for browser search
            encoded = urllib.parse.quote_plus(cleaned)
            cleaned = f"https://www.google.com/search?q={encoded}"

    parsed = urllib.parse.urlparse(cleaned)
    scheme = parsed.scheme.lower()

    # 1. Scheme Validation
    if scheme in BLOCKED_SCHEMES:
        return False, "", f"Forbidden URL scheme '{scheme}:' blocked for security."

    if scheme not in ('http', 'https'):
        return False, "", f"Unauthorized URL protocol '{scheme}'. Only HTTP/HTTPS allowed."

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        return False, "", "URL missing valid hostname."

    # 2. Loopback & Private Network Isolation
    if hostname in ('localhost', '127.0.0.1', '::1', '0.0.0.0'):
        return False, "", f"Navigation to local loopback host '{hostname}' is restricted."

    # Check IP addresses against private / link-local / loopback networks
    try:
        ip = ipaddress.ip_address(hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            return False, "", f"Navigation to private/local network IP '{hostname}' is restricted."
    except ValueError:
        # Not a raw IP address; hostname string is acceptable
        pass

    # 3. Block Dangerous Executable File Downloads
    path_lower = parsed.path.lower()
    for ext in DANGEROUS_DOWNLOAD_EXTENSIONS:
        if path_lower.endswith(ext):
            return False, "", f"Direct navigation to executable file download ('{ext}') is blocked."

    return True, cleaned, "URL is safe and verified."

def sanitize_app_target(app_name: str) -> Tuple[bool, str, str]:
    """
    Validates application name against the approved safe whitelist.
    Returns: (is_allowed, verified_target, reason)
    """
    if not app_name or not app_name.strip():
        return False, "", "Empty application name."

    clean_name = app_name.lower().strip()
    # Strip common leading words like "open "
    clean_name = re.sub(r'^(?:open|launch)\s+', '', clean_name).strip()

    if clean_name in APPROVED_APPLICATIONS:
        return True, APPROVED_APPLICATIONS[clean_name], f"Approved application: {clean_name}"

    # Disallowed / unverified app
    return (
        False, 
        "", 
        f"Application '{app_name}' is not in the approved safety whitelist. Launch restricted."
    )

def sanitize_typed_text(text: str) -> Tuple[bool, str, str]:
    """
    Inspects text to prevent injection of destructive terminal commands.
    Returns: (is_safe, sanitized_text, reason)
    """
    if not text:
        return True, "", "Empty text."

    for pattern in DANGEROUS_TYPING_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return False, "", f"Typing blocked: contains hazardous shell or database script pattern ('{match.group(0)}')."

    return True, text, "Text content verified safe."

def sanitize_search_query(query: str) -> Tuple[bool, str, str]:
    """
    Cleans search query to avoid command separator injection.
    Returns: (is_safe, sanitized_query, reason)
    """
    if not query or not query.strip():
        return False, "", "Empty search query."

    # Strip dangerous shell operators if present
    cleaned = re.sub(r'[;&|`$><]+', ' ', query).strip()
    return True, cleaned, "Search query sanitized."

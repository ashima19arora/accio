"""
Accio OpenRouter Intelligence Layer - High-Performance Multi-Key Voice Engine
==============================================================================
WHAT THIS FILE DOES (Simple English):
  This module connects Accio to fast OpenRouter AI models for instant knowledge Q&A
  and intelligent conversation. It pools multiple API keys with automatic, instantaneous
  failover: if one key is rate-limited (429) or busy, it immediately switches to the next
  key so the user never experiences delays. It sanitizes all responses into clean, natural
  spoken sentences formatted specifically for offline voice audio output (TTS).

KEY ARCHITECTURE & SAFETY:
  - NVIDIA NeMo Parakeet ASR continues to handle all local Speech-to-Text offline.
  - Multi-Key Circuit Breaker: Automatically rotates across healthy keys.
  - Model Cascading: Primary ultra-low-latency model with resilient fallback models.
  - Voice Optimization: Removes thinking blocks, markdown bolding, bullets, and citations.
  - In-Memory Response Cache: Sub-millisecond instant answers for repeated queries.
"""

import os
import re
import time
import json
import threading
from typing import Optional, List, Dict, Any
import requests
from dotenv import load_dotenv

# Load environment variables from workspace root
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
load_dotenv(os.path.join(PROJECT_ROOT, 'server', '.env'))

# Fallback built-in keys if .env is missing or empty (keep empty in source code for security)
DEFAULT_KEYS: List[str] = []

class KeyFailoverManager:
    """Manages a pool of OpenRouter API keys with automatic failover and temporary backoff."""

    def __init__(self, keys: List[str], cooldown_seconds: float = 30.0):
        self.keys = [k.strip() for k in keys if k.strip()]
        self.cooldown_seconds = cooldown_seconds
        self.key_cooldowns: Dict[str, float] = {}
        self.current_index = 0
        self.lock = threading.Lock()

    def get_candidate_keys(self) -> List[str]:
        """Returns all keys ordered starting from the current index, prioritizing healthy keys."""
        with self.lock:
            now = time.time()
            # Clean expired cooldowns
            for k in list(self.key_cooldowns.keys()):
                if now >= self.key_cooldowns[k]:
                    del self.key_cooldowns[k]

            if not self.keys:
                return []

            # Rotate keys starting from current index
            n = len(self.keys)
            ordered = [self.keys[(self.current_index + i) % n] for i in range(n)]

            # Put non-cooling keys first
            healthy = [k for k in ordered if k not in self.key_cooldowns]
            cooling = [k for k in ordered if k in self.key_cooldowns]
            return healthy + cooling

    def mark_failure(self, key: str, status_code: int = 429):
        """Puts a key on cooldown and advances the primary pointer."""
        with self.lock:
            # 429 (Rate Limit) gets cooldown, other errors brief backoff
            penalty = self.cooldown_seconds if status_code == 429 else 10.0
            self.key_cooldowns[key] = time.time() + penalty
            if self.keys and key == self.keys[self.current_index % len(self.keys)]:
                self.current_index = (self.current_index + 1) % len(self.keys)

    def mark_success(self, key: str):
        """Clears any cooldown and keeps key active."""
        with self.lock:
            if key in self.key_cooldowns:
                del self.key_cooldowns[key]

# Initialize Global Key Manager
raw_keys_env = os.getenv("OPENROUTER_API_KEYS", "")
parsed_keys = [k.strip() for k in raw_keys_env.split(",") if k.strip()]
_key_pool = parsed_keys if parsed_keys else DEFAULT_KEYS
key_manager = KeyFailoverManager(_key_pool)

# Models configuration
PRIMARY_MODEL = os.getenv("OPENROUTER_PRIMARY_MODEL", "nex-agi/nex-n2.5-mini:free")
raw_fallbacks = os.getenv("OPENROUTER_FALLBACK_MODELS", "dots-studio/dots-3-note-preview:free,liquid/lfm-2.5-2.6b:free,google/gemma-4-26b-a4b-it:free")
FALLBACK_MODELS = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]
TIMEOUT_SEC = float(os.getenv("OPENROUTER_TIMEOUT_SEC", "4.5"))

# In-Memory Q&A LRU Cache
_cache_lock = threading.Lock()
_qa_cache: Dict[str, str] = {}
MAX_CACHE_ITEMS = 200

def clean_for_speech_output(text: str) -> str:
    """
    Transforms raw LLM output into clean, natural spoken speech for TTS audio synthesis.
    Strips reasoning tokens, markdown formatting, bullet points, citations, and formulas.
    """
    if not text:
        return ""

    cleaned = text.strip()

    # 1. Strip <think>...</think> or reasoning blocks
    cleaned = re.sub(r'<think>.*?</think>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r'Here\'?s\s+a\s+thinking\s+process:.*?(?=\n\n|\Z)', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

    # 2. Remove markdown code blocks and inline code
    cleaned = re.sub(r'```.*?```', '', cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'`([^`]+)`', r'\1', cleaned)

    # 3. Remove markdown headers entirely (e.g. "### Summary\n")
    cleaned = re.sub(r'^#{1,6}\s+.*$', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'[*_~]', '', cleaned)

    # 4. Remove markdown bullet points and numbered list markers
    cleaned = re.sub(r'^\s*[-*•]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)

    # 5. Remove citations like [1], [2], [citation needed]
    cleaned = re.sub(r'\[\d+\]', '', cleaned)
    cleaned = re.sub(r'\[.*?\]\(.*?\)', '', cleaned)

    # 6. Replace LaTeX math symbols or special characters
    cleaned = re.sub(r'\$(.*?)\$', r'\1', cleaned)

    # 7. Normalize multiple whitespaces and punctuation spacing
    cleaned = re.sub(r'\s+([.,;:!?])', r'\1', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # 8. Limit length for conversational voice delivery (maximum ~2-3 sentences)
    sentences = re.split(r'(?<=[.!?])\s+', cleaned)
    if len(sentences) > 3:
        cleaned = ' '.join(sentences[:3])

    return cleaned

def ask_accio_llm(prompt: str, lang: str = 'en', timeout: float = TIMEOUT_SEC) -> Optional[str]:
    """
    Queries OpenRouter models with multi-key failover and model cascading.
    Returns a concise, voice-optimized spoken response or None if offline.
    """
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return None

    cache_key = f"{lang}:{clean_prompt.lower()}"
    with _cache_lock:
        if cache_key in _qa_cache:
            return _qa_cache[cache_key]

    # Prepare voice-tailored system prompt
    if lang == 'hi':
        system_content = (
            "आप Accio वॉइस असिस्टेंट हैं। उपयोगकर्ता के सवाल का उत्तर सीधा, स्पष्ट और प्राकृतिक बोलचाल "
            "के 1 से 2 वाक्यों में दें। बुलेट पॉइंट, मार्कडाउन (*, #), या प्रतीकों का उपयोग बिल्कुल न करें।"
        )
    else:
        system_content = (
            "You are Accio, a fast voice digital accessibility assistant. Answer directly and concisely "
            "in 1 to 2 spoken sentences. Do not use markdown, asterisks, bullet points, or citations. "
            "Speak naturally as if talking out loud."
        )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": clean_prompt}
    ]

    candidate_models = [PRIMARY_MODEL] + [m for m in FALLBACK_MODELS if m != PRIMARY_MODEL]
    candidate_keys = key_manager.get_candidate_keys()

    if not candidate_keys:
        return None

    # Cascade through models and keys
    for model_name in candidate_models:
        for api_key in candidate_keys:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://accio.local",
                "X-Title": "Accio Voice Assistant"
            }
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 150,
                "temperature": 0.3
            }

            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices:
                        raw_content = choices[0].get("message", {}).get("content", "")
                        spoken_answer = clean_for_speech_output(raw_content)
                        if spoken_answer:
                            key_manager.mark_success(api_key)
                            # Cache answer
                            with _cache_lock:
                                if len(_qa_cache) >= MAX_CACHE_ITEMS:
                                    _qa_cache.pop(next(iter(_qa_cache)))
                                _qa_cache[cache_key] = spoken_answer
                            return spoken_answer

                elif response.status_code in (429, 401, 403):
                    # Rate limit or auth error -> mark key failed and try next key immediately
                    key_manager.mark_failure(api_key, status_code=response.status_code)
                    continue

                elif response.status_code in (404, 502, 503):
                    # Model not available on OpenRouter -> break to next model
                    break

            except (requests.Timeout, requests.RequestException):
                # Network or timeout error on this key -> try next key
                key_manager.mark_failure(api_key, status_code=504)
                continue

    return None

def ask_screen_context_llm(user_question: str, screen_ctx: Dict[str, Any], lang: str = 'en', timeout: float = 5.0) -> str:
    """
    Synthesizes active screen context (active application, window title, clipboard text,
    running apps list, and optional visual snapshot) to provide an intelligent, voice-optimized answer.

    When no screenshot is available (GPU compositing blocks pixel capture), uses rich
    process metadata to provide accurate context instead of sending black images.
    """
    app_name = screen_ctx.get("app_name", "Desktop Window")
    window_title = screen_ctx.get("window_title", "")
    clipboard_text = screen_ctx.get("clipboard_snippet", "")
    has_image = screen_ctx.get("has_image", False)
    image_b64 = screen_ctx.get("image_base64", "")
    running_apps = screen_ctx.get("running_apps", "")
    screenshot_available = screen_ctx.get("screenshot_available", False)

    # Build rich system instruction with all available metadata
    if lang == 'hi':
        system_content = (
            "आप Accio वॉइस असिस्टेंट हैं। उपयोगकर्ता अपनी कंप्यूटर स्क्रीन को देख रहा है। "
            f"एक्टिव एप्लिकेशन: '{app_name}'"
        )
        if window_title:
            system_content += f", विंडो टाइटल: '{window_title}'"
        if running_apps:
            system_content += f"। अन्य चल रहे ऐप्स: {running_apps}"
        system_content += (
            "। उपयोगकर्ता के सवाल का उत्तर 1 से 2 स्पष्ट, प्राकृतिक बोलचाल के वाक्यों में दें। "
            "मार्कडाउन या बुलेट पॉइंट का उपयोग बिल्कुल न करें।"
        )
    else:
        system_content = (
            "You are Accio, a voice accessibility assistant. The user is looking at their computer screen. "
            f"Currently active application: '{app_name}'"
        )
        if window_title:
            system_content += f", Window title: '{window_title}'"
        if running_apps:
            system_content += f". Other running apps: {running_apps}"
        if not screenshot_available:
            system_content += (
                ". NOTE: A visual screenshot could not be captured due to GPU compositing restrictions, "
                "but the metadata about the active application and running processes is accurate. "
                "Answer based on the application and window metadata provided."
            )
        system_content += (
            ". Provide a direct, concise, and helpful spoken answer in 1 to 2 conversational sentences. "
            "Do not use markdown formatting, bullet points, or asterisks. Speak clearly for audio playback."
        )

    # Build detailed contextual user prompt
    context_parts = [f"I am currently using {app_name}"]
    if window_title:
        context_parts.append(f"with the window title: \"{window_title}\"")
    if running_apps:
        context_parts.append(f"Other apps running on my computer: {running_apps}")
    if clipboard_text:
        context_parts.append(f"Text currently in my clipboard: \"{clipboard_text}\"")

    user_content_text = f"Context: {'. '.join(context_parts)}. Question: {user_question}"

    candidate_keys = key_manager.get_candidate_keys()

    # 1. Attempt Multimodal Vision if a valid (non-black) snapshot is available
    if has_image and image_b64 and screenshot_available:
        for api_key in candidate_keys[:2]:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://accio.local",
                    "X-Title": "Accio Screen Lens"
                }
                payload = {
                    "model": "inclusionai/ling-3.0-flash-vl:free",
                    "messages": [
                        {"role": "system", "content": system_content},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": user_content_text},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                            ]
                        }
                    ],
                    "max_tokens": 150,
                    "temperature": 0.3
                }
                resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        raw = choices[0].get("message", {}).get("content", "")
                        clean = clean_for_speech_output(raw)
                        if clean:
                            key_manager.mark_success(api_key)
                            return clean
                elif resp.status_code in (429, 401, 403):
                    key_manager.mark_failure(api_key, status_code=resp.status_code)
            except Exception:
                pass

    # 2. Text-Based Context Reasoning with Primary Model
    for model_name in [PRIMARY_MODEL] + FALLBACK_MODELS:
        for api_key in candidate_keys:
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://accio.local",
                    "X-Title": "Accio Screen Lens"
                }
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_content},
                        {"role": "user", "content": user_content_text}
                    ],
                    "max_tokens": 150,
                    "temperature": 0.3
                }
                resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        raw = choices[0].get("message", {}).get("content", "")
                        clean = clean_for_speech_output(raw)
                        if clean:
                            key_manager.mark_success(api_key)
                            return clean
                elif resp.status_code in (429, 401, 403):
                    key_manager.mark_failure(api_key, status_code=resp.status_code)
                    continue
                elif resp.status_code in (404, 502, 503):
                    break
            except Exception:
                continue

    # 3. Graceful Local Fallback (Always returns a helpful answer, never crashes)
    if window_title:
        if lang == 'hi':
            return f"आपकी स्क्रीन पर {app_name} खुला है, जिसका टाइटल {window_title} है।"
        return f"You are currently in {app_name} viewing {window_title}."
    elif running_apps:
        if lang == 'hi':
            return f"आपकी स्क्रीन पर {app_name} खुला है। अन्य चल रहे ऐप्स: {running_apps}।"
        return f"You are currently using {app_name}. Other running apps: {running_apps}."
    else:
        if lang == 'hi':
            return f"आपकी स्क्रीन पर {app_name} खुला है।"
        return f"You are currently on your desktop looking at {app_name}."



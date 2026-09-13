"""
Accio Knowledge & Instant Q&A Actions Module
============================================
WHAT THIS FILE DOES (Simple English):
  This module allows users to ask factual questions (e.g., "What is photosynthesis?",
  "Who is Albert Einstein?", "Tell me about Mars") and immediately hear a short,
  concise 1-2 sentence answer spoken aloud. This is vital for users with visual
  impairments or reading difficulties who cannot read wall-of-text articles on screen.
  If an exact instant answer is not found, it gracefully opens web search results.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - requests:
      * What it does: Performs fast HTTP network requests.
      * Why we use it: Fetches instant factual summaries from open web endpoints in under 500ms.
      * Benefit: Completely hands-free factual Q&A without opening bloated browser tabs.
  - Wikipedia REST API (v1 /page/summary):
      * What it does: Returns concise, curated lead paragraphs for millions of encyclopedic topics.
      * Why we use it: Zero API key required, zero tracking, high uptime, and highly accurate.
  - DuckDuckGo Instant Answer API:
      * What it does: Zero-click answer extraction for definitions, calculations, and quick facts.
      * Why we use it: Provides a reliable secondary knowledge fallback with zero cost.
"""

import re
import urllib.parse
import requests
from .feedback import speak, notify
from .browser_actions import search_web

USER_AGENT = "AccioVoiceAssistant/1.0 (Windows NT 10.0; Win64; x64)"

def clean_knowledge_text(raw_text: str) -> str:
    """
    Cleans raw encyclopedia text for natural spoken speech.
    Removes parenthetical pronunciation symbols, birth/death year clutter, and citation tags.
    Extracts at most 2 clean, punchy sentences.
    """
    if not raw_text:
        return ""

    # Remove citations like [1], [citation needed]
    text = re.sub(r'\[\d+\]', '', raw_text)
    # Remove parenthetical pronunciation guides with IPA symbols or 'pronounced'
    text = re.sub(r'\s*\([^)]*(?:pronounced|\/|\\|ˈ|ˌ)[^)]*\)', '', text)
    # Remove birth/death date ranges like (14 March 1879 – 18 April 1955) if they break the sentence flow
    text = re.sub(r'\s*\((?:born\s+)?[A-Za-z0-9\s,–\-\.]+\)', '', text)
    # Collapse any double spaces
    text = re.sub(r'\s+', ' ', text).strip()

    # Split into sentences and take the first 1-2 sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    concise = " ".join(sentences[:2]).strip()
    if concise and not concise.endswith(('.', '!', '?')):
        concise += "."
    return concise

def fetch_wikipedia_summary(query: str) -> str:
    """
    Fetches a concise 1-2 sentence factual summary from Wikipedia using opensearch + REST API.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        search_url = (
            f"https://en.wikipedia.org/w/api.php?action=opensearch"
            f"&search={urllib.parse.quote(query)}&limit=1&namespace=0&format=json"
        )
        resp = requests.get(search_url, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if len(data) >= 2 and data[1]:
                title = data[1][0]
                summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}"
                s_resp = requests.get(summary_url, headers=headers, timeout=3.5)
                if s_resp.status_code == 200:
                    s_data = s_resp.json()
                    extract = s_data.get("extract", "").strip()
                    if extract:
                        return clean_knowledge_text(extract)
    except Exception:
        pass
    return ""

def fetch_duckduckgo_answer(query: str) -> str:
    """
    Fetches an instant answer from DuckDuckGo Instant Answer API.
    """
    try:
        headers = {"User-Agent": USER_AGENT}
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        resp = requests.get(url, headers=headers, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            abstract = (data.get("AbstractText") or data.get("Answer") or "").strip()
            if abstract:
                return clean_knowledge_text(abstract)
    except Exception:
        pass
    return ""

def answer_knowledge_query(query: str, lang: str = 'en', fallback_subject: str = "") -> bool:
    """
    Answers an informational or conversational query verbally using OpenRouter LLM intelligence
    with multi-key failover, falling back gracefully to Wikipedia/DuckDuckGo if offline.
    """
    clean_query = query.strip()
    if not clean_query:
        return False

    notify(f"Looking up answer for: '{clean_query}'")

    # 1. Primary: High-speed OpenRouter LLM Intelligence with Multi-Key Failover
    try:
        from .llm_client import ask_accio_llm
        llm_answer = ask_accio_llm(clean_query, lang=lang)
        if llm_answer:
            notify(f"Answer: {llm_answer}")
            speak(llm_answer, lang=lang)
            return True
    except Exception as e:
        print(f"[Knowledge Actions] OpenRouter query error: {e}")

    # 2. Resilient Offline/Local Fallback: Wikipedia Summary
    search_term = fallback_subject.strip() if fallback_subject else clean_query
    summary = fetch_wikipedia_summary(search_term)

    # 3. Secondary Fallback: DuckDuckGo Instant Answer
    if not summary:
        summary = fetch_duckduckgo_answer(search_term)

    if summary:
        notify(f"Answer: {summary}")
        # Speak the clean, concise summary directly to the user
        speak(summary, lang=lang)
        return True
    else:
        # Provide direct spoken answer without popping open browser tabs
        msg = f"{clean_query} का उत्तर नहीं मिला। गूगल पर खोजने के लिए 'सर्च करो' बोलें।" if lang == 'hi' else f"I don't have an instant answer for {clean_query}. Say 'search for {clean_query}' to look it up on Google."
        notify(msg)
        speak(msg, lang=lang)
        return True

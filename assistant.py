"""
Accio Interactive Voice Assistant - Main Execution Runtime
===========================================================
WHAT THIS FILE DOES (Simple English):
  This is the primary heartbeat of Accio. It continuously listens to your microphone,
  converts your spoken words into text using an offline neural speech-to-text model,
  understands your intent (whether in English or Hindi), and triggers the computer
  to perform the action (e.g. fill forms, control windows, search websites, or answer questions).
  It also features an automatic 45-second sleep mode to save CPU when you are not speaking.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - onnx_asr (NVIDIA NeMo Parakeet TDT 0.6B int8):
      * What it does: High-speed, local neural Speech-to-Text (Automatic Speech Recognition).
      * Why we use it: Transcribes voice in real-time (~0.1s on standard CPU) without sending
        private user voice recordings to external cloud servers.
      * Benefit: Completely private, zero cloud latency, and works even without fast internet.
  - speech_recognition:
      * What it does: Hardware microphone audio capture and silence detection.
      * Why we use it: Continuously streams audio from the user's microphone with ambient
        noise filtering and responsive pause detection.
      * Benefit: Automatically detects when you finish speaking (0.8s silence) and cuts off
        instantly so you never have to wait.
  - soundfile & numpy:
      * What it does: Ultra-fast mathematical audio buffer decoding in RAM.
      * Why we use it: Converts raw microphone WAV bytes directly into float32 arrays in under 2ms.
"""

import io
import sys
import numpy as np
import soundfile as sf
import speech_recognition as sr
import onnx_asr
import actions

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import time
import re
from actions.languages import detect_language

def run_assistant():
    print("=" * 60)
    print("  ACCIO - Realtime Hands-Free Voice Operating Layer")
    print("=" * 60)
    print("Loading Parakeet ASR model into memory...")
    try:
        model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8")
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return

    recognizer = sr.Recognizer()
    # Natural pause detection: allows 1.4s silence for conversational pauses so user isn't cut off mid-thought
    recognizer.pause_threshold = 2.0
    recognizer.non_speaking_duration = 0.5
    recognizer.phrase_threshold = 0.3

    actions.speak("Accio is online and ready for voice commands.")
    # Ensure startup speech finishes playing completely before opening microphone and calibrating
    actions.wait_until_speech_finishes()

    print("\n[Accio Ready] Try commands like:")
    print("  - 'create a txt file on desktop named Notes' / 'make a note called Tasks'")
    print("  - 'what is photosynthesis' / 'who is Albert Einstein' (Instant Knowledge Q&A)")
    print("  - 'scroll down' / 'scroll up' / 'zoom in' / 'find on page physics'")
    print("  - 'press tab' / 'next field' / 'fill field with Mayank' / 'submit form'")
    print("  - 'type I am running late and send' (Messaging automation)")
    print("  - 'snap window left' / 'snap right' / 'task view' / 'next desktop'")
    print("  - 'search for SpaceX' / 'open YouTube' / 'open WhatsApp web'")
    print("  - 'how much RAM is occupied' / 'check battery'")
    print("  - 'volume up' / 'volume down' / 'mute' / 'take screenshot'")
    print("  - Wake with 'hey accio' / 'hi accio' / 'hello accio' / 'wake up' (after 45s of silence, it sleeps)")
    print("  - 'exit', 'goodbye', or 'bye' to fully stop the assistant\n")

    INACTIVITY_SLEEP_TIMEOUT = 45.0  # seconds of silence before entering sleep mode
    is_sleeping = False
    last_active_time = time.time()
    current_lang = 'en'

    try:
        with sr.Microphone(sample_rate=16000) as source:
            print("Calibrating for background noise (1s)...")
            recognizer.adjust_for_ambient_noise(source, duration=1.0)
            # Fix dynamic energy drift so microphone cuts off promptly when user stops speaking
            recognizer.dynamic_energy_threshold = False
            recognizer.energy_threshold = max(recognizer.energy_threshold, 300)
            print(f"Calibrated energy threshold: {recognizer.energy_threshold:.1f}")
            print("Listening continuously. Speak anytime!\n")

            while True:
                try:
                    # Prevent acoustic loopback: never listen while assistant is still speaking
                    actions.wait_until_speech_finishes()

                    # Check for inactivity and enter sleep mode if silent for 45s
                    if not is_sleeping and (time.time() - last_active_time > INACTIVITY_SLEEP_TIMEOUT):
                        is_sleeping = True
                        print("\n\033[94m[Accio State] Inactivity detected. Entering Sleep Mode...\033[0m")
                        sleep_msg = "Going to sleep mode. Say 'hey accio', 'hi accio', 'hello accio', or 'wake up' to wake me up."
                        actions.speak(sleep_msg, lang='en')
                        actions.wait_until_speech_finishes()
                        print("\033[94m[Accio Asleep - Listening for wake word: 'hey accio' / 'hi accio' / 'hello accio' / 'wake up']\033[0m\n")

                    status_prompt = "\033[94m[Accio Asleep (Say 'hey accio' / 'hi accio' / 'hello accio' / 'wake up')...]\033[0m" if is_sleeping else "\033[90m[Listening...]\033[0m"
                    print(status_prompt, end="\r", flush=True)

                    # Listen with 5s timeout to periodically refresh sleep-timer
                    # phrase_time_limit=150 (2.5 min): generous ceiling for
                    # users who need extended time to fully explain a
                    # multi-step request (per research brief). Tradeoff: if
                    # someone genuinely goes silent mid-recording without
                    # triggering pause_threshold (e.g. long thinking pause
                    # under 2s repeated), the mic could stay open a while
                    # before this ceiling kicks in. Worth real-user testing.
                    audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=150)
                    print("                                                         \r", end="")

                    # Audio conversion to float32 numpy array
                    audio_data = audio.get_wav_data()
                    audio_np, sample_rate = sf.read(io.BytesIO(audio_data))
                    audio_np = audio_np.astype(np.float32)

                    # Speech Recognition via Parakeet
                    text = model.recognize(audio_np, sample_rate=sample_rate).strip()

                    if not text:
                        continue

                    detected_lang = detect_language(text)
                    current_lang = detected_lang

                    # Handle Sleep Mode Wake-Up
                    if is_sleeping:
                        # NOTE: "accio" is a placeholder project name, not
                        # final. When the product name changes, these
                        # phrases must be updated to match.
                        # Wake words: "hey accio", "hi accio", "hello accio",
                        # or plain "wake up" (4 options total). Greeting
                        # word (hi/hey/hello) is NOT optional when paired
                        # with "accio" -- those words alone are too common
                        # in normal speech and would false-trigger. "wake
                        # up" alone is kept as a 4th, simpler option.
                        # (?:\s+\w+)? allows one filler word in between,
                        # e.g. "hey, um, accio".
                        WAKE_WORDS_PATTERN = (
                            r'\b(?:(?:hi|hey|hello)(?:\s+\w+)?[,]?\s*accio|wake\s*up)\b'
                        )
                        wake_match = re.search(WAKE_WORDS_PATTERN, text, re.IGNORECASE)

                        # Also check if user spoke a direct valid accessibility command while asleep
                        parsed_candidate = None
                        if not wake_match:
                            candidate_intent = actions.intent_parser.parse_intent(text)
                            if candidate_intent.name not in ("UNKNOWN", "SEARCH_WEB"):
                                parsed_candidate = candidate_intent

                        if wake_match or parsed_candidate:
                            is_sleeping = False
                            last_active_time = time.time()
                            print(f"\n\033[92m[Accio Woke Up!]\033[0m (Heard: '{text}')")

                            # Check if a command was appended after wake word (e.g., "hey accio, open youtube")
                            # Matches WAKE_WORDS_PATTERN above -- anchored to
                            # the START (^) since this strips a prefix.
                            WAKE_PREFIX_STRIP = (
                                r'^(?:(?:hi|hey|hello)(?:\s+\w+)?[,]?\s*accio|wake\s*up)\b[,\s]*'
                            )
                            command_after = text.strip()
                            while True:
                                prev_cmd = command_after
                                command_after = re.sub(WAKE_PREFIX_STRIP, '', command_after, flags=re.IGNORECASE).strip()
                                if command_after == prev_cmd:
                                    break

                            # BUGFIX: if only punctuation is left after
                            # stripping the wake phrase (e.g. "hi accio."
                            # -> "."), that must NOT be treated as a real
                            # command (previously caused it to search the
                            # web for a period).
                            has_real_content = bool(re.search(r'[a-zA-Z0-9]', command_after))

                            if command_after and has_real_content:
                                text = command_after
                                print(f"\033[92m[Accio Direct Execution]\033[0m Running '{text}' immediately...")
                            else:
                                wake_response = "Hey, I am awake and ready for your commands!"
                                actions.speak(wake_response, lang='en')
                                actions.wait_until_speech_finishes()
                                continue
                        else:
                            # While sleeping, ignore ambient background chatter
                            continue

                    # Active Mode: Reset inactivity timer
                    last_active_time = time.time()
                    print(f"\n\033[93m[Transcribed]\033[0m \"{text}\"")
                    print(f"\033[96m[Accio Analyzing]\033[0m Understanding command and validating action...")
                    time.sleep(0.2)

                    # Dispatch Native Action
                    result = actions.execute_command(text)

                    if result.should_exit:
                        print("\n[Accio Assistant] Session ended by user request.")
                        break

                    # Wait for action's feedback audio to complete before giving the turn-taking cue
                    actions.wait_until_speech_finishes()

                    # Clear Turn-Taking Readiness Cue
                    # Forced to English -- current_lang/Hindi detection is
                    # unreliable (separate known bug, not fixed tonight),
                    # was causing random Hindi responses to English input.
                    ready_cue = "Hey, I am ready for the next query."
                    actions.speak(ready_cue, lang='en')
                    print(f"\033[92m[Accio Turn-Taking]\033[0m {ready_cue}")
                    actions.wait_until_speech_finishes()
                    print("-" * 50)

                except sr.WaitTimeoutError:
                    # Timeout periodically triggers so we can evaluate the sleep timer
                    continue
                except OSError as e:
                    # Microphone hardware issue -- e.g. device disconnected,
                    # unplugged, or claimed by another application. This is
                    # NOT recoverable by just looping again; alert clearly.
                    print(f"[Accio] Microphone error: {e}")
                    print("[Accio] Check that your microphone is connected and not in use by another app.")
                    continue
                except ImportError as e:
                    # A required action module failed to import (e.g. a
                    # missing dependency for a specific action file). This
                    # means a whole category of commands may be unusable
                    # until fixed -- worth surfacing clearly, not hiding.
                    print(f"[Accio] A required module is missing: {e}")
                    print("[Accio] Some commands may not work until this is fixed. Run: pip install -r requirements.txt")
                    continue
                except Exception as e:
                    # Genuinely unexpected error -- not one of the cases
                    # above. Logged with full detail so it can be diagnosed
                    # later, but the assistant keeps running rather than
                    # crashing outright.
                    print(f"[Accio Unexpected Error] {type(e).__name__}: {e}")
                    continue

    except KeyboardInterrupt:
        print("\n\n[Accio Assistant] Stopped by user (Ctrl+C). Goodbye!")
        actions.speak("Goodbye!")
    except Exception as e:
        print(f"\n[Microphone Error] Could not initialize audio input: {e}")

if __name__ == "__main__":
    run_assistant()
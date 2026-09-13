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
    recognizer.pause_threshold = 1.4
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
    print("  - 'exit' or 'goodbye' to quit\n")

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
                        sleep_msg = "स्लीप मोड में जा रहा हूँ। मुझे जगाने के लिए 'hey', 'wake up', या 'start' बोलें।" if current_lang == 'hi' else "Going to sleep mode. Say 'Hey', 'Wake up', or 'Start' to wake me up."
                        actions.speak(sleep_msg, lang=current_lang)
                        actions.wait_until_speech_finishes()
                        print("\033[94m[Accio Asleep - Listening for wake word: 'Hey', 'Wake up', 'Start', or 'Accio']\033[0m\n")

                    status_prompt = "\033[94m[Accio Asleep (Say 'Hey', 'Wake up', or 'Start')...]\033[0m" if is_sleeping else "\033[90m[Listening...]\033[0m"
                    print(status_prompt, end="\r", flush=True)

                    # Listen with 5s timeout to periodically refresh sleep-timer
                    audio = recognizer.listen(source, timeout=5.0, phrase_time_limit=25)
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
                        WAKE_WORDS_PATTERN = (
                            r'\b(?:'
                            r'hey(?:\s+there)?|'
                            r'wake\s*up(?:\s+(?:up|wake\s*up|now|please))?|'
                            r'start(?:\s+(?:assistant|listening|up))?|'
                            r'hello|hi|'
                            r'accio|akio|echo|hey\s+accio|ok\s+accio|'
                            r'jag\s*jao|suno|shuru\s*karo|uth\s*jao'
                            r')\b'
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

                            # Check if a command was appended after wake word (e.g., "Wake up open youtube")
                            WAKE_PREFIX_STRIP = (
                                r'^(?:'
                                r'hey\s+accio|ok\s+accio|hello\s+accio|accio|akio|echo|'
                                r'wake\s*up(?:\s+(?:up|wake\s*up|now|please))?|'
                                r'start(?:\s+(?:assistant|listening|up))?|'
                                r'hey(?:\s+there)?|hello|hi|'
                                r'jag\s*jao|suno|shuru\s*karo|uth\s*jao'
                                r')\b[,\s]*'
                            )
                            command_after = text.strip()
                            while True:
                                prev_cmd = command_after
                                command_after = re.sub(WAKE_PREFIX_STRIP, '', command_after, flags=re.IGNORECASE).strip()
                                if command_after == prev_cmd:
                                    break

                            if command_after:
                                text = command_after
                                print(f"\033[92m[Accio Direct Execution]\033[0m Running '{text}' immediately...")
                            else:
                                wake_response = "हाँ, मैं जाग गया हूँ! बताइए क्या मदद करूँ?" if current_lang == 'hi' else "Hey, I am awake and ready for your commands!"
                                actions.speak(wake_response, lang=current_lang)
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
                    ready_cue = "मैं अगले सवाल के लिए तैयार हूँ।" if current_lang == 'hi' else "Hey, I am ready for the next query."
                    actions.speak(ready_cue, lang=current_lang)
                    print(f"\033[92m[Accio Turn-Taking]\033[0m {ready_cue}")
                    actions.wait_until_speech_finishes()
                    print("-" * 50)

                except sr.WaitTimeoutError:
                    # Timeout periodically triggers so we can evaluate the sleep timer
                    continue
                except Exception as e:
                    print(f"[Loop Error] {e}")
                    continue

    except KeyboardInterrupt:
        print("\n\n[Accio Assistant] Stopped by user (Ctrl+C). Goodbye!")
        actions.speak("Goodbye!")
    except Exception as e:
        print(f"\n[Microphone Error] Could not initialize audio input: {e}")

if __name__ == "__main__":
    run_assistant()

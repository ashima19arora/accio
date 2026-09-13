"""
Accio Single-Shot Voice Command Listener
========================================
WHAT THIS FILE DOES (Simple English):
  This is a standalone diagnostic tool for testing microphone input, speech recognition,
  and action execution in a single run. You run `python listen.py`, speak a single command,
  and it transcribes your speech and runs the corresponding OS action immediately.

GREAT TECH & PACKAGES USED IN THIS FILE:
  - onnx_asr (NVIDIA NeMo Parakeet TDT 0.6B int8):
      * What it does: Local quantized neural Speech-to-Text model.
      * Why we use it: Accurate transcription on CPU without requiring an expensive GPU or cloud API.
  - speech_recognition:
      * What it does: Captures audio from the microphone and cuts off when silence is detected.
      * Why we use it: Adjusted to snappy 0.8s silence cutoff so it stops recording as soon as
        you finish speaking rather than hanging.
  - soundfile & numpy:
      * What it does: In-memory raw WAV decoding into floating point arrays for Parakeet.
"""

import speech_recognition as sr
import onnx_asr
import numpy as np
import io
import soundfile as sf

print("Loading Parakeet model into memory...")
model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8")
print("Model loaded.")

def listen_and_transcribe():
    recognizer = sr.Recognizer()
    # Natural pause detection: allows 1.4s silence for conversational pauses
    recognizer.pause_threshold = 1.4
    recognizer.non_speaking_duration = 0.5
    recognizer.phrase_threshold = 0.3

    with sr.Microphone(sample_rate=16000) as source:
        print("Adjusting for ambient noise, please wait...")
        recognizer.adjust_for_ambient_noise(source, duration=1)
        # Prevent dynamic energy drift from hanging on background noise
        recognizer.dynamic_energy_threshold = False
        recognizer.energy_threshold = max(recognizer.energy_threshold, 300)

        print("Listening... say something.")
        try:
            audio = recognizer.listen(source, timeout=15, phrase_time_limit=30)
        except sr.WaitTimeoutError:
            print("No speech detected within 15 seconds. Try again.")
            return

    print("Transcribing...")

    audio_data = audio.get_wav_data()
    audio_np, sample_rate = sf.read(io.BytesIO(audio_data))
    audio_np = audio_np.astype(np.float32)

    text = model.recognize(audio_np, sample_rate=sample_rate)
    text = text.strip()

    if text:
        print(f"You said: {text}")
        try:
            import actions
            actions.execute_command(text)
        except Exception as e:
            print(f"Error executing action: {e}")
    else:
        print("Could not transcribe any words.")

if __name__ == "__main__":
    listen_and_transcribe()
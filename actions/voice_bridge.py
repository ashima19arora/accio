"""
Accio Voice Bridge Server - Local Speech Execution IPC Service
=============================================================
WHAT THIS FILE DOES:
  Provides a fast, local HTTP bridge on http://127.0.0.1:48124 so the Electron desktop
  orb can dispatch recorded push-to-talk audio directly to the in-memory Parakeet
  ASR model and Accio native actions engine.
"""

import sys
import os

# Ensure project root is in sys.path when executed directly or spawned
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import http.server
import io
import json
import threading
import soundfile as sf
import numpy as np

_server_instance = None
_server_thread = None
_asr_model = None

def get_asr_model():
    global _asr_model
    if _asr_model is None:
        import onnx_asr
        print("[Accio Voice Bridge] Initializing Parakeet ASR model...")
        _asr_model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v2", quantization="int8")
        print("[Accio Voice Bridge] Parakeet ASR model ready.")
    return _asr_model

def set_shared_model(model):
    global _asr_model
    _asr_model = model

class VoiceBridgeHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Quiet standard HTTP access logs
        pass

    def _send_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path.startswith('/health'):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            resp = json.dumps({
                "status": "online",
                "model": "loaded" if _asr_model is not None else "idle",
                "port": 48124
            })
            self.wfile.write(resp.encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path.startswith('/execute_audio'):
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length <= 0:
                self.send_response(400)
                self.end_headers()
                return

            wav_bytes = self.rfile.read(content_length)

            try:
                import actions
                # Notify orb of processing state
                actions.notify_desktop_orb("processing")

                # Decode WAV bytes into numpy array
                audio_np, sample_rate = sf.read(io.BytesIO(wav_bytes))
                audio_np = audio_np.astype(np.float32)

                # Transcribe with warm in-memory model
                model = get_asr_model()
                transcribed_text = model.recognize(audio_np, sample_rate=sample_rate).strip()

                if not transcribed_text:
                    actions.notify_desktop_orb("idle")
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        "success": False,
                        "text": "",
                        "intent": "EMPTY",
                        "message": "No audible speech detected"
                    }).encode('utf-8'))
                    return

                print(f"\n\033[92m[Orb Push-to-Talk Received]\033[0m \"{transcribed_text}\"")
                # Immediately show the user's transcribed speech on the desktop orb
                actions.notify_desktop_orb("transcribed", text=transcribed_text)

                # Execute action
                result = actions.execute_command(transcribed_text)

                # Wait for primary action feedback speech to complete
                actions.wait_until_speech_finishes()

                # Always announce readiness for the next interaction
                actions.notify_desktop_orb("ready_for_next", message="Ready for next")
                actions.speak("Ready for next.")
                actions.wait_until_speech_finishes()
                actions.notify_desktop_orb("ready_for_next", message="Ready for next")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": result.success,
                    "text": transcribed_text,
                    "intent": result.intent,
                    "message": result.message
                }).encode('utf-8'))
                return
            except Exception as e:
                print(f"[Accio Voice Bridge Error] {e}")
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": False,
                    "error": str(e)
                }).encode('utf-8'))
                return

        elif self.path.startswith('/execute_text'):
            content_length = int(self.headers.get('Content-Length', 0))
            raw_body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(raw_body)
                command_text = data.get("text", "").strip()

                import actions
                result = actions.execute_command(command_text)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({
                    "success": result.success,
                    "text": command_text,
                    "intent": result.intent,
                    "message": result.message
                }).encode('utf-8'))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))
                return

        self.send_response(404)
        self.end_headers()

def start_voice_bridge(model=None, port=48124, daemon=True):
    """
    Launches the Accio voice bridge HTTP server in a daemon thread.
    """
    global _server_instance, _server_thread
    if model is not None:
        set_shared_model(model)

    if _server_instance is not None:
        return _server_instance

    try:
        server = http.server.ThreadingHTTPServer(('127.0.0.1', port), VoiceBridgeHandler)
        _server_instance = server

        def _serve():
            try:
                server.serve_forever()
            except Exception:
                pass

        thread = threading.Thread(target=_serve, daemon=daemon, name="AccioVoiceBridgeThread")
        thread.start()
        _server_thread = thread
        print(f"[Accio Voice Bridge] Online and listening on http://127.0.0.1:{port}")
        return server
    except Exception as e:
        print(f"[Accio Voice Bridge Notice] Could not bind port {port}: {e}")
        return None

if __name__ == "__main__":
    print("[Accio Voice Bridge] Starting standalone service on port 48124...")
    get_asr_model()
    srv = start_voice_bridge(port=48124, daemon=False)
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down Accio Voice Bridge.")
        if srv:
            srv.shutdown()

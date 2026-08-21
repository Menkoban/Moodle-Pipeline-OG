import asyncio
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

PORT = 7890
HOST = "localhost"

# Global state
active_connections = []
log_history = []

def log(msg):
    print(f"[copilot-bridge] {msg}")
    log_history.append(msg)

class SimpleBridgeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(200)

    def do_GET(self):
        if self.path == "/status":
            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "running", "port": PORT}).encode("utf-8"))
        elif self.path == "/actions":
            config_path = r"C:\moodle-playground\moodle\local\copilot\actions_config.json"
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode("utf-8"))
            else:
                self._set_headers(404)
                self.wfile.write(b'{"error":"not found"}')
        else:
            self._set_headers(200, "text/plain")
            self.wfile.write(b"Moodle Copilot Bridge is active.")

    def do_POST(self):
        if self.path == "/prompt":
            content_len = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_len)
            try:
                payload = json.loads(post_body.decode("utf-8"))
                prompt = payload.get("prompt", "")
                level = payload.get("level", "meso")
                focus = payload.get("focus", {})
                
                log(f"Received prompt ({level}): {prompt}")
                
                # Mock response / action dispatch
                reply = {
                    "status": "success",
                    "text": f"✨ Verarbeite: '{prompt}' (Ebene: {level})",
                    "reload": False
                }
                
                self._set_headers(200)
                self.wfile.write(json.dumps(reply).encode("utf-8"))
            except Exception as e:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

def start_bridge():
    server = HTTPServer((HOST, PORT), SimpleBridgeHandler)
    log(f"Bridge running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    start_bridge()

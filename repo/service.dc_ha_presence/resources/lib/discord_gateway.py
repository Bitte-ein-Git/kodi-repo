import websocket
import json
import threading
import time
import logging

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("DiscordRPC")

class DiscordClient:
    def __init__(self, app_id, token):
        self.token = token
        self.app_id = app_id
        self.ws = None
        self.heartbeat_interval = None
        self._stop_event = threading.Event()

    def connect(self):
        self.ws = websocket.WebSocketApp(
            GATEWAY_URL,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        threading.Thread(target=self.ws.run_forever, daemon=True).start()

    def _on_open(self, ws):
        log.info("Gateway verbunden.")

    def _on_close(self, ws, close_status_code, close_msg):
        log.warning(f"Gateway getrennt: {close_status_code} {close_msg}")

    def _on_error(self, ws, error):
        log.error(f"WebSocket-Fehler: {error}")

    def _on_message(self, ws, message):
        data = json.loads(message)
        op = data.get("op")
        if op == 10:  # Hello
            self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000.0
            self._start_heartbeat()
            self._identify()

    def _start_heartbeat(self):
        def hb():
            while not self._stop_event.is_set():
                self.ws.send(json.dumps({"op": 1, "d": None}))
                time.sleep(self.heartbeat_interval)
        threading.Thread(target=hb, daemon=True).start()

    def _identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {"os": "windows", "browser": "chrome", "device": "pc"},
                "presence": {"status": "online", "since": 0, "activities": [], "afk": False}
            }
        }
        self.ws.send(json.dumps(payload))
        log.info("Selfbot authentifiziert.")

    def send_activity(self, activity):
        payload = {
            "op": 3,
            "d": {"since": 0, "activities": [activity], "status": "online", "afk": False}
        }
        self.ws.send(json.dumps(payload))
        log.info("Presence gesendet.")

    def clear_activity(self):
        self.send_activity({"name": "Kodi", "type": 3, "status_display_type": 2})

    def disconnect(self):
        self._stop_event.set()
        if self.ws:
            self.ws.close()
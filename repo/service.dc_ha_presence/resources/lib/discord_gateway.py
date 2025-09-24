import websocket
import json
import threading
import time
import xbmc # Importiere xbmc für das Logging

GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"

class DiscordClient:
    def __init__(self, app_id, token):
        self.token = token
        self.app_id = app_id
        self.ws = None
        self.heartbeat_interval = None
        self._stop_event = threading.Event()
        self.s = None  # Sequence number

    def connect(self):
        self.ws = websocket.WebSocketApp(
            GATEWAY_URL,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        threading.Thread(target=self.ws.run_forever, daemon=True, name="DiscordWS").start()

    def _on_open(self, ws):
        xbmc.log("[DiscordGateway] Gateway verbunden.", xbmc.LOGINFO)

    def _on_close(self, ws, close_status_code, close_msg):
        xbmc.log(f"[DiscordGateway] Gateway getrennt: {close_status_code} {close_msg}", xbmc.LOGWARNING)

    def _on_error(self, ws, error):
        xbmc.log(f"[DiscordGateway] WebSocket-Fehler: {error}", xbmc.LOGERROR)

    def _on_message(self, ws, message):
        data = json.loads(message)
        op = data.get("op")

        if data.get("s"):
            self.s = data["s"]

        if op == 10:  # Hello
            self.heartbeat_interval = data["d"]["heartbeat_interval"] / 1000.0
            self._start_heartbeat()
            self._identify()
        elif op == 0 and data.get("t") == "READY": # Ready
            xbmc.log(f"[DiscordGateway] READY empfangen. Angemeldet als: {data['d']['user']['username']}", xbmc.LOGINFO)
        elif op == 11: # Heartbeat ACK
            xbmc.log("[DiscordGateway] Heartbeat ACK empfangen.", xbmc.LOGDEBUG)

    def _start_heartbeat(self):
        def hb():
            while not self._stop_event.is_set():
                payload = {"op": 1, "d": self.s}
                self.ws.send(json.dumps(payload))
                time.sleep(self.heartbeat_interval)
        threading.Thread(target=hb, daemon=True, name="Heartbeat").start()

    def _identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.token,
                "properties": {"os": "windows", "browser": "kodi_addon", "device": "pc"},
                "presence": {"status": "online", "since": 0, "activities": [], "afk": False}
            }
        }
        self.ws.send(json.dumps(payload))
        xbmc.log("[DiscordGateway] Self-Bot Identifizierung gesendet.", xbmc.LOGINFO)

    def set_activity(self, activity):
        payload = {
            "op": 3,
            "d": {"since": 0, "activities": [activity], "status": "online", "afk": False}
        }
        self.ws.send(json.dumps(payload))
        xbmc.log(f"[DiscordGateway] Presence gesendet: {activity.get('details')}", xbmc.LOGINFO)

    def clear_activity(self):
        payload = {
            "op": 3,
            "d": {"since": 0, "activities": [], "status": "online", "afk": False}
        }
        self.ws.send(json.dumps(payload))
        xbmc.log("[DiscordGateway] Presence gelöscht.", xbmc.LOGINFO)

    def disconnect(self):
        self._stop_event.set()
        if self.ws:
            self.ws.close()
import websocket
import json
import threading
import time
import xbmc
import requests
import datetime

class DiscordConnectionError(Exception):
    pass

class DiscordClient:
    def __init__(self, app_id, user_token):
        self.app_id = app_id
        self.user_token = user_token
        self.ws = None
        self.heartbeat_thread = None
        self.listen_thread = None
        self.stop_threads = threading.Event()
        self.connected = threading.Event()
        self.last_payload = None
        self.last_timestamps = None
        self.last_progress = 0

    def _connect_websocket(self):
        try:
            self.ws = websocket.create_connection("wss://gateway.discord.gg/?v=6&encoding=json", timeout=10)
            self.connected.set()
            xbmc.log("[DiscordRPC] Connected to Discord Gateway", xbmc.LOGINFO)
            return True
        except Exception as e:
            xbmc.log(f"[DiscordRPC] WebSocket connection failed: {e}", xbmc.LOGERROR)
            self.connected.clear()
            return False

    def connect(self):
        self.stop_threads.clear()
        if not self._connect_websocket():
            raise DiscordConnectionError("Failed to establish initial connection.")
        self.listen_thread = threading.Thread(target=self._listen, daemon=True)
        self.listen_thread.start()

    def disconnect(self):
        xbmc.log("[DiscordRPC] Disconnecting from Discord Gateway", xbmc.LOGINFO)
        self.stop_threads.set()
        self.connected.clear()
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                xbmc.log(f"[DiscordRPC] WebSocket close error: {e}", xbmc.LOGWARNING)
        self.ws = None
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join()

    def reconnect(self):
        self.disconnect()
        xbmc.log("[DiscordRPC] Attempting reconnect...", xbmc.LOGINFO)
        time.sleep(5)
        try:
            self.connect()
            if self.last_payload:
                self.set_activity(self.last_payload['d']['activities'][0])
        except Exception:
            xbmc.log("[DiscordRPC] Reconnect failed", xbmc.LOGERROR)

    def _listen(self):
        while not self.stop_threads.is_set():
            try:
                message = self.ws.recv()
                if not message:
                    if not self.stop_threads.is_set():
                        xbmc.log("[DiscordRPC] Empty WebSocket message, connection lost", xbmc.LOGWARNING)
                        self.connected.clear()
                    break
                payload = json.loads(message)
                if payload.get("op") == 10:
                    interval = payload["d"]["heartbeat_interval"] / 1000.0
                    self._identify()
                    if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                        self.heartbeat_thread = threading.Thread(target=self._heartbeat, args=(interval,), daemon=True)
                        self.heartbeat_thread.start()
            except (websocket.WebSocketConnectionClosedException, BrokenPipeError, OSError) as e:
                if not self.stop_threads.is_set():
                    xbmc.log(f"[DiscordRPC] WebSocket closed: {e}", xbmc.LOGWARNING)
                    self.connected.clear()
                break
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Listen thread error: {e}", xbmc.LOGERROR, exc_info=True)
                self.connected.clear()
                break

    def _heartbeat(self, interval):
        while not self.stop_threads.wait(interval):
            if self.connected.is_set():
                try:
                    self.send({"op": 1, "d": None}, is_heartbeat=True)
                except DiscordConnectionError:
                    xbmc.log("[DiscordRPC] Heartbeat failed", xbmc.LOGWARNING)
                    self.connected.clear()
                    break
        xbmc.log("[DiscordRPC] Heartbeat stopped", xbmc.LOGINFO)

    def _identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.user_token,
                "properties": {
                    "$os": "linux",
                    "$browser": "kodi-discord-presence",
                    "$device": "kodi"
                }
            }
        }
        self.send(payload)

    def send(self, payload, is_heartbeat=False):
        if not self.connected.is_set() or not self.ws:
            raise DiscordConnectionError("Not connected to Discord.")
        try:
            self.ws.send(json.dumps(payload))
            if not is_heartbeat:
                xbmc.log(f"[DiscordRPC] Sent payload OP {payload['op']}", xbmc.LOGDEBUG)
        except Exception as e:
            self.connected.clear()
            raise DiscordConnectionError(f"Send failed: {e}")

    def _process_image(self, image_url):
        if not image_url:
            return None
        if image_url.startswith("mp:") or "discordapp.net" in image_url:
            return image_url
        try:
            url = f"https://discord.com/api/v9/applications/{self.app_id}/external-assets"
            response = requests.post(
                url,
                headers={
                    "Authorization": self.user_token,
                    "Content-Type": "application/json"
                },
                json={"urls": [image_url]},
                timeout=10
            )
            data = response.json()
            if isinstance(data, list) and "external_asset_path" in data[0]:
                path = data[0]["external_asset_path"]
                xbmc.log(f"[DiscordRPC] External asset registered: {path}", xbmc.LOGINFO)
                return f"mp:{path}"
        except Exception as e:
            xbmc.log(f"[DiscordRPC] External asset upload failed: {e}", xbmc.LOGWARNING)
        return image_url

    def _calculate_timestamps(self, duration, progress, is_paused):
        now = int(time.time())
        start_time = now - int(progress)
        end_time = start_time + int(duration)
        if is_paused:
            # freeze timer
            return {"start": start_time, "end": start_time + int(progress)}
        return {"start": start_time, "end": end_time}

    def set_activity(self, activity_payload):
        try:
            assets = activity_payload.get("assets", {})
            if "large_image" in assets and isinstance(assets["large_image"], str):
                assets["large_image"] = self._process_image(assets["large_image"])
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Asset processing failed: {e}", xbmc.LOGWARNING)

        # Add timestamps if player info is available
        try:
            player = xbmc.Player()
            if player.isPlaying():
                duration = player.getTotalTime()
                position = player.getTime()
                is_paused = xbmc.getCondVisibility("Player.Paused")
                if duration > 0:
                    timestamps = self._calculate_timestamps(duration, position, is_paused)
                    activity_payload["timestamps"] = timestamps
                    self.last_timestamps = timestamps
                    self.last_progress = position
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Timestamp generation failed: {e}", xbmc.LOGWARNING)

        payload = {
            "op": 3,
            "d": {
                "since": int(time.time() * 1000),
                "activities": [activity_payload],
                "status": "online",
                "afk": False
            }
        }

        self.send(payload)
        self.last_payload = payload

    def clear_activity(self):
        payload = {
            "op": 3,
            "d": {
                "since": None,
                "activities": [],
                "status": "online",
                "afk": False
            }
        }
        self.send(payload)
        self.last_payload = None

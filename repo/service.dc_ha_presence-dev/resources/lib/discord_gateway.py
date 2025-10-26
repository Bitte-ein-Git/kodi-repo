import websocket
import json
import threading
import time
import xbmc
import requests

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

    def _connect_websocket(self):
        # establish websocket connection
        try:
            self.ws = websocket.create_connection("wss://gateway.discord.gg/?v=6&encoding=json", timeout=10)
            self.connected.set()
            xbmc.log("[DiscordRPC] Discord Gateway connected.", xbmc.LOGINFO)
            return True
        except (websocket.WebSocketException, ConnectionRefusedError, OSError) as e:
            xbmc.log(f"[DiscordRPC] Failed to connect to Discord Gateway: {e}", xbmc.LOGERROR)
            self.connected.clear()
            return False

    def connect(self):
        # connect and start listening
        self.stop_threads.clear()
        if not self._connect_websocket():
            raise DiscordConnectionError("Failed to establish initial websocket connection.")
        self.listen_thread = threading.Thread(target=self._listen, daemon=True)
        self.listen_thread.start()

    def disconnect(self):
        # disconnect from discord gateway
        xbmc.log("[DiscordRPC] Disconnecting...", xbmc.LOGINFO)
        self.stop_threads.set()
        self.connected.clear()
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Error closing websocket: {e}", xbmc.LOGWARNING)
        self.ws = None
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join()

    def reconnect(self):
        # attempt to reconnect
        self.disconnect()
        xbmc.log("[DiscordRPC] Attempting to reconnect...", xbmc.LOGINFO)
        time.sleep(5)
        try:
            self.connect()
            if self.last_payload:
                self.set_activity(self.last_payload['d']['activities'][0])
        except DiscordConnectionError:
            xbmc.log("[DiscordRPC] Reconnect failed.", xbmc.LOGERROR)

    def _listen(self):
        # listen for gateway events
        while not self.stop_threads.is_set():
            try:
                message = self.ws.recv()
                if not message:
                    if not self.stop_threads.is_set():
                        xbmc.log("[DiscordRPC] Empty message received, connection might be lost.", xbmc.LOGWARNING)
                        self.connected.clear()
                    break
                payload = json.loads(message)
                if payload.get('op') == 10:  # Hello
                    interval = payload['d']['heartbeat_interval'] / 1000.0
                    self._identify()
                    if not self.heartbeat_thread or not self.heartbeat_thread.is_alive():
                        self.heartbeat_thread = threading.Thread(target=self._heartbeat, args=(interval,), daemon=True)
                        self.heartbeat_thread.start()
            except (websocket.WebSocketConnectionClosedException, BrokenPipeError, OSError) as e:
                if not self.stop_threads.is_set():
                    xbmc.log(f"[DiscordRPC] Connection closed unexpectedly: {e}", xbmc.LOGWARNING)
                    self.connected.clear()
                break
            except Exception as e:
                if not self.stop_threads.is_set():
                    xbmc.log(f"[DiscordRPC] Listener thread error: {e}", xbmc.LOGERROR, exc_info=True)
                    self.connected.clear()
                break

    def _heartbeat(self, interval):
        # send heartbeat
        while not self.stop_threads.wait(interval):
            if self.connected.is_set():
                try:
                    self.send({'op': 1, 'd': None}, is_heartbeat=True)
                except DiscordConnectionError:
                    xbmc.log("[DiscordRPC] Heartbeat failed, connection lost.", xbmc.LOGWARNING)
                    self.connected.clear()
                    break
        xbmc.log("[DiscordRPC] Heartbeat thread stopped.", xbmc.LOGINFO)

    def _identify(self):
        # identify to discord
        payload = {
            'op': 2,
            'd': {
                'token': self.user_token,
                'properties': {
                    '$os': 'linux',
                    '$browser': 'kodi-discord-presence',
                    '$device': 'kodi'
                }
            }
        }
        self.send(payload)

    def send(self, payload, is_heartbeat=False):
        # send payload to discord
        if not self.connected.is_set() or not self.ws:
            raise DiscordConnectionError("Not connected to Discord Gateway.")
        try:
            self.ws.send(json.dumps(payload))
            if not is_heartbeat:
                xbmc.log(f"[DiscordRPC] Sent payload OP {payload['op']}", xbmc.LOGDEBUG)
        except (websocket.WebSocketConnectionClosedException, BrokenPipeError, OSError) as e:
            self.connected.clear()
            raise DiscordConnectionError(f"Failed to send payload: {e}")

    def _process_image(self, image_url):
        # convert external URL into Discord external asset path
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

    def set_activity(self, activity_payload):
        # convert image if dynamic artwork is used
        try:
            assets = activity_payload.get("assets", {})
            if "large_image" in assets and isinstance(assets["large_image"], str):
                assets["large_image"] = self._process_image(assets["large_image"])
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Asset processing failed: {e}", xbmc.LOGWARNING)

        payload = {
            'op': 3,
            'd': {
                'since': int(time.time() * 1000),
                'activities': [activity_payload],
                'status': 'online',
                'afk': False
            }
        }
        self.send(payload)
        self.last_payload = payload

    def clear_activity(self):
        # clear discord activity
        payload = {
            'op': 3,
            'd': {
                'since': None,
                'activities': [],
                'status': 'online',
                'afk': False
            }
        }
        self.send(payload)
        self.last_payload = None
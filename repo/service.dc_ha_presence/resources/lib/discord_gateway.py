import websocket
import json
import threading
import time
import xbmc

class DiscordClient:
    def __init__(self, app_id, user_token):
        self.app_id = app_id
        self.user_token = user_token
        self.ws = None
        self.heartbeat_thread = None
        self.listen_thread = None
        self.stop_threads = False
        self.connected = False

    def connect(self):
        # connect to discord gateway
        try:
            self.ws = websocket.create_connection("wss://gateway.discord.gg/?v=6&encoding=json")
            self.stop_threads = False
            
            self.listen_thread = threading.Thread(target=self._listen)
            self.listen_thread.daemon = True
            self.listen_thread.start()
            self.connected = True
            xbmc.log("[DiscordRPC] Discord Gateway connected.", xbmc.LOGINFO)
        except Exception as e:
            self.connected = False
            xbmc.log(f"[DiscordRPC] Failed to connect to Discord Gateway: {e}", xbmc.LOGERROR)
            raise

    def disconnect(self):
        # disconnect from discord gateway
        self.connected = False
        self.stop_threads = True
        if self.ws:
            try:
                self.ws.close()
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Error closing websocket: {e}", xbmc.LOGWARNING)
        self.ws = None

    def _listen(self):
        # listen for gateway events
        try:
            while not self.stop_threads:
                message = self.ws.recv()
                if message:
                    payload = json.loads(message)
                    if payload['op'] == 10:  # Hello
                        interval = payload['d']['heartbeat_interval'] / 1000.0
                        self._identify()
                        if self.heartbeat_thread is None or not self.heartbeat_thread.is_alive():
                            self.heartbeat_thread = threading.Thread(target=self._heartbeat, args=(interval,))
                            self.heartbeat_thread.daemon = True
                            self.heartbeat_thread.start()
        except websocket.WebSocketConnectionClosedException:
            xbmc.log("[DiscordRPC] Connection closed by Discord.", xbmc.LOGINFO)
            self.connected = False
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Listener thread error: {e}", xbmc.LOGERROR)
            self.connected = False


    def _heartbeat(self, interval):
        # send heartbeat
        try:
            while not self.stop_threads:
                self.send({'op': 1, 'd': None})
                time.sleep(interval)
        except (websocket.WebSocketConnectionClosedException, BrokenPipeError):
            xbmc.log("[DiscordRPC] Heartbeat failed (connection closed).", xbmc.LOGWARNING)
            self.connected = False
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Heartbeat thread error: {e}", xbmc.LOGERROR)
            self.connected = False

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

    def send(self, payload):
        # send payload to discord
        if not self.connected or not self.ws:
            raise websocket.WebSocketConnectionClosedException("Not connected to Discord Gateway.")
        try:
            self.ws.send(json.dumps(payload))
        except (websocket.WebSocketConnectionClosedException, BrokenPipeError) as e:
            xbmc.log(f"[DiscordRPC] Failed to send payload: {e}", xbmc.LOGWARNING)
            self.connected = False
            raise e

    def set_activity(self, activity_payload):
        # set discord activity
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

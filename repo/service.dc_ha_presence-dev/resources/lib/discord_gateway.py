# resources/lib/dc_gateway.py
import websocket
import json
import threading
import time
import xbmc
import requests
import traceback

# Exceptions
class DiscordConnectionError(Exception):
    pass

class DiscordClient:
    """
    Discord client using websocket-client.WebSocketApp for more robust
    ping/pong handling and reconnect behavior.
    """
    def __init__(self, app_id, user_token, gateway_url=None):
        self.app_id = app_id
        self.user_token = user_token
        # default gateway URL (v6 used previously; using v9 for more compatibility)
        self.gateway_url = gateway_url or "wss://gateway.discord.gg/?v=9&encoding=json"
        self.ws_app = None
        self.ws_thread = None
        self._connected_evt = threading.Event()
        self._stop_evt = threading.Event()
        self._lock = threading.RLock()
        self.last_payload = None
        self._session_id = None
        self._seq = None
        self._reconnect_lock = threading.Lock()
        self._backoff = 1
        self._max_backoff = 60

    # Public helpers
    def is_connected(self):
        return self._connected_evt.is_set()

    def connect(self, wait=True, timeout=8):
        """
        Start the websocket thread and wait until connected or timeout.
        """
        with self._lock:
            if self.ws_app and self.is_connected():
                xbmc.log("[DiscordRPC] Already connected.", xbmc.LOGDEBUG)
                return

            self._stop_evt.clear()
            self._create_and_start_ws()

        if wait:
            started = self._connected_evt.wait(timeout)
            if not started:
                raise DiscordConnectionError("Timeout waiting for websocket connect.")

    def disconnect(self):
        xbmc.log("[DiscordRPC] Disconnecting from Discord Gateway", xbmc.LOGINFO)
        self._stop_evt.set()
        self._connected_evt.clear()
        try:
            if self.ws_app:
                try:
                    self.ws_app.close()
                except Exception as e:
                    xbmc.log(f"[DiscordRPC] Error closing websocket: {e}", xbmc.LOGWARNING)
            if self.ws_thread and self.ws_thread.is_alive():
                self.ws_thread.join(timeout=3)
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Disconnect exception: {e}", xbmc.LOGWARNING)
        finally:
            self.ws_app = None
            self.ws_thread = None

    # Reconnect helpers
    def reconnect_background(self):
        """
        Trigger reconnect in background (non-blocking).
        """
        t = threading.Thread(target=self._reconnect, daemon=True)
        t.start()

    def reconnect(self):
        """
        Blocking reconnect.
        """
        return self._reconnect()

    def _reconnect(self):
        with self._reconnect_lock:
            try:
                xbmc.log("[DiscordRPC] Reconnect requested.", xbmc.LOGINFO)
                self.disconnect()
                # incremental backoff
                backoff = self._backoff
                while not self._stop_evt.is_set():
                    try:
                        self._create_and_start_ws()
                        if self._connected_evt.wait(timeout=8):
                            xbmc.log("[DiscordRPC] Reconnected successfully.", xbmc.LOGINFO)
                            # reset backoff
                            self._backoff = 1
                            # if we had last payload, try to restore presence
                            if self.last_payload:
                                try:
                                    # last_payload is full op3 payload; re-send
                                    self._send_raw(self.last_payload)
                                except Exception as e:
                                    xbmc.log(f"[DiscordRPC] Failed to restore last payload: {e}", xbmc.LOGWARNING)
                            return True
                        else:
                            xbmc.log(f"[DiscordRPC] Reconnect attempt timed out (waiting {backoff}s).", xbmc.LOGWARNING)
                    except Exception as e:
                        xbmc.log(f"[DiscordRPC] Reconnect attempt exception: {e}", xbmc.LOGWARNING)
                    # exponential backoff, with cap
                    time.sleep(backoff)
                    backoff = min(backoff * 2, self._max_backoff)
                    self._backoff = backoff
                return False
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Reconnect failed: {e}", xbmc.LOGERROR)
                return False

    # Internal: create and start websocket thread
    def _create_and_start_ws(self):
        xbmc.log(f"[DiscordRPC] Creating WebSocketApp to {self.gateway_url}", xbmc.LOGDEBUG)
        # if there is an existing ws_app, close it first
        if self.ws_app:
            try:
                self.ws_app.close()
            except Exception:
                pass

        self.ws_app = websocket.WebSocketApp(
            self.gateway_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # run_forever in a thread with pings handled by the lib (ping_interval)
        def run_ws():
            try:
                # ping_interval ensures ping/pong and will raise on missing pong
                self.ws_app.run_forever(ping_interval=20, ping_timeout=10, ping_payload="ping")
            except Exception as e:
                xbmc.log(f"[DiscordRPC] WebSocket run_forever exception: {e}", xbmc.LOGERROR)
            finally:
                # ensure connected flag cleared
                self._connected_evt.clear()

        self.ws_thread = threading.Thread(target=run_ws, daemon=True)
        self.ws_thread.start()

    # WebSocket callbacks
    def _on_open(self, ws):
        xbmc.log("[DiscordRPC] WebSocket opened.", xbmc.LOGINFO)
        # Connected at TCP level; wait for Gateway Hello (op 10) to identify
        # Mark connection event after we get hello and send identify
        # we don't set connected here; that happens after successful identify/hello handshake

    def _on_message(self, ws, message):
        try:
            payload = json.loads(message)
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Malformed websocket message: {e}", xbmc.LOGWARNING)
            return

        op = payload.get("op")
        t = payload.get("t")
        d = payload.get("d")
        # update sequence if present
        if payload.get("s") is not None:
            self._seq = payload.get("s")

        # Hello - start heartbeat and identify
        if op == 10:
            try:
                heartbeat_interval = d.get("heartbeat_interval", 41250) / 1000.0
            except Exception:
                heartbeat_interval = 41.25
            xbmc.log(f"[DiscordRPC] Received Hello. Heartbeat interval: {heartbeat_interval}s", xbmc.LOGDEBUG)
            # after hello we identify
            try:
                self._identify()
                # mark connected after identify attempt
                self._connected_evt.set()
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Identify failed: {e}", xbmc.LOGERROR)
                self._connected_evt.clear()
        elif op == 11:
            # Heartbeat ACK
            xbmc.log("[DiscordRPC] Heartbeat ACK received.", xbmc.LOGDEBUG)
        elif op == 1:
            # heartbeat request - respond with heartbeat
            try:
                self._send_heartbeat()
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Failed responding to heartbeat request: {e}", xbmc.LOGWARNING)
        elif op == 0:
            # Dispatch events - may contain READY/resume etc
            if t == "READY":
                try:
                    self._session_id = d.get("session_id")
                    xbmc.log("[DiscordRPC] READY received. Session established.", xbmc.LOGINFO)
                    self._connected_evt.set()
                except Exception as e:
                    xbmc.log(f"[DiscordRPC] READY handling error: {e}", xbmc.LOGWARNING)
            elif t == "RESUMED":
                xbmc.log("[DiscordRPC] RESUMED session.", xbmc.LOGINFO)
                self._connected_evt.set()
            # other events can be handled if needed
        # other ops are ignored here

    def _on_error(self, ws, error):
        xbmc.log(f"[DiscordRPC] WebSocket error: {error}", xbmc.LOGERROR)
        # clear connected flag - triggers reconnect logic
        self._connected_evt.clear()

    def _on_close(self, ws, close_status_code, close_msg):
        xbmc.log(f"[DiscordRPC] WebSocket closed: code={close_status_code} msg={close_msg}", xbmc.LOGWARNING)
        self._connected_evt.clear()
        # run reconnect in background unless we are explicitly stopping
        if not self._stop_evt.is_set():
            # short delay before reconnect attempts
            xbmc.log("[DiscordRPC] Scheduling reconnect...", xbmc.LOGINFO)
            self.reconnect_background()

    # low-level send helpers
    def _send_raw(self, payload):
        if not self.ws_app or not self.is_connected():
            raise DiscordConnectionError("Not connected to websocket.")
        try:
            self.ws_app.send(json.dumps(payload))
            return True
        except Exception as e:
            self._connected_evt.clear()
            raise DiscordConnectionError(f"Send failed: {e}")

    def send(self, payload, is_heartbeat=False):
        with self._lock:
            if not self.is_connected():
                raise DiscordConnectionError("Not connected to Discord.")
            try:
                self._send_raw(payload)
            except DiscordConnectionError as e:
                xbmc.log(f"[DiscordRPC] Send failed, clearing connected: {e}", xbmc.LOGWARNING)
                self._connected_evt.clear()
                raise

    # Heartbeat helpers
    def _send_heartbeat(self):
        hb = {"op": 1, "d": self._seq}
        try:
            self._send_raw(hb)
            xbmc.log("[DiscordRPC] Sent heartbeat.", xbmc.LOGDEBUG)
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Heartbeat send failed: {e}", xbmc.LOGWARNING)
            raise

    def _identify(self):
        payload = {
            "op": 2,
            "d": {
                "token": self.user_token,
                "properties": {
                    "$os": "linux",
                    "$browser": "kodi-discord-presence",
                    "$device": "kodi"
                },
                "presence": {
                    "status": "online",
                    "since": None,
                    "activities": [],
                    "afk": False
                }
            }
        }
        self._send_raw(payload)
        xbmc.log("[DiscordRPC] Sent IDENTIFY.", xbmc.LOGDEBUG)

    # image handling similar to previous implementation
    def _process_image(self, image_url):
        if not image_url:
            return None
        if not (image_url.startswith("http://") or image_url.startswith("https://")):
            xbmc.log(f"[DiscordRPC] Using static asset key: {image_url}", xbmc.LOGDEBUG)
            return image_url
        if image_url.startswith("mp:") or "discordapp.net" in image_url or "discord.com" in image_url:
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
                timeout=6
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data and "external_asset_path" in data[0]:
                path = data[0]["external_asset_path"]
                xbmc.log(f"[DiscordRPC] External asset registered: {path}", xbmc.LOGINFO)
                return f"mp:{path}"
        except Exception as e:
            xbmc.log(f"[DiscordRPC] External asset upload failed: {e}", xbmc.LOGWARNING)

        if "api.heyfordy.de" in image_url:
            try:
                head_resp = requests.head(image_url, allow_redirects=True, timeout=4)
                if head_resp.ok and "image.tmdb.org" in head_resp.url:
                    xbmc.log(f"[DiscordRPC] Resolved TMDB URL: {head_resp.url}", xbmc.LOGINFO)
                    return self._process_image(head_resp.url)
                else:
                    xbmc.log(f"[DiscordRPC] TMDB URL resolve failed or not tmdb: {head_resp.url}", xbmc.LOGWARNING)
            except Exception as e:
                xbmc.log(f"[DiscordRPC] TMDB URL resolve exception: {e}", xbmc.LOGWARNING)

        return image_url

    # high-level activity operations
    def set_activity(self, activity_payload):
        try:
            assets = activity_payload.get("assets", {})
            if "large_image" in assets and isinstance(assets["large_image"], str):
                assets["large_image"] = self._process_image(assets["large_image"])
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Asset processing failed: {e}", xbmc.LOGWARNING)

        payload = {
            "op": 3,
            "d": {
                "since": int(time.time() * 1000),
                "activities": [activity_payload],
                "status": "online",
                "afk": False
            }
        }

        # store last payload so we can resend after reconnect
        with self._lock:
            self.last_payload = payload

        # attempt send; if not connected, raise
        self.send(payload)

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
        with self._lock:
            self.last_payload = None
        self.send(payload)
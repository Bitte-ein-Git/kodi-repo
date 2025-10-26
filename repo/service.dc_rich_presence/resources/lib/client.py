# -*- coding: utf-8 -*-
import json
import threading
import time
import base64
import re

import requests
import websocket
import xbmc
import xbmcaddon

# --- Constants ---
ADDON = xbmcaddon.Addon('service.dc_rich_presence')
APP_ID = "1244203892145786992"
GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
IMGBB_URL = "https://api.imgbb.com/1/upload"

# --- Utility Functions ---
def log(msg, level=xbmc.LOGINFO):
    if level == xbmc.LOGDEBUG and not ADDON.getSettingBool('debug_logging'):
        return
    xbmc.log(f"[service.dc_rich_presence] {msg}", level)

def get_setting(key):
    return ADDON.getSetting(key)

# --- ImgBB Uploader ---
class ImgBBClient:
    def __init__(self):
        self.api_key = get_setting('imgbb_key')
        self.session = requests.Session()
        self.upload_cache = {} # simple cache

    def upload_from_path(self, path):
        if not self.api_key:
            log("imgbb_key is missing. Cannot upload artwork.", xbmc.LOGERROR)
            return None
        
        if path in self.upload_cache:
            log(f"Using cached image URL for: {path}", xbmc.LOGDEBUG)
            return self.upload_cache[path]

        try:
            # Handle kodi image:// paths
            if path.startswith('image://'):
                path = xbmc.translatePath(path)
                # This might still be tricky if it's not a direct file path
                if 'http' in path: # if translatePath returns a URL
                     return self.upload_from_url(path)

            # Attempt to read local file and base64 encode
            with open(path, "rb") as f:
                b64_image = base64.b64encode(f.read()).decode('utf-8')
                return self.upload_base64(b64_image, path)

        except Exception as e:
            log(f"Failed to read local image file: {path} - Error: {e}", xbmc.LOGWARNING)
            # Fallback: try to upload via URL if it looks like one
            if path.startswith('http'):
                return self.upload_from_url(path)
            
            log(f"Could not handle image path: {path}", xbmc.LOGERROR)
            return None

    def upload_from_url(self, url):
        if url in self.upload_cache:
            return self.upload_cache[url]
        log(f"Uploading image from URL: {url}", xbmc.LOGDEBUG)
        try:
            data = {
                'key': self.api_key,
                'image': url
            }
            response = self.session.post(IMGBB_URL, data=data, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                img_url = result['data']['url']
                self.upload_cache[url] = img_url
                log(f"imgbb upload successful: {img_url}", xbmc.LOGDEBUG)
                return img_url
            else:
                log(f"imgbb upload failed: {result.get('error', {}).get('message', 'Unknown error')}", xbmc.LOGERROR)
                return None
        except Exception as e:
            log(f"imgbb request failed: {e}", xbmc.LOGERROR)
            return None

    def upload_base64(self, b64_image, cache_key):
        log("Uploading image from base64 data.", xbmc.LOGDEBUG)
        try:
            data = {
                'key': self.api_key,
                'image': b64_image
            }
            response = self.session.post(IMGBB_URL, data=data, timeout=15)
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                img_url = result['data']['url']
                self.upload_cache[cache_key] = img_url
                log(f"imgbb upload successful: {img_url}", xbmc.LOGDEBUG)
                return img_url
            else:
                log(f"imgbb upload failed: {result.get('error', {}).get('message', 'Unknown error')}", xbmc.LOGERROR)
                return None
        except Exception as e:
            log(f"imgbb request failed: {e}", xbmc.LOGERROR)
            return None

# --- Discord Gateway Client ---
class DiscordGatewayClient(threading.Thread):
    def __init__(self):
        super(DiscordGatewayClient, self).__init__()
        self.token = get_setting('discord_token')
        self.ws = None
        self.heartbeat_interval = 40
        self.last_sequence = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.imgbb = ImgBBClient()
        self.active_payload = None

    def send_json(self, payload):
        if self.ws:
            try:
                self.ws.send(json.dumps(payload))
                log(f"Sent Opcode {payload.get('op')}", xbmc.LOGDEBUG)
            except websocket.WebSocketConnectionClosedException as e:
                log(f"WS send failed, connection closed: {e}", xbmc.LOGWARNING)
                self.reconnect()
            except Exception as e:
                log(f"WS send error: {e}", xbmc.LOGERROR)

    def heartbeat(self):
        while not self.stop_event.is_set():
            log("Sending heartbeat", xbmc.LOGDEBUG)
            payload = {
                'op': 1,
                'd': self.last_sequence
            }
            self.send_json(payload)
            self.stop_event.wait(self.heartbeat_interval)

    def identify(self):
        payload = {
            'op': 2,
            'd': {
                'token': self.token,
                'properties': {
                    '$os': 'linux',
                    '$browser': 'kodi_rpc',
                    '$device': 'kodi'
                },
                'presence': {
                    'status': 'online',
                    'since': 0,
                    'activities': [],
                    'afk': False
                }
            }
        }
        self.send_json(payload)

    def update_presence(self, activity):
        with self.lock:
            self.active_payload = activity
            payload = {
                'op': 3,
                'd': {
                    'since': None,
                    'activities': [activity] if activity else [],
                    'status': 'online',
                    'afk': False
                }
            }
            self.send_json(payload)
            log("Presence updated", xbmc.LOGINFO)

    def clear_presence(self):
        self.update_presence(None)

    def on_message(self, ws, message):
        msg = json.loads(message)
        op = msg.get('op')
        data = msg.get('d')
        seq = msg.get('s')

        if seq:
            self.last_sequence = seq

        log(f"Received Opcode {op}", xbmc.LOGDEBUG)

        if op == 10: # Hello
            self.heartbeat_interval = data['heartbeat_interval'] / 1000
            log(f"Heartbeat interval set to {self.heartbeat_interval}s", xbmc.LOGDEBUG)
            self.identify()
            threading.Thread(target=self.heartbeat, daemon=True).start()
        
        elif op == 0: # Dispatch
            event_type = msg.get('t')
            if event_type == 'READY':
                log("Gateway READY.", xbmc.LOGINFO)
                # Resend last known payload on READY (e.g. after reconnect)
                if self.active_payload:
                    self.update_presence(self.active_payload)
            elif event_type == 'RESUMED':
                log("Gateway RESUMED.", xbmc.LOGINFO)
        
        elif op == 1: # Heartbeat
            log("Received heartbeat request, sending response", xbmc.LOGDEBUG)
            self.send_json({'op': 1, 'd': self.last_sequence})
            
        elif op == 7: # Reconnect
            log("Gateway requested reconnect. Closing and reconnecting.", xbmc.LOGWARNING)
            self.ws.close()

        elif op == 9: # Invalid Session
            log("Invalid session. Re-identifying after wait.", xbmc.LOGERROR)
            time.sleep(5)
            self.identify()

    def on_error(self, ws, error):
        log(f"WS Error: {error}", xbmc.LOGERROR)

    def on_close(self, ws, close_status_code, close_msg):
        log(f"WS Closed: {close_status_code} - {close_msg}", xbmc.LOGWARNING)
        if not self.stop_event.is_set():
            self.reconnect()

    def on_open(self, ws):
        log("WS Connection opened.", xbmc.LOGINFO)

    def connect(self):
        log("Attempting to connect to Discord Gateway...", xbmc.LOGINFO)
        if not self.token:
            log("Discord Token is not set. Aborting.", xbmc.LOGERROR)
            return

        self.ws = websocket.WebSocketApp(GATEWAY_URL,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close,
                                         on_open=self.on_open)
        self.ws.run_forever()

    def reconnect(self):
        if self.stop_event.is_set():
            return
        log("Attempting reconnect in 10 seconds...", xbmc.LOGWARNING)
        time.sleep(10)
        if not self.stop_event.is_set():
            self.connect()

    def run(self):
        self.connect()

    def stop(self):
        log("Stopping Gateway Client...", xbmc.LOGINFO)
        self.stop_event.set()
        if self.ws:
            self.ws.close()
        self.clear_presence() # Try to clear presence on exit

    # --- Payload Builder ---
    
    def _build_activity(self, player, status='play'):
        activity = {
            'application_id': APP_ID,
            'name': "🍿 Kodi",
            'type': 3, # Watching
            'flags': 1, # Instance
        }

        # 1. Get Timestamps
        try:
            now_s = int(time.time())
            elapsed_s = player.getTime()
            total_s = player.getTotalTime()

            if elapsed_s > 0 and total_s > 0:
                start_ms = int((now_s - elapsed_s) * 1000)
                end_ms = int((now_s - elapsed_s + total_s) * 1000)
                activity['timestamps'] = {'start': start_ms, 'end': end_ms}
            elif elapsed_s > 0: # e.g. Live TV with no end
                start_ms = int((now_s - elapsed_s) * 1000)
                activity['timestamps'] = {'start': start_ms}
        except Exception as e:
            log(f"Error getting timestamps: {e}", xbmc.LOGWARNING)

        # 2. Get Details & State (Movie, TV Show, Live TV)
        video_type = xbmc.getInfoLabel('VideoPlayer.VideoType')
        
        if xbmc.getInfoLabel('Player.IsInternetStream') == 'true' or 'pvr' in video_type:
            # --- Live TV ---
            channel_name = xbmc.getInfoLabel('Player.ChannelName')
            program_title = xbmc.getInfoLabel('Player.Title') # Current program
            
            activity['details'] = program_title if program_title else channel_name
            activity['state'] = f"📺 • {channel_name}" if channel_name else "📺 • Live TV"
            
            art_path = xbmc.getInfoLabel('Player.ChannelLogo')
            small_asset = 'livetv'
            small_text = 'Live TV'

        elif video_type == 'episode':
            # --- TV Show ---
            show_title = xbmc.getInfoLabel('VideoPlayer.TVShowTitle')
            season = xbmc.getInfoLabel('VideoPlayer.Season')
            episode = xbmc.getInfoLabel('VideoPlayer.Episode')
            ep_name = xbmc.getInfoLabel('VideoPlayer.Title')
            
            activity['details'] = show_title
            activity['state'] = f"🎞️ S{season:02}E{episode:02} » {ep_name}"
            
            art_path = xbmc.getInfoLabel('VideoPlayer.Art(thumb)')
            if not art_path:
                art_path = xbmc.getInfoLabel('VideoPlayer.Art(tvshow.poster)')
            small_asset = status
            small_text = status.capitalize()

        elif video_type == 'movie':
            # --- Movie ---
            title = xbmc.getInfoLabel('VideoPlayer.Title')
            genres = xbmc.getInfoLabel('VideoPlayer.Genre')
            
            activity['details'] = title
            if genres:
                # Use first genre or combined list
                genre_list = [g.strip() for g in genres.split('/')]
                activity['state'] = f"🎭 • {genre_list[0]}"
            else:
                activity['state'] = "🎬 • Movie"
                
            art_path = xbmc.getInfoLabel('VideoPlayer.Art(poster)')
            if not art_path:
                art_path = xbmc.getInfoLabel('VideoPlayer.Art(thumb)')
            small_asset = status
            small_text = status.capitalize()
            
        else:
            # --- Fallback (Unknown Video) ---
            title = xbmc.getInfoLabel('Player.Title')
            activity['details'] = title if title else "Kodi"
            activity['state'] = "Watching Video"
            art_path = xbmc.getInfoLabel('VideoPlayer.Art(thumb)')
            small_asset = status
            small_text = status.capitalize()

        # 3. Get Artwork (Run upload in a thread)
        def set_artwork(path, payload, s_asset, s_text):
            img_url = None
            if path:
                # Clean up kodi image paths
                path = re.sub(r'^image://|/$', '', path)
                if 'http' not in path:
                     path = xbmc.translatePath(path)
                
                log(f"Attempting to upload artwork from: {path}", xbmc.LOGDEBUG)
                img_url = self.imgbb.upload_from_path(path)
            
            assets = {
                'large_image': img_url if img_url else 'kodi',
                'large_text': 'Kodi',
                'small_image': s_asset,
                'small_text': s_text
            }
            payload['assets'] = assets
            
            # Send the final payload
            self.update_presence(payload)

        # Start artwork upload/payload update in a background thread
        # This prevents the UI from blocking if imgbb is slow
        threading.Thread(target=set_artwork, args=(art_path, activity, small_asset, small_text), daemon=True).start()

    def update_status(self, player, status='play'):
        try:
            if status == 'stop':
                self.clear_presence()
            else:
                self._build_activity(player, status)
        except Exception as e:
            log(f"Failed to build/update activity: {e}", xbmc.LOGERROR)
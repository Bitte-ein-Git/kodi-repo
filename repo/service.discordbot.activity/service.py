import xbmc
import xbmcaddon
import xbmcgui
import json
import threading
import time
import sys
import websocket

# --- Addon Metadaten ---
ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

# --- Discord Client (Gateway-Kommunikation) ---
class DiscordClient:
    def __init__(self, token, app_id):
        self.token = token
        self.app_id = app_id
        self.ws = None
        self.ws_thread = None
        self.heartbeat_thread = None
        self.heartbeat_interval = None
        self.sequence = None
        self.session_id = None
        self.is_connected = threading.Event()

    def send_json_request(self, payload):
        if self.ws and self.is_connected.is_set():
            try:
                self.ws.send(json.dumps(payload))
            except Exception as e:
                xbmc.log(f"[{ADDON_ID}] Fehler beim Senden an Discord: {e}", level=xbmc.LOGERROR)

    def _send_heartbeat(self):
        while self.is_connected.is_set():
            payload = {'op': 1, 'd': self.sequence}
            self.send_json_request(payload)
            time.sleep(self.heartbeat_interval / 1000)

    def identify(self):
        payload = {
            'op': 2,
            'd': {
                'token': self.token,
                'properties': {
                    '$os': sys.platform,
                    '$browser': 'kodi_discord_presence',
                    '$device': 'kodi'
                },
                'presence': {'status': 'online', 'since': 0, 'afk': False, 'activities': []}
            }
        }
        self.send_json_request(payload)

    def update_presence(self, details, state, large_image="kodi", large_text="Kodi"):
        payload = {
            'op': 3,
            'd': {
                'since': int(time.time() * 1000),
                'activities': [{
                    'name': 'Kodi',
                    'type': 3,
                    'status_display_type': 2,
                    'application_id': self.app_id,
                    'details': str(details)[:128], # Discord-Limit
                    'state': str(state)[:128],   # Discord-Limit
                    'assets': {
                        'large_image': large_image,
                        'large_text': large_text
                    }
                }],
                'status': 'online',
                'afk': False
            }
        }
        self.send_json_request(payload)

    def clear_presence(self):
        payload = {
            'op': 3,
            'd': {'since': 0, 'activities': [], 'status': 'online', 'afk': False}
        }
        self.send_json_request(payload)

    def on_message(self, ws, message):
        event = json.loads(message)
        op = event['op']
        self.sequence = event.get('s', self.sequence)

        if op == 10:  # Hello
            self.heartbeat_interval = event['d']['heartbeat_interval']
            self.heartbeat_thread = threading.Thread(target=self._send_heartbeat)
            self.heartbeat_thread.daemon = True
            self.identify()
        elif op == 0 and event['t'] == 'READY':  # Ready
            self.session_id = event['d']['session_id']
            self.is_connected.set() # Verbindung als aktiv markieren
            self.heartbeat_thread.start()
            xbmc.log(f"[{ADDON_ID}] Discord READY. Session ID: {self.session_id}", level=xbmc.LOGINFO)

    def on_error(self, ws, error):
        xbmc.log(f"[{ADDON_ID}] Discord WS Error: {error}", level=xbmc.LOGERROR)

    def on_close(self, ws, close_status_code, close_msg):
        self.is_connected.clear()
        xbmc.log(f"[{ADDON_ID}] Discord WS Closed. Code: {close_status_code}, Msg: {close_msg}", level=xbmc.LOGINFO)
        # Hier könnte man eine Reconnect-Logik implementieren, falls gewünscht.

    def connect(self):
        self.ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=9&encoding=json",
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def disconnect(self):
        self.is_connected.clear()
        if self.ws:
            self.ws.close()
            
# --- Kodi Player Monitor ---
class KodiMonitor(xbmc.Player):
    def __init__(self, client):
        super(KodiMonitor, self).__init__()
        self.client = client
        self.current_details = None
        self.current_state = None

    def get_playback_info_with_retry(self, retries=5, delay=0.3):
        """
        Versucht mehrmals, Metadaten abzurufen, um Race Conditions zu umgehen.
        """
        for i in range(retries):
            # GEÄNDERT: Zuverlässigere InfoLabels für PVR verwenden
            if xbmc.getCondVisibility('Pvr.IsPlayingTv'):
                details = xbmc.getInfoLabel('Pvr.EPGEventTitle')
                state = xbmc.getInfoLabel('Pvr.ChannelName')
                if details and state:
                    return {'details': details, 'state': f'📺 {state}'}

            # Original-Logik für Filme und Serien
            video_info = self.getVideoInfoTag()
            if video_info:
                media_type = video_info.getMediaType()
                if media_type == 'movie':
                    title = video_info.getTitle()
                    year = video_info.getYear()
                    return {'details': f"{title} ({year})", 'state': '🎬 Film'}
                
                elif media_type == 'episode':
                    show_title = video_info.getTVShowTitle()
                    season = video_info.getSeason()
                    episode = video_info.getEpisode()
                    ep_title = video_info.getTitle()
                    return {'details': f"{show_title} - S{season:02d}E{episode:02d}", 'state': f'🎞️ {ep_title}'}
            
            xbmc.sleep(int(delay * 1000))
        
        xbmc.log(f"[{ADDON_ID}] Konnte nach {retries} Versuchen keine Metadaten abrufen.", level=xbmc.LOGWARNING)
        return None

    def onPlayBackStarted(self):
        info = self.get_playback_info_with_retry()
        if info:
            self.current_details = info['details']
            self.current_state = info['state']
            xbmc.log(f"[{ADDON_ID}] Starte Presence Update: {self.current_details} | {self.current_state}", level=xbmc.LOGINFO)
            self.client.update_presence(self.current_details, self.current_state)

    def onPlayBackStopped(self):
        xbmc.log(f"[{ADDON_ID}] Playback gestoppt, lösche Presence.", level=xbmc.LOGINFO)
        self.client.clear_presence()
        self.current_details = None
        self.current_state = None

    def onPlayBackPaused(self):
        # GEÄNDERT: Presence nicht löschen, sondern Pausenstatus anzeigen
        if self.current_details and self.current_state:
            xbmc.log(f"[{ADDON_ID}] Playback pausiert.", level=xbmc.LOGINFO)
            paused_state = f"{self.current_state} (Pausiert)"
            self.client.update_presence(self.current_details, paused_state)

    def onPlayBackResumed(self):
        # GEÄNDERT: Originalstatus wiederherstellen
        if self.current_details and self.current_state:
            xbmc.log(f"[{ADDON_ID}] Playback fortgesetzt.", level=xbmc.LOGINFO)
            self.client.update_presence(self.current_details, self.current_state)

# --- Haupt-Addon-Logik ---
if __name__ == '__main__':
    APP_ID = ADDON.getSetting('discord_app_id')
    USER_TOKEN = ADDON.getSetting('discord_user_token')

    if not APP_ID or not USER_TOKEN:
        xbmc.log(f"[{ADDON_ID}] Discord App ID oder User Token nicht gesetzt.", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(ADDON_NAME, "Discord App ID oder Token fehlt.", xbmcgui.NOTIFICATION_ERROR, 5000)
    else:
        discord_client = DiscordClient(token=USER_TOKEN, app_id=APP_ID)
        discord_client.connect()

        monitor = KodiMonitor(client=discord_client)
        addon_monitor = xbmc.Monitor()

        xbmc.log(f"[{ADDON_ID}] Service gestartet.", level=xbmc.LOGINFO)

        while not addon_monitor.abortRequested():
            xbmc.sleep(1000)

        # Aufräumen beim Beenden
        discord_client.clear_presence()
        discord_client.disconnect()
        xbmc.log(f"[{ADDON_ID}] Service gestoppt.", level=xbmc.LOGINFO)
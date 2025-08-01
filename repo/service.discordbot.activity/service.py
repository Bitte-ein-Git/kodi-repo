import xbmc
import xbmcaddon
import xbmcgui
import json
import threading
import time
import sys
import websocket

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo('id')
ADDON_NAME = ADDON.getAddonInfo('name')

class DiscordClient:
    def __init__(self, token, app_id):
        self.token = token
        self.app_id = app_id
        self.ws = None
        self.heartbeat_interval = None
        self.sequence = None
        self.session_id = None
        self.ws_thread = None
        self.heartbeat_thread = None

    def send_json_request(self, payload):
        if self.ws:
            self.ws.send(json.dumps(payload))

    def send_heartbeat(self):
        while True:
            try:
                payload = {'op': 1, 'd': self.sequence}
                self.send_json_request(payload)
                time.sleep(self.heartbeat_interval / 1000)
            except:
                return

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
                'presence': {
                    'status': 'online',
                    'since': 0,
                    'afk': False,
                    'activities': []
                }
            }
        }
        self.send_json_request(payload)

    def update_presence(self, details, state):
        payload = {
            'op': 3,
            'd': {
                'since': int(time.time() * 1000),
                'activities': [{
                    'name': 'Kodi',
                    'type': 3,
                    'status_display_type': 2,
                    'application_id': self.app_id,
                    'details': details,
                    'state': state
                }],
                'status': 'online',
                'afk': False
            }
        }
        self.send_json_request(payload)

    def clear_presence(self):
        payload = {
            'op': 3,
            'd': {
                'since': 0,
                'activities': [],
                'status': 'online',
                'afk': False
            }
        }
        self.send_json_request(payload)
    
    def on_message(self, ws, message):
        event = json.loads(message)
        op = event['op']
        self.sequence = event.get('s')

        if op == 10: # Hello
            self.heartbeat_interval = event['d']['heartbeat_interval']
            self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
            self.heartbeat_thread.daemon = True
            self.heartbeat_thread.start()
            self.identify()
        elif op == 0 and event['t'] == 'READY': # Ready
            self.session_id = event['d']['session_id']
            xbmc.log(f"[{ADDON_ID}] Discord READY. Session ID: {self.session_id}", level=xbmc.LOGINFO)


    def on_error(self, ws, error):
        xbmc.log(f"[{ADDON_ID}] Discord WS Error: {error}", level=xbmc.LOGERROR)

    def on_close(self, ws, close_status_code, close_msg):
        xbmc.log(f"[{ADDON_ID}] Discord WS Closed.", level=xbmc.LOGINFO)
        # Hier könnte man eine Reconnect-Logik implementieren

    def connect(self):
        self.ws = websocket.WebSocketApp("wss://gateway.discord.gg/?v=9&encoding=json",
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

class KodiMonitor(xbmc.Player):
    def __init__(self, client):
        super(KodiMonitor, self).__init__()
        self.client = client
        self.last_media_type = None

    def onPlayBackStarted(self):
        time.sleep(1) # Gib Kodi eine Sekunde Zeit, um Metadaten zu laden
        video_info = self.getVideoInfoTag()
        if not video_info:
            return

        media_type = video_info.getMediaType()
        details = ""
        state = ""
        
        if media_type == 'movie':
            title = video_info.getTitle()
            year = video_info.getYear()
            genre = video_info.getGenre()
            details = f"{title} ({year})"
            state = genre.split(' / ')[0] if genre else "Movie"
            self.last_media_type = 'movie'

        elif media_type == 'episode':
            show_title = video_info.getTVShowTitle()
            year = video_info.getYear()
            season = video_info.getSeason()
            episode = video_info.getEpisode()
            episode_title = video_info.getTitle()
            details = f"{show_title} ({year})"
            state = f"S{season:02d}E{episode:02d} | {episode_title}"
            self.last_media_type = 'episode'

        elif xbmc.getCondVisibility('Pvr.IsPlayingTv'):
            title = video_info.getTitle()
            channel = video_info.getStation() if hasattr(video_info, 'getStation') else xbmc.getInfoLabel('Player.ChannelName')
            details = title or "Unbekannte Sendung"
            state = channel or "Unbekannter Sender"
            self.last_media_type = 'livetv'
            xbmc.log(f"[{ADDON_ID}] LiveTV erkannt – Sende '{details}' auf '{state}'", level=xbmc.LOGINFO)

        if details and state:
            xbmc.log(f"[{ADDON_ID}] Updating Discord Presence: {details} | {state}", level=xbmc.LOGINFO)
            self.client.update_presence(details, state)

    def onPlayBackStopped(self):
        if self.last_media_type:
            xbmc.log(f"[{ADDON_ID}] Playback stopped, clearing Discord Presence.", level=xbmc.LOGINFO)
            self.client.clear_presence()
            self.last_media_type = None

    def onPlayBackPaused(self):
        self.onPlayBackStopped()

    def onPlayBackResumed(self):
        self.onPlayBackStarted()


if __name__ == '__main__':
    APP_ID = ADDON.getSetting('discord_app_id')
    USER_TOKEN = ADDON.getSetting('discord_user_token')

    if not APP_ID or not USER_TOKEN:
        xbmc.log(f"[{ADDON_ID}] App ID or User Token not set in addon settings.", level=xbmc.LOGERROR)
        try:
            xbmcgui.Dialog().notification(ADDON_NAME, "App ID or User Token missing.", xbmcgui.NOTIFICATION_ERROR, 5000)
        except:
            pass
    else:
        discord_client = DiscordClient(token=USER_TOKEN, app_id=APP_ID)
        discord_client.connect()

        monitor = KodiMonitor(client=discord_client)
        system_monitor = xbmc.Monitor()

        xbmc.log(f"[{ADDON_ID}] Service started.", level=xbmc.LOGINFO)

        while not system_monitor.abortRequested():
            xbmc.sleep(1000)

        discord_client.clear_presence()
        if discord_client.ws:
            discord_client.ws.close()

        xbmc.log(f"[{ADDON_ID}] Service stopped.", level=xbmc.LOGINFO)
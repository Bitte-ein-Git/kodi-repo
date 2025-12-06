import xbmc
import xbmcaddon
import xbmcgui
import json
import time
import os
import requests
import re
import urllib.parse

# Versuch den Import an den Dateinamen anzupassen, Fallback falls lokal anders benannt
try:
    from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError
except ImportError:
    from resources.lib.dc_gateway import DiscordClient, DiscordConnectionError

ADDON = xbmcaddon.Addon()
TMDB_API_URL = "https://api.heyfordy.de/tmdb"

def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[DiscordRPC] {msg}", level)

def removeKodiTags(text):
    if not text:
        return ""
    validTags = ["I", "B", "LIGHT", "UPPERCASE", "LOWERCASE", "CAPITALIZE", "COLOR"]
    for tag in validTags:
        r = re.compile(r"\[\s*/?\s*"+tag+r"\s*?\]")
        text = r.sub("", text)
    r = re.compile(r"\[\s*/?\s*CR\s*?\]")
    text = r.sub(" ", text)
    r = re.compile(r"\[\s*/?\s*COLOR\s*?.*?\]")
    text = r.sub("", text)
    return text

def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=4000):
    xbmcgui.Dialog().notification(title, message, icon, duration)

class DiscordKodiService(xbmc.Monitor):
    def __init__(self):
        super(DiscordKodiService, self).__init__()
        self.client = None
        self.last_payload_str = ""
        # Default Werte initialisieren
        self.ha_url = ""
        self.ha_token = ""
        self.load_settings()

    def load_settings(self):
        self.app_id = ADDON.getSettingString("app_id")
        self.user_token = ADDON.getSettingString("user_token")
        self.icon_color = ADDON.getSettingString("icon_color")
        
        # Home Assistant Settings laden
        self.ha_url = ADDON.getSettingString("ha_url")
        self.ha_token = ADDON.getSettingString("ha_token")
        
        log("Settings loaded.")

    def is_config_valid(self):
        # Wir prüfen hier nur Discord Config. HA ist optional, aber wenn gesetzt, wird es geprüft.
        return all([self.app_id, self.user_token])

    def check_ha_availability(self):
        """
        Prüft, ob Home Assistant erreichbar ist.
        Gibt True zurück, wenn erreichbar oder nicht konfiguriert (Fallback).
        Gibt False zurück, wenn konfiguriert aber nicht erreichbar.
        """
        # Wenn keine HA URL konfiguriert ist, ignorieren wir den Check (oder geben True zurück, damit das Addon läuft)
        if not self.ha_url or not self.ha_token:
            return True

        try:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "content-type": "application/json",
            }
            # Wir pingen die API Root, um generell Konnektivität zu prüfen
            # Man könnte hier auch spezifisch auf 'sensor_state' prüfen: f"{self.ha_url}/api/states/{self.sensor_state}"
            url = f"{self.ha_url}/api/"
            
            response = requests.get(url, headers=headers, timeout=5)
            
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                log("HA Auth failed (401). Check Token.", xbmc.LOGERROR)
                return False
            else:
                log(f"HA Check failed. Status: {response.status_code}", xbmc.LOGWARNING)
                return False
        except requests.exceptions.ConnectionError:
            log("HA Connection Error: Host unreachable.", xbmc.LOGWARNING)
            return False
        except requests.exceptions.Timeout:
            log("HA Connection Error: Timeout.", xbmc.LOGWARNING)
            return False
        except Exception as e:
            log(f"HA Check exception: {e}", xbmc.LOGERROR)
            return False

    def get_current_playing_info(self):
        try:
            rpc_query = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {"playerid": 1, "properties": [
                    "title", "showtitle", "season", "episode", "album",
                    "artist", "genre", "streamdetails", "art", "duration",
                    "channel", "year", "imdbnumber", "type"
                ]},
                "id": 1
            })
            rpc_response = xbmc.executeJSONRPC(rpc_query)
            data = json.loads(rpc_response)
            return data.get("result", {}).get("item", {})
        except Exception as e:
            log(f"Error fetching playback info: {e}", xbmc.LOGERROR)
            return {}

    def get_playback_time(self):
        try:
            rpc_query = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetProperties",
                "params": {"playerid": 1, "properties": ["time", "totaltime"]},
                "id": 1
            })
            rpc_response = xbmc.executeJSONRPC(rpc_query)
            data = json.loads(rpc_response)
            props = data.get("result", {})
            current = self.time_to_seconds(props.get("time", {}))
            total = self.time_to_seconds(props.get("totaltime", {}))
            return current, total
        except Exception as e:
            log(f"Error fetching playback time: {e}", xbmc.LOGERROR)
            return 0, 0

    def time_to_seconds(self, time_dict):
        if not time_dict:
            return 0
        return (time_dict.get("hours", 0) * 3600 +
                time_dict.get("minutes", 0) * 60 +
                time_dict.get("seconds", 0) +
                time_dict.get("milliseconds", 0) / 1000.0)

    def build_payload(self, info, is_pvr, is_paused, current_time, total_time):
        title = info.get("title") or info.get("label") or "Unbekannter Titel"
        title = removeKodiTags(title)
        year = info.get("year", 0) or 0
        details = f"{title} ({year})" if year > 0 else title
        state = ""
        assets = {}

        if self.icon_color == 'Greyscale':
            large_image_key_default = "1405130772981223454"
            small_image_key_pvr = "1407207956877021236"
            small_image_key_media = "1407207958294564884"
            pause_image_key = "1407207956851982336"
        else: # colored
            large_image_key_default = "1405130772981223454"
            small_image_key_pvr = "1407207958252884149"
            small_image_key_media = "1407207956914634772"
            pause_image_key = "1407207957422411849"

        small_image_key = small_image_key_pvr
        small_text = "Live TV"
        large_image_key = large_image_key_default

        showtitle = info.get("showtitle")
        season = info.get("season", 0) or 0
        episode = info.get("episode", 0) or 0

        if is_pvr:
            channel_name = info.get("channel", "")
            if season > 0 and episode > 0:
                state = f"🎞️ S{season:02d}E{episode:02d} • {channel_name}"
            else:
                state = channel_name
        else:
            media_type = info.get("type")
            imdb_id = info.get("imdbnumber")
            media_name = None
            api_type = None

            if media_type == 'episode' and showtitle and season > 0 and episode > 0:
                state = f"🎞️ » S{season:02d}E{episode:02d}"
                details_title = removeKodiTags(showtitle)
                details = f"{details_title} ({year})" if year > 0 else details_title
                media_name = showtitle
                api_type = 'tv'
            elif media_type == 'movie' or (media_type in ['video', 'unknown'] and imdb_id):
                genres = info.get("genre", [])
                if genres:
                    state = "🎭 » " + ", ".join(genres)
                else:
                    state = "🎬 Movie"
                media_name = title
                api_type = 'movie'

            small_image_key = small_image_key_media
            small_text = "Playing"

            if api_type and (imdb_id or media_name):
                try:
                    params = {'type': api_type}
                    if imdb_id:
                        params['id'] = imdb_id
                    elif media_name:
                        # remove year suffix from show/movie title if present
                        clean_name = re.sub(r"\s*\(\d{4}\)\s*$", "", media_name).strip()
                        params['name'] = clean_name
                        # if we stripped a year, include it
                        match = re.search(r"\((\d{4})\)\s*$", media_name)
                        if match:
                            params['year'] = match.group(1)
                    large_image_key = f"{TMDB_API_URL}?{urllib.parse.urlencode(params)}"
                    log(f"Using dynamic artwork URL: {large_image_key}")
                except Exception as e:
                    log(f"Failed to build artwork URL: {e}", xbmc.LOGWARNING)

        if is_paused:
            small_image_key = pause_image_key
            small_text = "PAUSE ⏸️"

        timestamps = {}
        if not is_paused and total_time > 0:
            now = time.time()
            start_timestamp = now - current_time
            end_timestamp = start_timestamp + total_time
            timestamps = {"start": int(start_timestamp * 1000), "end": int(end_timestamp * 1000)}

        assets["large_image"] = large_image_key
        assets["large_text"] = details
        assets["small_image"] = small_image_key
        assets["small_text"] = small_text

        payload = {
            "name": "Kodi",
            "type": 3,
            "application_id": self.app_id,
            "details": details,
            "state": state,
            "status_display_type": 2,
            "assets": assets,
        }

        if timestamps:
            payload["timestamps"] = timestamps

        return payload

    def run_service(self):
        if not self.is_config_valid():
            log("Incomplete configuration.", xbmc.LOGERROR)
            show_notification("Discord Presence", "Configuration incomplete!", xbmcgui.NOTIFICATION_ERROR)
            return

        # Client initialisieren, aber NOCH NICHT verbinden
        self.client = DiscordClient(self.app_id, self.user_token)
        log("Discord client initialized (waiting for HA/Loop).")
        
        # Flag um Benachrichtigungs-Spam zu verhindern
        ha_error_notified = False

        try:
            while not self.abortRequested():
                try:
                    # 1. PRÜFUNG: Ist Home Assistant erreichbar?
                    is_ha_online = self.check_ha_availability()
                    
                    if not is_ha_online:
                        # HA nicht erreichbar
                        if self.client.is_connected():
                            # NOT-AUS: Gateway trennen
                            log("Home Assistant unreachable! Disconnecting Gateway.", xbmc.LOGWARNING)
                            self.client.disconnect()
                            show_notification("Fehler", "HA Sensoren nicht erreichbar. Discord getrennt!", xbmcgui.NOTIFICATION_ERROR)
                            ha_error_notified = True
                        elif not ha_error_notified:
                            # Einmalige Warnung, wenn wir bereits getrennt sind
                            show_notification("Fehler", "Warte auf Home Assistant...", xbmcgui.NOTIFICATION_WARNING)
                            ha_error_notified = True
                        
                        # Wir warten kurz und prüfen im nächsten Loop erneut
                        if self.waitForAbort(10): break
                        continue
                    
                    # 2. Wenn HA erreichbar ist:
                    if ha_error_notified:
                        # Wir waren vorher offline, jetzt wieder da
                        show_notification("Info", "Home Assistant wieder verbunden.", xbmcgui.NOTIFICATION_INFO)
                        ha_error_notified = False

                    # 3. Discord Verbindung sicherstellen
                    if not self.client.is_connected():
                        log("HA is online. Connecting Discord client...", xbmc.LOGINFO)
                        try:
                            self.client.connect() # Dies blockiert kurz, bis Verbindung steht
                            # show_notification("Discord", "Verbunden", xbmcgui.NOTIFICATION_INFO)
                        except DiscordConnectionError as e:
                            log(f"Connection failed: {e}", xbmc.LOGERROR)
                            show_notification("Discord Error", "Verbindung fehlgeschlagen", xbmcgui.NOTIFICATION_ERROR)
                            if self.waitForAbort(10): break
                            continue

                    # 4. Normale Presence Logik (Kodi Player Status)
                    player = xbmc.Player()
                    is_playing = player.isPlaying()
                    is_paused = xbmc.getCondVisibility("Player.Paused")
                    is_pvr = xbmc.getCondVisibility("Pvr.IsPlayingTv")

                    if not is_playing:
                        if self.last_payload_str:
                            log("Stopped, clearing presence.")
                            try:
                                self.client.clear_activity()
                            except Exception as e:
                                log(f"Failed clearing activity: {e}", xbmc.LOGWARNING)
                            self.last_payload_str = ""
                        if self.waitForAbort(5): break
                        continue

                    info = self.get_current_playing_info()
                    current_time, total_time = self.get_playback_time()
                    payload = self.build_payload(info, is_pvr, is_paused, current_time, total_time)

                    current_payload_str = str(payload)
                    if current_payload_str != self.last_payload_str:
                        log(f"Updating activity: {payload.get('details')}")
                        try:
                            self.client.set_activity(payload)
                            self.last_payload_str = current_payload_str
                        except DiscordConnectionError as e:
                            log(f"Failed to set activity: {e}", xbmc.LOGWARNING)
                            # Im nächsten Loop wird versucht neu zu verbinden
                    
                    if self.waitForAbort(5): break

                except Exception as e:
                    log(f"Service loop error: {e}", xbmc.LOGERROR)
                    # Bei generellen Fehlern kurz warten
                    if self.waitForAbort(10): break
        finally:
            try:
                if self.client:
                    self.client.disconnect()
            except Exception:
                pass
            log("Service stopped.")

if __name__ == "__main__":
    log("Starting standalone service.")
    service = DiscordKodiService()
    service.run_service()
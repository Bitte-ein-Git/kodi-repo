import xbmc
import xbmcaddon
import xbmcgui
import time
import requests
import json
import re
import urllib.parse
from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError

ADDON = xbmcaddon.Addon()
UNAVAILABLE_STATES = ["unavailable", "unknown", "no playback", "keine wiedergabe", "kodi offline"]

TMDB_API_URL = "https://api.heyfordy.de/tmdb"

CHANNEL_LOGO_MAP = {
    "top-gear": "1425598699836407858",
    "the-history-channel-sky": "1407207956877021236",
    "discovery-channel-sky": "1408572921752064073",
    "national-geographic": "1408572840256475278",
    "nick-comedy-central": "1408572683280453674",
    "kabel-eins-classics": "1408572931738701927",
    "kabel-eins-doku": "1408572829204742174",
    "prosieben-maxx": "1408572932321706015",
    "magenta-musik-1": "1408572931008757861",
    "wetter-com-tv": "1408572933277880370",
    "disney-channel": "1408572839946092564",
    "magentatv-info": "1408572840730431561",
    "comedy-central": "1408572766554427443",
    "prosieben-fun": "1408572841791848578",
    "kabel-eins": "1408572926709469184",
    "das-erste": "1408572918430171318",
    "axn-black": "1408572682936778782",
    "prosieben": "1408572920975982743",
    "rtlzwei": "1408572838964756570",
    "zdfinfo": "1408572774079008941",
    "sport1": "1408572687424553132",
    "tele-5": "1408572930752774234",
    "zdfneo": "1408572838503383232",
    "sat.1": "1408572629958398054",
    "nitro": "1408572770144489472",
    "ntv": "1408572919935664412",
    "dmax": "1408572931226730629",
    "3sat": "1408572930161508413",
    "kika": "1408572763161100448",
    "welt": "1408572923903610982",
    "arte": "1408572923836629143",
    "sixx": "1408572619518775438",
    "vox": "1408572919394598982",
    "zdf": "1408572920749621450",
    "mtv": "1408572834531246152",
}

def get_channel_logo_id(channel_name):
    normalized_channel_name = channel_name.lower().replace('-', '').replace(' ', '').replace('.', '')
    for name, logo_id in CHANNEL_LOGO_MAP.items():
        if name.replace('-', '').replace('.', '') in normalized_channel_name:
            return logo_id
    return None

def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=5000):
    xbmcgui.Dialog().notification(title, message, icon, duration)

def get_ha_sensor_state(url, token, entity_id):
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.get(f"{url}/api/states/{entity_id}", headers=headers, timeout=5)
        response.raise_for_status()
        return response.json().get("state", "")
    except requests.exceptions.RequestException as e:
        xbmc.log(f"[DiscordRPC] Error fetching {entity_id}: {e}", xbmc.LOGERROR)
        show_notification("Home Assistant Error", f"Could not reach {entity_id}", xbmcgui.NOTIFICATION_ERROR)
    return ""

def get_playing_addon(is_pvr):
    try:
        rpc_query = json.dumps({
            "jsonrpc": "2.0",
            "method": "Player.GetItem",
            "params": {"playerid": 1, "properties": ["file", "type", "studio", "art"]},
            "id": 1
        })
        rpc_response_str = xbmc.executeJSONRPC(rpc_query)
        rpc_data = json.loads(rpc_response_str)
        item = rpc_data.get('result', {}).get('item', {})
        
        file_path = item.get('file', "")
        if not file_path:
            return ""

        if is_pvr:
            art = item.get('art', {})
            for art_type in art:
                url = art[art_type].lower()
                if 'pluto.tv' in url:
                    return "Pluto.TV"
                elif 't-online' in url or 'telekom' in url:
                    return "MagentaTV"
            return "IPTV"

        if file_path.startswith('plugin://'):
            addon_id = file_path.split('/')[2]
            try:
                addon_obj = xbmcaddon.Addon(addon_id)
                addon_name = addon_obj.getAddonInfo('name')
                return addon_name
            except RuntimeError:
                return addon_id

        studios = [s.lower() for s in item.get('studio', [])]
        if any(s in ['disney', 'pixar'] for s in studios): return "Disney+"
        if any(s in ['paramount', 'viacom', 'nickelodeon'] for s in studios): return "Paramount+"
        
        if '154ca21497fd425d1677bfea175b4771' in file_path or 'f72cfc62f132f99d731c292481870375' in file_path: return "Prime Video DE"
        if 'rtla9855e4a9f748ce5bc33cbb76cd52949group' in file_path or '48495193c8f9599c52bf17a174921de4' in file_path: return "RTL+"
        if 'amazon' in file_path: return "Prime Video DE"
        if 'dmax' in file_path: return "DMAX Mediathek"
        if 'discoveryplus' in file_path: return "Discovery+"
        if 'joyn' in file_path: return "Joyn"
        if 'rtlgroup' in file_path or 'tvnow' in file_path: return "RTL+"
        if 'themoviedb' in file_path or 'tmdb' in file_path: return "TMDb Helper"
        if 'jellyfin' in file_path: return "Jellyfin"
            
    except Exception as e:
        xbmc.log(f"[DiscordRPC] Could not get playing addon name: {e}", xbmc.LOGWARNING)
    return ""

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
        xbmc.log(f"[DiscordRPC] Error fetching playback info: {e}", xbmc.LOGERROR)
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
        xbmc.log(f"[DiscordRPC] Error fetching playback time: {e}", xbmc.LOGERROR)
        return 0, 0

def time_to_seconds(self, time_dict):
    if not time_dict:
        return 0
    return (time_dict.get("hours", 0) * 3600 +
            time_dict.get("minutes", 0) * 60 +
            time_dict.get("seconds", 0) +
            time_dict.get("milliseconds", 0) / 1000.0)


class DiscordHAService(xbmc.Monitor):
    def __init__(self):
        super(DiscordHAService, self).__init__()
        self.client = None
        self.settings_changed = False
        self.load_settings()

        self.get_current_playing_info = get_current_playing_info
        self.get_playback_time = get_playback_time
        self.time_to_seconds = time_to_seconds

    def load_settings(self):
        self.app_id = ADDON.getSettingString("app_id")
        self.user_token = ADDON.getSettingString("user_token")
        self.ha_url = ADDON.getSettingString("ha_url").rstrip("/")
        self.ha_token = ADDON.getSettingString("ha_token")
        self.sensor_detail_id = ADDON.getSettingString("sensor_detail")
        self.sensor_state_id = ADDON.getSettingString("sensor_state")
        self.app_name = ADDON.getSettingString("app_name")
        self.display_addon_name = ADDON.getSettingBool("display_addon_name")
        self.media_display_mode = ADDON.getSettingString("media_display_mode")
        self.pvr_display_mode = ADDON.getSettingString("pvr_display_mode")
        self.icon_color = ADDON.getSettingString("icon_color")
        xbmc.log("[DiscordRPC] Settings loaded.", xbmc.LOGINFO)

    def onSettingsChanged(self):
        xbmc.log("[DiscordRPC] Settings changed. Triggering restart.", xbmc.LOGINFO)
        self.settings_changed = True

    def is_config_valid(self):
        return all([self.app_id, self.user_token, self.ha_url, self.ha_token, self.sensor_detail_id, self.sensor_state_id])

    def run_service(self):
        if not self.is_config_valid():
            xbmc.log("[DiscordRPC] Configuration is incomplete. Halting addon.", xbmc.LOGERROR)
            show_notification("Discord Presence", "Configuration incomplete!", xbmcgui.NOTIFICATION_ERROR)
            return

        try:
            xbmc.log("[DiscordRPC] Starting Discord client...", xbmc.LOGINFO)
            self.client = DiscordClient(self.app_id, self.user_token)
            self.client.connect()
            time.sleep(5)
            xbmc.log("[DiscordRPC] Service initialized.", xbmc.LOGINFO)
        except DiscordConnectionError as e:
            xbmc.log(f"[DiscordRPC] Initial connection failed: {e}", xbmc.LOGERROR)
            show_notification("Discord Presence", "Connection failed. Check token.", xbmcgui.NOTIFICATION_ERROR)
            return

        last_payload_str = ""

        while not self.abortRequested() and not self.settings_changed:
            try:
                if not self.client or not self.client.connected:
                    xbmc.log("[DiscordRPC] Not connected. Attempting to reconnect...", xbmc.LOGWARNING)
                    show_notification("Discord Presence", "Connection lost. Reconnecting...")
                    self.client.reconnect()
                    time.sleep(5)
                    if not self.client.connected:
                        if self.waitForAbort(15): break
                        continue

                is_playing = xbmc.Player().isPlaying()
                is_paused = xbmc.getCondVisibility('Player.Paused')
                is_pvr = xbmc.getCondVisibility("Pvr.IsPlayingTv")

                mode = self.pvr_display_mode if is_pvr else self.media_display_mode
                if not is_playing or mode == "disabled":
                    if last_payload_str:
                        xbmc.log("[DiscordRPC] Clearing presence (stopped).", xbmc.LOGINFO)
                        self.client.clear_activity()
                        last_payload_str = ""
                    if self.waitForAbort(5): break
                    continue

                details_val = get_ha_sensor_state(self.ha_url, self.ha_token, self.sensor_detail_id)
                state_val = get_ha_sensor_state(self.ha_url, self.ha_token, self.sensor_state_id)
                
                info = self.get_current_playing_info()
                current_time, total_time = self.get_playback_time()
                
                addon_name = get_playing_addon(is_pvr)

                payload = None
                if not details_val or details_val.lower() in UNAVAILABLE_STATES:
                    payload = {
                        "name": "Kodi",
                        "type": 3,
                        "application_id": self.app_id,
                        "status_display_type": 0,
                        "details": "🍿 Kodi",
                        "state": "📺 Live TV" if is_pvr else " "
                    }
                else:
                    payload = self.build_payload(is_pvr, details_val, state_val, is_paused, addon_name, info, current_time, total_time)

                if not payload:
                    if self.waitForAbort(5): break
                    continue
                
                current_payload_str = str(payload)
                if current_payload_str != last_payload_str:
                    xbmc.log(f"[DiscordRPC] Updating presence: {payload.get('details')} | Paused: {is_paused}", xbmc.LOGINFO)
                    self.client.set_activity(payload)
                    last_payload_str = current_payload_str

                if self.waitForAbort(5): break
            
            except DiscordConnectionError as e:
                xbmc.log(f"[DiscordRPC] Connection error in main loop: {e}", xbmc.LOGERROR)
                last_payload_str = ""
                if self.waitForAbort(15): break
            
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Unhandled error in loop: {e}", xbmc.LOGERROR, exc_info=True)
                show_notification("Discord Presence", "An error occurred. Restarting...", xbmcgui.NOTIFICATION_ERROR)
                if self.waitForAbort(30): break
        
        if self.client:
            xbmc.log("[DiscordRPC] Stopping service or restarting.", xbmc.LOGINFO)
            self.client.disconnect()
        
        if self.settings_changed:
            self.settings_changed = False

    def build_payload(self, is_pvr, details_val, state_val, is_paused, addon_name, info, current_time, total_time):
        app_name_str = self.app_name
        if self.display_addon_name and addon_name:
            app_name_str += f" • {addon_name}"

        payload = { "name": app_name_str, "type": 3, "application_id": self.app_id }
        
        mode_map = {
            (False, "App name"):    (details_val, state_val, 0),
            (False, "Media title"): (details_val, state_val, 2),
            (True, "App name"):      (details_val, state_val, 0),
            (True, "Channel name"):  (details_val, state_val, 2),
            (True, "TV-show title"): (state_val, details_val, 2)
        }
        mode_label = self.pvr_display_mode if is_pvr else self.media_display_mode
        config = mode_map.get((is_pvr, mode_label))

        if not config: return None

        payload["details"] = config[0]
        payload["state"] = config[1]
        payload["status_display_type"] = config[2]

        if addon_name == "Pluto.TV":
            payload["state"] = "Livestream - Pluto.TV"

        try:
            if total_time > 0 and not is_paused:
                now_ts = time.time()
                start_ts = now_ts - current_time
                end_ts = start_ts + total_time
                payload["timestamps"] = {
                    "start": int(start_ts * 1000),
                    "end": int(end_ts * 1000)
                }
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Failed to set timestamps: {e}", xbmc.LOGWARNING)

        assets = {}
        
        large_image_key = "1405130772981223454" if self.icon_color == 'Greyscale' else "1405130772981223454"
        small_image_key_pvr = "1407207956877021236" if self.icon_color == 'Greyscale' else "1407207958252884149"
        small_image_key_media = "1407207958294564884" if self.icon_color == 'Greyscale' else "1407207956914634772"
        pause_image_key = "1407207956851982336" if self.icon_color == 'Greyscale' else "1407207957422411849"
        
        small_image_key = small_image_key_pvr if is_pvr else small_image_key_media
        small_text = "Live TV" if is_pvr else "Playing"

        if is_pvr:
            channel_name = details_val 
            logo_id = get_channel_logo_id(channel_name)
            if logo_id:
                large_image_key = logo_id
        else:
            media_type = info.get("type")
            imdb_id = info.get("imdbnumber")
            media_name = None
            api_type = None

            if media_type == 'episode':
                media_name = info.get("showtitle")
                api_type = 'tv'
            elif media_type == 'movie' or (media_type in ['video', 'unknown'] and imdb_id):
                media_name = removeKodiTags(info.get("title", "Film"))
                api_type = 'movie'
            
            if api_type and (imdb_id or media_name):
                try:
                    params = {'type': api_type}
                    if imdb_id:
                        params['id'] = imdb_id
                    elif media_name:
                        params['name'] = media_name
                    
                    large_image_key = f"{TMDB_API_URL}?{urllib.parse.urlencode(params)}"
                    xbmc.log(f"[DiscordRPC] Using dynamic artwork URL: {large_image_key}")
                except Exception as e:
                    xbmc.log(f"[DiscordRPC] Failed to build artwork URL: {e}", xbmc.LOGWARNING)

        assets["large_image"] = large_image_key
        assets["large_text"] = details_val if not is_pvr else state_val
        assets["small_image"] = small_image_key
        assets["small_text"] = small_text
        
        if is_paused:
            assets["small_image"] = pause_image_key
            assets["small_text"] = "PAUSE ⏸️"
            payload["state"] = "PAUSE ⏸️" 
            if "timestamps" in payload:
                del payload["timestamps"]
        
        payload["assets"] = assets
        return payload

if __name__ == "__main__":
    xbmc.log("[DiscordRPC] Addon starting.", xbmc.LOGINFO)
    service = DiscordHAService()
    
    while not xbmc.Monitor().abortRequested():
        try:
            service.load_settings()
            service.run_service()
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Unhandled exception, restarting in 30s: {e}", xbmc.LOGERROR, exc_info=True)
            show_notification("Discord Presence", "Addon crashed! Restarting...", xbmcgui.NOTIFICATION_ERROR)
            if xbmc.Monitor().waitForAbort(30):
                break
        
        if service.settings_changed:
            xbmc.log("[DiscordRPC] Restarting due to settings change.", xbmc.LOGINFO)
        elif not xbmc.Monitor().abortRequested():
            if xbmc.Monitor().waitForAbort(2):
                break

    xbmc.log("[DiscordRPC] Addon has been shut down.", xbmc.LOGINFO)
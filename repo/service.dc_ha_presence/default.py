import xbmc
import xbmcaddon
import xbmcgui
import time
import requests
import json
from resources.lib.discord_gateway import DiscordClient

ADDON = xbmcaddon.Addon()
UNAVAILABLE_STATES = ["unavailable", "unknown", "no playback", "keine wiedergabe", "kodi offline"]

def get_ha_sensor_state(url, token, entity_id):
    # fetch ha sensor state
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.get(f"{url}/api/states/{entity_id}", headers=headers, timeout=5)
        response.raise_for_status()
        return response.json().get("state", "")
    except requests.exceptions.RequestException as e:
        xbmc.log(f"[DiscordRPC] Error fetching {entity_id}: {e}", xbmc.LOGERROR)
    return ""

def get_playing_addon(is_pvr):
    # get playing addon name
    if is_pvr:
        return "IPTV"
        
    try:
        rpc_query = json.dumps({
            "jsonrpc": "2.0",
            "method": "Player.GetItem",
            "params": {"playerid": 1, "properties": ["file", "type", "studio"]},
            "id": 1
        })
        rpc_response_str = xbmc.executeJSONRPC(rpc_query)
        rpc_data = json.loads(rpc_response_str)
        item = rpc_data.get('result', {}).get('item', {})
        
        file_path = item.get('file')
        studios = [s.lower() for s in item.get('studio', [])]

        if not file_path: return ""

        # studio checks
        if any(s in ['disney', 'pixar'] for s in studios): return "Disney +"
        if any(s in ['paramount', 'viacom', 'nickelodeon'] for s in studios): return "Paramount +"
        
        # file path checks
        if '154ca21497fd425d1677bfea175b4771' in file_path or 'f72cfc62f132f99d731c292481870375' in file_path: return "Prime Video DE"
        if 'rtla9855e4a9f748ce5bc33cbb76cd52949group' in file_path or '48495193c8f9599c52bf17a174921de4' in file_path: return "TMDb Helper"
        if 'amazon' in file_path: return "Prime Video DE"
        if 'disney' in file_path: return "Disney +"
        if 'dmax' in file_path: return "DMAX Mediathek"
        if 'discoveryplus' in file_path: return "Discovery +"
        if 'joyn' in file_path: return "Joyn"
        if 'rtlgroup' in file_path or 'tvnow' in file_path: return "RTL +"
        if 'xship' in file_path: return "xShip"
        if 'xstream' in file_path: return "xStream"
        if 'themoviedb' in file_path or 'tmdb' in file_path: return "TMDb Helper"
        if 'jellyfin' in file_path: return "Jellyfin"
        
        # plugin path check
        if file_path.startswith('plugin://'):
            parts = file_path.split('/')
            return parts[2] if len(parts) > 2 else ""
            
    except Exception as e:
        xbmc.log(f"[DiscordRPC] Could not get playing addon name: {e}", xbmc.LOGWARNING)
    return ""

def time_obj_to_seconds(time_dict):
    # convert time object to seconds
    if not isinstance(time_dict, dict): return 0
    return (time_dict.get('hours', 0) * 3600 +
            time_dict.get('minutes', 0) * 60 +
            time_dict.get('seconds', 0) +
            time_dict.get('milliseconds', 0) / 1000.0)

class DiscordHAService(xbmc.Monitor):
    def __init__(self):
        super(DiscordHAService, self).__init__()
        self.client = None
        self.settings_changed = False
        self.load_settings()

    def load_settings(self):
        # load addon settings
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
        # handle settings changes
        xbmc.log("[DiscordRPC] Settings changed. Triggering restart.", xbmc.LOGINFO)
        self.settings_changed = True

    def is_config_valid(self):
        # validate configuration
        return all([self.app_id, self.user_token, self.ha_url, self.ha_token, self.sensor_detail_id, self.sensor_state_id])

    def run_service(self):
        # main service loop
        if not self.is_config_valid():
            xbmc.log("[DiscordRPC] Configuration is incomplete. Halting addon.", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("Discord Presence", "Configuration incomplete!", xbmcgui.NOTIFICATION_ERROR, 5000)
            return

        xbmc.log("[DiscordRPC] Starting Discord client...", xbmc.LOGINFO)
        self.client = DiscordClient(self.app_id, self.user_token)
        self.client.connect()
        time.sleep(5)
        xbmc.log("[DiscordRPC] Service initialized.", xbmc.LOGINFO)

        last_payload_str = ""

        while not self.abortRequested() and not self.settings_changed:
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
                state_val = get_ha_sensor_state(self.ha_url, self.ha_token, self.sensor_state_id)
                addon_name = get_playing_addon(is_pvr)
                payload = self.build_payload(is_pvr, details_val, state_val, is_paused, addon_name)

            if not payload:
                if self.waitForAbort(5): break
                continue
            
            current_payload_str = str(payload)
            if current_payload_str != last_payload_str:
                xbmc.log(f"[DiscordRPC] Updating presence: {payload.get('details')} | Paused: {is_paused}", xbmc.LOGINFO)
                self.client.set_activity(payload)
                last_payload_str = current_payload_str

            if self.waitForAbort(5): break
        
        if self.client:
            xbmc.log("[DiscordRPC] Stopping service or restarting.", xbmc.LOGINFO)
            self.client.disconnect()
        
        if self.settings_changed:
            self.settings_changed = False

    def build_payload(self, is_pvr, details_val, state_val, is_paused, addon_name):
        # build discord payload
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

        try:
            rpc_query = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetProperties",
                "params": {"playerid": 1, "properties": ["time", "totaltime"]},
                "id": 1
            })
            rpc_response_str = xbmc.executeJSONRPC(rpc_query)
            rpc_data = json.loads(rpc_response_str)

            if 'result' in rpc_data:
                time_data = rpc_data['result']
                current_time_sec = time_obj_to_seconds(time_data.get('time'))
                total_time_sec = time_obj_to_seconds(time_data.get('totaltime'))

                if total_time_sec > 0:
                    now_ts = time.time()
                    start_ts = now_ts - current_time_sec
                    end_ts = start_ts + total_time_sec
                    payload["timestamps"] = {
                        "start": int(start_ts * 1000),
                        "end": int(end_ts * 1000)
                    }
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Failed to set timestamps via JSONRPC: {e}", xbmc.LOGWARNING)

        if self.icon_color == 'Greyscale':
            assets = {
                "small_image": "1407207956877021236" if is_pvr else "1407207958294564884",
                "large_text": state_val if is_pvr else details_val
            }
            
            if is_paused:
                assets["small_image"] = "1407207956851982336"
                assets["small_text"] = "𝗣𝗔𝗨𝗦𝗘 ⏸️"
                payload["state"] = "𝗣𝗔𝗨𝗦𝗘 ⏸️"

                if "timestamps" in payload:
                    del payload["timestamps"]
            
            payload["assets"] = assets
            
            return payload

        if self.icon_color == 'Colored':
            assets = {
                "small_image": "1407207958252884149" if is_pvr else "1407207956914634772",
                "large_text": state_val if is_pvr else details_val
            }
            
            if is_paused:
                assets["small_image"] = "1407207957422411849"
                assets["small_text"] = "𝗣𝗔𝗨𝗦𝗘 ⏸️"
                payload["state"] = "𝗣𝗔𝗨𝗦𝗘 ⏸️"

                if "timestamps" in payload:
                    del payload["timestamps"]
            
            payload["assets"] = assets
            
            return payload
        return None

if __name__ == "__main__":
    xbmc.log("[DiscordRPC] Addon starting.", xbmc.LOGINFO)
    service = DiscordHAService()
    
    while not xbmc.Monitor().abortRequested():
        try:
            service.load_settings()
            service.run_service()
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Unhandled error, restarting in 30s: {e}", xbmc.LOGERROR, exc_info=True)
            if xbmc.Monitor().waitForAbort(30): break
        else:
            if xbmc.Monitor().waitForAbort(2): break
    
    xbmc.log("[DiscordRPC] Addon has been shut down.", xbmc.LOGINFO)

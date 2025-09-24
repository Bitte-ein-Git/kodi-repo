import xbmc
import xbmcaddon
import xbmcgui
import time
import requests
import json
from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError

ADDON = xbmcaddon.Addon()
UNAVAILABLE_STATES = ["unavailable", "unknown", "no playback", "keine wiedergabe", "kodi offline"]

def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=5000):
    # display a notification in kodi
    xbmcgui.Dialog().notification(title, message, icon, duration)

def get_ha_sensor_state(url, token, entity_id):
    # fetch ha sensor state
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
        
        file_path = item.get('file', "")
        if not file_path:
            return ""

        # Check if it's a plugin path first, as it's the most reliable
        if file_path.startswith('plugin://'):
            addon_id = file_path.split('/')[2]
            try:
                # Use addon.xml to get a user-friendly name
                addon_obj = xbmcaddon.Addon(addon_id)
                addon_name = addon_obj.getAddonInfo('name')
                return addon_name
            except RuntimeError:
                # Fallback to addon_id if getting info fails
                return addon_id

        # Fallback to studio and file path checks if not a direct plugin path
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
                    time.sleep(5) # give it time to reconnect
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
            
            except DiscordConnectionError as e:
                xbmc.log(f"[DiscordRPC] Connection error in main loop: {e}", xbmc.LOGERROR)
                last_payload_str = "" # force update after reconnect
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

                if total_time_sec > 0 and not is_paused:
                    now_ts = time.time()
                    start_ts = now_ts - current_time_sec
                    end_ts = start_ts + total_time_sec
                    payload["timestamps"] = {
                        "start": int(start_ts * 1000),
                        "end": int(end_ts * 1000)
                    }
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Failed to set timestamps via JSONRPC: {e}", xbmc.LOGWARNING)

        assets = {}
        large_image_key = "1407207958294564884" if self.icon_color == 'Greyscale' else "1407207956914634772"
        small_image_key = "1407207956877021236" if self.icon_color == 'Greyscale' else "1407207958252884149"
        pause_image_key = "1407207956851982336" if self.icon_color == 'Greyscale' else "1407207957422411849"

        assets["large_image"] = large_image_key
        assets["large_text"] = details_val if not is_pvr else state_val
        assets["small_image"] = small_image_key
        assets["small_text"] = "Live TV"
        
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
            service.load_settings() # reload settings in case they changed
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

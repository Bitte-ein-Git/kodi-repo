import xbmc
import xbmcaddon
import xbmcgui
import time
import requests
from resources.lib.discord_gateway import DiscordClient

ADDON = xbmcaddon.Addon()

def get_ha_sensor_state(url, token, entity_id):
    # Fetches a sensor state from Home Assistant.
    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.get(f"{url}/api/states/{entity_id}", headers=headers, timeout=5)
        response.raise_for_status()
        return response.json().get("state", "")
    except requests.exceptions.RequestException as e:
        xbmc.log(f"[DiscordRPC] Error fetching {entity_id}: {e}", xbmc.LOGERROR)
    return ""

class DiscordHAService(xbmc.Monitor):
    def __init__(self):
        super(DiscordHAService, self).__init__()
        self.client = None
        self.settings_changed = False
        self.load_settings()

    def load_settings(self):
        # Load all required settings from the addon configuration.
        self.app_id = ADDON.getSettingString("app_id")
        self.user_token = ADDON.getSettingString("user_token")
        self.ha_url = ADDON.getSettingString("ha_url").rstrip("/")
        self.ha_token = ADDON.getSettingString("ha_token")
        self.sensor_detail_id = ADDON.getSettingString("sensor_detail")
        self.sensor_state_id = ADDON.getSettingString("sensor_state")
        self.app_name = ADDON.getSettingString("app_name")
        self.media_display_mode = ADDON.getSettingString("media_display_mode")
        self.pvr_display_mode = ADDON.getSettingString("pvr_display_mode")
        xbmc.log("[DiscordRPC] Settings loaded.", xbmc.LOGINFO)

    def onSettingsChanged(self):
        # Triggered when addon settings are changed.
        xbmc.log("[DiscordRPC] Settings changed. Triggering restart.", xbmc.LOGINFO)
        self.settings_changed = True

    def is_config_valid(self):
        # Check if the essential configuration is complete.
        return all([self.app_id, self.user_token, self.ha_url, self.ha_token, self.sensor_detail_id, self.sensor_state_id])

    def run_service(self):
        # Main service logic.
        if not self.is_config_valid():
            xbmc.log("[DiscordRPC] Configuration is incomplete. Halting addon.", xbmc.LOGERROR)
            xbmcgui.Dialog().notification("Discord Presence", "Configuration incomplete!", xbmcgui.NOTIFICATION_ERROR, 5000)
            return

        xbmc.log("[DiscordRPC] Starting Discord client...", xbmc.LOGINFO)
        self.client = DiscordClient(self.app_id, self.user_token)
        self.client.connect()
        time.sleep(5) # Give the websocket time to connect.
        xbmc.log("[DiscordRPC] Service initialized.", xbmc.LOGINFO)

        last_payload_str = ""

        while not self.abortRequested() and not self.settings_changed:
            is_playing = xbmc.Player().isPlaying()
            is_paused = xbmc.getCondVisibility('Player.Paused')
            is_pvr = xbmc.getCondVisibility("Pvr.IsPlayingTv")
            
            mode = self.pvr_display_mode if is_pvr else self.media_display_mode
            if not is_playing or mode == "disabled":
                if self.waitForAbort(5): break
                continue

            details_val = get_ha_sensor_state(self.ha_url, self.ha_token, self.sensor_detail_id)
            state_val = get_ha_sensor_state(self.ha_url, self.ha_token, self.sensor_state_id)

            payload = self.build_payload(is_pvr, details_val, state_val, is_paused)

            if not payload:
                if self.waitForAbort(5): break
                continue
            
            # Only send an update if the payload has changed.
            current_payload_str = str(payload)
            if current_payload_str != last_payload_str:
                xbmc.log(f"[DiscordRPC] Updating presence: {payload.get('details')} | Paused: {is_paused}", xbmc.LOGINFO)
                self.client.set_activity(payload)
                last_payload_str = current_payload_str

            if self.waitForAbort(5): break
        
        if self.client:
            xbmc.log("[DiscordRPC] Stopping service or restarting.", xbmc.LOGINFO)
            self.client.disconnect()
        
        if self.settings_changed: self.settings_changed = False


    def build_payload(self, is_pvr, details_val, state_val, is_paused):
        # Builds the presence payload dictionary based on current state.
        payload = { "name": self.app_name, "type": 3, "application_id": self.app_id }
        
        mode_map = {
            # (is_pvr, display_mode_label): (details, state, status_display_type)
            (False, "App name"):    (details_val, state_val, 0),
            (False, "Media title"): (details_val, state_val, 2),
            (True, "App name"):      (details_val, state_val, 0),
            (True, "Channel name"):  (state_val, details_val, 2),
            (True, "TV-show title"): (details_val, state_val, 2)
        }
        
        mode_label = self.pvr_display_mode if is_pvr else self.media_display_mode
        config = mode_map.get((is_pvr, mode_label))

        if not config: return None

        payload["details"] = config[0]
        payload["state"] = config[1]
        payload["status_display_type"] = config[2]

        # Hardcoded asset keys.
        assets = {
            "small_image": "1407207956877021236" if is_pvr else "1407207958294564884",
            "large_text": state_val if is_pvr else details_val
        }
        
        if is_paused:
            assets["small_image"] = "1407207956851982336"
            assets["small_text"] = "Paused"
        
        payload["assets"] = assets
        
        return payload

if __name__ == "__main__":
    xbmc.log("[DiscordRPC] Addon starting.", xbmc.LOGINFO)
    service = DiscordHAService()
    
    # Main loop to ensure the service restarts on unexpected errors.
    while not xbmc.Monitor().abortRequested():
        try:
            service.load_settings()
            service.run_service()
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Unhandled error, restarting in 30s: {e}", xbmc.LOGERROR, exc_info=True)
            if xbmc.Monitor().waitForAbort(30): break
        else:
            # Normal exit (e.g. settings changed), restart quickly.
            if xbmc.Monitor().waitForAbort(2): break
    
    xbmc.log("[DiscordRPC] Addon has been shut down.", xbmc.LOGINFO)
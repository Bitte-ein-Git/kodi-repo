import xbmc
import xbmcaddon
import xbmcgui
import time
import requests
import json
import os
from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError
from resources.lib.image_uploader import decode_kodi_image_url, upload_to_imgbb

ADDON = xbmcaddon.Addon()
UNAVAILABLE_STATES = ["unavailable", "unknown", "no playback", "keine wiedergabe", "kodi offline"]

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

def time_obj_to_seconds(time_dict):
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
        self.enable_dynamic_artwork = ADDON.getSettingBool("enable_dynamic_artwork")
        self.imgbb_api_key = ADDON.getSettingString("imgbb_api_key")
        xbmc.log("[DiscordRPC] Settings loaded.", xbmc.LOGINFO)

    def onSettingsChanged(self):
        xbmc.log("[DiscordRPC] Settings changed. Triggering restart.", xbmc.LOGINFO)
        self.settings_changed = True

    def is_config_valid(self):
        return all([self.app_id, self.user_token, self.ha_url, self.ha_token, self.sensor_detail_id, self.sensor_state_id])

    def run_service(self):
        if not self.is_config_valid():
            xbmc.log("[DiscordRPC] Configuration incomplete. Halting addon.", xbmc.LOGERROR)
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
                    payload = self.build_payload(is_pvr, details_val, state_val, is_paused)

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
                xbmc.log(f"[DiscordRPC] Connection error: {e}", xbmc.LOGERROR)
                last_payload_str = ""
                if self.waitForAbort(15): break
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Loop error: {e}", xbmc.LOGERROR, exc_info=True)
                show_notification("Discord Presence", "An error occurred.", xbmcgui.NOTIFICATION_ERROR)
                if self.waitForAbort(30): break

        if self.client:
            self.client.disconnect()
        if self.settings_changed:
            self.settings_changed = False

    def build_payload(self, is_pvr, details_val, state_val, is_paused):
        payload = {"name": self.app_name, "type": 3, "application_id": self.app_id}

        assets = {}
        large_image_key = "1405130772981223454"
        small_image_key = "1407207958294564884"
        pause_image_key = "1407207956851982336"

        if is_pvr:
            logo_id = get_channel_logo_id(details_val)
            if logo_id:
                large_image_key = logo_id
            assets["small_text"] = "Live TV"
        else:
            assets["small_text"] = "Streaming"

        if self.enable_dynamic_artwork and self.imgbb_api_key:
            try:
                rpc_query = json.dumps({
                    "jsonrpc": "2.0",
                    "method": "Player.GetItem",
                    "params": {"playerid": 1, "properties": ["art"]},
                    "id": 1
                })
                rpc_response = xbmc.executeJSONRPC(rpc_query)
                rpc_data = json.loads(rpc_response)
                art = rpc_data.get("result", {}).get("item", {}).get("art", {})
                art_url = art.get("thumb") if is_pvr else art.get("fanart") or art.get("poster")
                decoded_path = decode_kodi_image_url(art_url)
                if decoded_path and os.path.exists(decoded_path):
                    uploaded_url = upload_to_imgbb(decoded_path, self.imgbb_api_key)
                    if uploaded_url:
                        large_image_key = uploaded_url
                        xbmc.log(f"[DiscordRPC] Using dynamic artwork: {uploaded_url}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Dynamic artwork failed: {e}", xbmc.LOGWARNING)

        assets["large_image"] = large_image_key
        assets["large_text"] = details_val
        assets["small_image"] = pause_image_key if is_paused else small_image_key

        payload["assets"] = assets
        payload["details"] = details_val
        payload["state"] = state_val

        return payload

if __name__ == "__main__":
    xbmc.log("[DiscordRPC] Addon starting.", xbmc.LOGINFO)
    service = DiscordHAService()
    while not xbmc.Monitor().abortRequested():
        try:
            service.load_settings()
            service.run_service()
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Unhandled exception: {e}", xbmc.LOGERROR, exc_info=True)
            show_notification("Discord Presence", "Addon crashed! Restarting...", xbmcgui.NOTIFICATION_ERROR)
            if xbmc.Monitor().waitForAbort(30):
                break
        if service.settings_changed:
            xbmc.log("[DiscordRPC] Restarting due to settings change.", xbmc.LOGINFO)
        elif not xbmc.Monitor().abortRequested():
            if xbmc.Monitor().waitForAbort(2):
                break
    xbmc.log("[DiscordRPC] Addon stopped.", xbmc.LOGINFO)

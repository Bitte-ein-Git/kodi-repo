import xbmc
import xbmcaddon
import xbmcgui
import json
import time
import os
import requests
from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError
from resources.lib.image_uploader import decode_kodi_image_url, upload_to_imgbb

ADDON = xbmcaddon.Addon()

CHANNEL_LOGO_MAP = {
    "das-erste": "1408572918430171318",
    "zdf": "1408572920749621450",
    "prosieben": "1408572920975982743",
    "rtl": "1408572926709469184",
    "vox": "1408572919394598982",
    "arte": "1408572923836629143",
    "3sat": "1408572930161508413",
    "kabel-eins": "1408572926709469184",
    "sat.1": "1408572629958398054",
    "sport1": "1408572687424553132",
    "nick": "1408572683280453674",
    "kika": "1408572763161100448",
    "zdfneo": "1408572838503383232",
    "ntv": "1408572919935664412",
    "dmax": "1408572931226730629",
    "discovery": "1408572921752064073",
    "national-geographic": "1408572840256475278",
    "redbulltv": "1425598699836407858"
}


def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=4000):
    # display notification
    xbmcgui.Dialog().notification(title, message, icon, duration)


def get_channel_logo_id(channel_name):
    # map channel name to discord asset id
    if not channel_name:
        return None
    normalized = channel_name.lower().replace('-', '').replace(' ', '').replace('.', '')
    for name, logo_id in CHANNEL_LOGO_MAP.items():
        if name.replace('-', '').replace('.', '') in normalized:
            return logo_id
    return None


class DiscordKodiService(xbmc.Monitor):
    def __init__(self):
        super(DiscordKodiService, self).__init__()
        self.client = None
        self.last_payload_str = ""
        self.load_settings()

    def load_settings(self):
        # load addon settings
        self.app_id = ADDON.getSettingString("app_id")
        self.user_token = ADDON.getSettingString("user_token")
        self.app_name = ADDON.getSettingString("app_name")
        self.enable_dynamic_artwork = ADDON.getSettingBool("enable_dynamic_artwork")
        self.imgbb_api_key = ADDON.getSettingString("imgbb_api_key")
        self.icon_color = ADDON.getSettingString("icon_color")
        xbmc.log("[DiscordRPC] Settings loaded.", xbmc.LOGINFO)

    def is_config_valid(self):
        # check required settings
        return all([self.app_id, self.user_token])

    def get_current_playing_info(self):
        # get player item details via jsonrpc
        try:
            rpc_query = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {"playerid": 1, "properties": ["title", "showtitle", "season", "episode", "album", "artist", "genre", "streamdetails", "art", "duration", "channel"]},
                "id": 1
            })
            rpc_response = xbmc.executeJSONRPC(rpc_query)
            data = json.loads(rpc_response)
            return data.get("result", {}).get("item", {})
        except Exception as e:
            xbmc.log(f"[DiscordRPC] Error fetching playback info: {e}", xbmc.LOGERROR)
            return {}

    def get_playback_time(self):
        # get player time properties via jsonrpc
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
        # convert kodi time object to seconds
        if not time_dict:
            return 0
        return (time_dict.get("hours", 0) * 3600 +
                time_dict.get("minutes", 0) * 60 +
                time_dict.get("seconds", 0) +
                time_dict.get("milliseconds", 0) / 1000.0)

    def build_payload(self, info, is_pvr, is_paused, current_time, total_time):
        # build the discord activity payload
        details = info.get("title") or info.get("label") or "Unbekannter Titel"
        state = ""
        assets = {}
        
        # select assets based on icon color setting
        if self.icon_color == 'Greyscale':
            large_image_key = "1405130772981223454"
            small_image_key_pvr = "1407207956877021236"
            small_image_key_media = "1407207958294564884"
            pause_image_key = "1407207956851982336"
        else: # colored
            large_image_key = "1405130772981223454"
            small_image_key_pvr = "1407207958252884149"
            small_image_key_media = "1407207956914634772"
            pause_image_key = "1407207957422411849"
            
        small_image_key = small_image_key_pvr
        small_text = "Live TV"

        if is_pvr:
            channel_name = info.get("channel", "")
            logo_id = get_channel_logo_id(channel_name)
            if logo_id:
                large_image_key = logo_id
            state = f"📺 {channel_name}"
        else:
            state = "🎬 " + (info.get("showtitle") or "Film / Addon")
            small_image_key = small_image_key_media
            small_text = "Playing"

        # dynamic artwork upload
        if self.enable_dynamic_artwork and self.imgbb_api_key:
            try:
                art = info.get("art", {})
                art_url = art.get("thumb") if is_pvr else art.get("fanart") or art.get("poster")
                decoded = decode_kodi_image_url(art_url)
                if decoded and os.path.exists(decoded):
                    uploaded = upload_to_imgbb(decoded, self.imgbb_api_key)
                    if uploaded:
                        large_image_key = uploaded
                        xbmc.log(f"[DiscordRPC] Uploaded artwork: {uploaded}", xbmc.LOGINFO)
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Dynamic artwork failed: {e}", xbmc.LOGWARNING)

        # handle pause state
        if is_paused:
            small_image_key = pause_image_key
            small_text = "PAUSE ⏸️"
            
        # timestamps for playback progress
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
            "name": self.app_name or "Kodi",
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
        # main service loop
        if not self.is_config_valid():
            xbmc.log("[DiscordRPC] Incomplete configuration.", xbmc.LOGERROR)
            show_notification("Discord Presence", "Configuration incomplete!", xbmcgui.NOTIFICATION_ERROR)
            return

        try:
            self.client = DiscordClient(self.app_id, self.user_token)
            self.client.connect()
            xbmc.log("[DiscordRPC] Discord client connected.", xbmc.LOGINFO)
        except DiscordConnectionError as e:
            xbmc.log(f"[DiscordRPC] Connection failed: {e}", xbmc.LOGERROR)
            show_notification("Discord Presence", "Connection failed to Discord.", xbmcgui.NOTIFICATION_ERROR)
            return

        while not self.abortRequested():
            try:
                if not self.client.connected.is_set():
                    xbmc.log("[DiscordRPC] Not connected. Attempting reconnect.", xbmc.LOGWARNING)
                    try:
                        self.client.reconnect()
                    except DiscordConnectionError:
                        xbmc.log("[DiscordRPC] Reconnect failed. Retrying later.", xbmc.LOGERROR)
                    if self.waitForAbort(15): break
                    continue

                player = xbmc.Player()
                is_playing = player.isPlaying()
                is_paused = xbmc.getCondVisibility("Player.Paused")
                is_pvr = xbmc.getCondVisibility("Pvr.IsPlayingTv")

                if not is_playing:
                    if self.last_payload_str:
                        xbmc.log("[DiscordRPC] Stopped, clearing presence.", xbmc.LOGINFO)
                        self.client.clear_activity()
                        self.last_payload_str = ""
                    if self.waitForAbort(5): break
                    continue

                info = self.get_current_playing_info()
                current_time, total_time = self.get_playback_time()
                payload = self.build_payload(info, is_pvr, is_paused, current_time, total_time)

                current_payload_str = str(payload)
                if current_payload_str != self.last_payload_str:
                    xbmc.log(f"[DiscordRPC] Updating activity: {payload.get('details')}", xbmc.LOGINFO)
                    self.client.set_activity(payload)
                    self.last_payload_str = current_payload_str

                if self.waitForAbort(10): break

            except DiscordConnectionError as e:
                 xbmc.log(f"[DiscordRPC] Connection error in loop: {e}", xbmc.LOGERROR)
                 self.last_payload_str = ""
                 if self.waitForAbort(15): break
            except Exception as e:
                xbmc.log(f"[DiscordRPC] Service error: {e}", xbmc.LOGERROR, exc_info=True)
                show_notification("Discord Presence", "Error in DiscordRPC loop.", xbmcgui.NOTIFICATION_ERROR)
                if self.waitForAbort(15): break

        if self.client:
            self.client.disconnect()
        xbmc.log("[DiscordRPC] Service stopped.", xbmc.LOGINFO)


if __name__ == "__main__":
    xbmc.log("[DiscordRPC] Starting standalone service.", xbmc.LOGINFO)
    service = DiscordKodiService()
    service.run_service()
import xbmc
import xbmcaddon
import xbmcgui
import json
import time
import urllib.parse
import re
import requests
from resources.lib.discord_gateway import DiscordClient, DiscordConnectionError

ADDON = xbmcaddon.Addon()
IMAGES_URL = "https://api.heyfordy.de/tmdb" # global var for artwork lookup

def log(msg, level=xbmc.LOGINFO):
    # helper for logging
    xbmc.log(f"[DiscordRPC] {msg}", level)

def show_notification(title, message, icon=xbmcgui.NOTIFICATION_INFO, duration=4000):
    # display notification
    log(f"Notification: {title} - {message}", xbmc.LOGDEBUG)
    xbmcgui.Dialog().notification(title, message, icon, duration)

def removeKodiTags(text):
    # remove kodi color/style tags from string
    if not text:
        return ""
    
    log(f"Removing tags for: {text}", xbmc.LOGDEBUG)
    validTags = ["I", "B", "LIGHT", "UPPERCASE", "LOWERCASE", "CAPITALIZE", "COLOR"]
    
    for tag in validTags:
        r = re.compile(r"\[\s*/?\s*"+tag+r"\s*?\]")
        text = r.sub("", text)

    r = re.compile(r"\[\s*/?\s*CR\s*?\]")
    text = r.sub(" ", text)

    r = re.compile(r"\[\s*/?\s*COLOR\s*?.*?\]")
    text = r.sub("", text)

    log(f"Removed tags. Result: {text}", xbmc.LOGDEBUG)
    return text

def decode_kodi_image_url(image_url):
    # decode kodi image url
    if not image_url:
        return None
    try:
        if image_url.startswith("image://"):
            clean_url = image_url[len("image://"):]
            if clean_url.endswith("/"):
                clean_url = clean_url[:-1]
            return urllib.parse.unquote(clean_url)
        return image_url
    except Exception as e:
        log(f"Image decode failed: {e}", xbmc.LOGWARNING)
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
        self.icon_color = ADDON.getSettingString("icon_color")
        log("Settings loaded.", xbmc.LOGINFO)

    def is_config_valid(self):
        # check required settings
        return all([self.app_id, self.user_token])

    def get_current_playing_info(self):
        # get player item details via jsonrpc
        try:
            rpc_query = json.dumps({
                "jsonrpc": "2.0",
                "method": "Player.GetItem",
                "params": {"playerid": 1, "properties": ["title", "showtitle", "season", "episode", "album", "artist", "genre", "streamdetails", "art", "duration", "channel", "year", "uniqueid"]},
                "id": 1
            })
            rpc_response = xbmc.executeJSONRPC(rpc_query)
            data = json.loads(rpc_response)
            return data.get("result", {}).get("item", {})
        except Exception as e:
            log(f"Error fetching playback info: {e}", xbmc.LOGERROR)
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
            log(f"Error fetching playback time: {e}", xbmc.LOGERROR)
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
        title = info.get("title") or info.get("label") or "Unbekannter Titel"
        year = info.get("year", 0) or 0
        
        details = ""
        state = ""
        assets = {}
        art = info.get("art", {})
        art_url = None
        
        # artwork search metadata
        search_name = ""
        search_id = info.get("uniqueid", {}).get("imdb", "") # use IMDB ID if available
        search_type = "movie"
        
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
        default_large_image_key = large_image_key # save default asset

        if is_pvr:
            channel_name = info.get("channel", "")
            clean_title = removeKodiTags(title)
            details = f"{clean_title} ({year})" if year > 0 else clean_title
            
            season = info.get("season", 0) or 0
            episode = info.get("episode", 0) or 0
            
            if season > 0 and episode > 0:
                state = f"🎞️ S{season:02d}E{episode:02d} • {channel_name}"
                search_type = "tv"
            else:
                state = channel_name
                search_type = "movie" # assume movie if no S/E info
                
            art_url = art.get("thumb")
            search_name = clean_title
        else:
            art_url = art.get("poster") or art.get("tvshow.poster") or art.get("thumb")
            
            showtitle = info.get("showtitle")
            season = info.get("season", 0) or 0
            episode = info.get("episode", 0) or 0
            
            if showtitle and season > 0 and episode > 0:
                # series
                clean_showtitle = removeKodiTags(showtitle)
                clean_ep_title = removeKodiTags(title)
                details = f"{clean_showtitle} ({year})" if year > 0 else clean_showtitle
                state = f"🎞️ S{season:02d}E{episode:02d} • {clean_ep_title}"
                search_name = clean_showtitle
                search_type = "tv"
            else:
                # movie or addon
                clean_title = removeKodiTags(title)
                details = f"{clean_title} ({year})" if year > 0 else clean_title
                
                genres = info.get("genre", [])
                if genres:
                    state = "🎭 » " + ", ".join(genres)
                else:
                    state = "🎬 Movie"
                search_name = clean_title
                search_type = "movie"
            
            small_image_key = small_image_key_media
            small_text = "Playing"

        # dynamic artwork processing
        if art_url:
            decoded_url = decode_kodi_image_url(art_url)
            
            if decoded_url and (decoded_url.startswith("http://") or decoded_url.startswith("https://")):
                # remote url (http/https), pass to discord gateway
                large_image_key = decoded_url
                log(f"Using decoded remote URL: {decoded_url}", xbmc.LOGINFO)
            # else: keep default large_image_key
        
        elif IMAGES_URL and search_name:
            # no local art, try tmdb lookup via our worker
            log(f"No local art found. Attempting TMDB lookup for: {search_name}", xbmc.LOGINFO)
            
            # hyphen fallback logic
            if " - " in search_name:
                hyphen_search_name = search_name.split(" - ", 1)[0]
                log(f"Title contains hyphen. Using primary part: {hyphen_search_name}", xbmc.LOGDEBUG)
                search_name = hyphen_search_name
                
            try:
                tmdb_art_url = f"{IMAGES_URL}?name={urllib.parse.quote(search_name)}&id={urllib.parse.quote(search_id)}&type={search_type}"
                large_image_key = tmdb_art_url
            except Exception as e:
                log(f"Error building TMDB URL: {e}", xbmc.LOGWARNING)
                large_image_key = default_large_image_key
        
        else:
             large_image_key = default_large_image_key

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
        # main service loop
        if not self.is_config_valid():
            log("Incomplete configuration.", xbmc.LOGERROR)
            show_notification("Discord Presence", "Configuration incomplete!", xbmc.gui.NOTIFICATION_ERROR)
            return

        try:
            self.client = DiscordClient(self.app_id, self.user_token)
            self.client.connect()
            log("Discord client connected.", xbmc.LOGINFO)
        except DiscordConnectionError as e:
            log(f"Connection failed: {e}", xbmc.LOGERROR)
            show_notification("Discord Presence", "Connection failed to Discord.", xbmc.gui.NOTIFICATION_ERROR)
            return

        while not self.abortRequested():
            try:
                if not self.client.connected.is_set():
                    log("Not connected. Attempting reconnect.", xbmc.LOGWARNING)
                    try:
                        self.client.reconnect()
                    except DiscordConnectionError:
                        log("Reconnect failed. Retrying later.", xbmc.LOGERROR)
                    if self.waitForAbort(15): break
                    continue

                player = xbmc.Player()
                is_playing = player.isPlaying()
                is_paused = xbmc.getCondVisibility("Player.Paused")
                is_pvr = xbmc.getCondVisibility("Pvr.IsPlayingTv")

                if not is_playing:
                    if self.last_payload_str:
                        log("Stopped, clearing presence.", xbmc.LOGINFO)
                        self.client.clear_activity()
                        self.last_payload_str = ""
                    if self.waitForAbort(5): break
                    continue

                info = self.get_current_playing_info()
                current_time, total_time = self.get_playback_time()
                payload = self.build_payload(info, is_pvr, is_paused, current_time, total_time)

                current_payload_str = str(payload)
                if current_payload_str != self.last_payload_str:
                    log(f"Updating activity: {payload.get('details')}", xbmc.LOGINFO)
                    self.client.set_activity(payload)
                    self.last_payload_str = current_payload_str

                if self.waitForAbort(10): break

            except DiscordConnectionError as e:
                 log(f"Connection error in loop: {e}", xbmc.LOGERROR)
                 self.last_payload_str = ""
                 if self.waitForAbort(15): break
            except Exception as e:
                log(f"Service error: {e}", xbmc.LOGERROR, exc_info=True)
                show_notification("Discord Presence", "Error in DiscordRPC loop.", xbmc.gui.NOTIFICATION_ERROR)
                if self.waitForAbort(15): break

        if self.client:
            self.client.disconnect()
        log("Service stopped.", xbmc.LOGINFO)


if __name__ == "__main__":
    log("Starting standalone service.", xbmc.LOGINFO)
    
    # artwork service url is now static
    if IMAGES_URL:
        log(f"Using artwork service URL: {IMAGES_URL}", xbmc.LOGINFO)
    else:
        log("Artwork service URL is not set.", xbmc.LOGWARNING)
        
    service = DiscordKDodiService()
    service.run_service()
import xbmc
import xbmcaddon
import time
import requests
from resources.lib.discord_gateway import DiscordClient

ADDON = xbmcaddon.Addon()
APP_ID = ADDON.getSettingString("app_id")
TOKEN = ADDON.getSettingString("user_token")
HA_URL = ADDON.getSettingString("ha_url").rstrip("/")
HA_TOKEN = ADDON.getSettingString("ha_token")
SENSOR_DETAIL = ADDON.getSettingString("sensor_detail")
SENSOR_STATE = ADDON.getSettingString("sensor_state")

HEADERS = {"Authorization": f"Bearer {HA_TOKEN}", "Content-Type": "application/json"}
UPDATE_INTERVAL = 15

def get_sensor_state(entity_id):
    try:
        url = f"{HA_URL}/api/states/{entity_id}"
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status() # Löst einen Fehler bei 4xx/5xx Status aus
        return response.json().get("state", "")
    except requests.exceptions.RequestException as e:
        xbmc.log(f"[DiscordRPC] Fehler beim Abrufen von {entity_id}: {e}", xbmc.LOGERROR)
    return ""

class DiscordHAService(xbmc.Monitor):
    def __init__(self):
        super(DiscordHAService, self).__init__()
        self.client = None

        if not all([APP_ID, TOKEN, HA_URL, HA_TOKEN, SENSOR_DETAIL, SENSOR_STATE]):
            xbmc.log("[DiscordRPC] Konfiguration unvollständig. Addon wird beendet.", xbmc.LOGERROR)
            return

        xbmc.log("[DiscordRPC] Starte Discord Client...", xbmc.LOGINFO)
        self.client = DiscordClient(APP_ID, TOKEN)
        self.client.connect()
        xbmc.log("[DiscordRPC] Service initialisiert.", xbmc.LOGINFO)

    def run(self):
        if not self.client:
            return

        last_details = ""
        last_state = ""
        is_playing_video = False

        while not self.abortRequested():
            new_is_playing_video = xbmc.Player().isPlayingVideo()

            if new_is_playing_video:
                if not is_playing_video:
                    xbmc.log("[DiscordRPC] Wiedergabe gestartet. Warte 3s auf Sensor-Update.", xbmc.LOGINFO)
                    if self.waitForAbort(3): break

                details = get_sensor_state(SENSOR_DETAIL)
                state = get_sensor_state(SENSOR_STATE)

                if details != last_details or state != last_state:
                    xbmc.log(f"[DiscordRPC] Update Presence: {details} | {state}", xbmc.LOGINFO)
                    payload = {
                        "name": "Kodi",
                        "type": 3,
                        "details": details,
                        "state": state,
                        "application_id": APP_ID,
                        "status_display_type": 2
                    }
                    self.client.set_activity(payload)
                    last_details = details
                    last_state = state

            elif is_playing_video and not new_is_playing_video:
                xbmc.log("[DiscordRPC] Wiedergabe beendet. Lösche Presence.", xbmc.LOGINFO)
                self.client.clear_activity()
                last_details = ""
                last_state = ""

            is_playing_video = new_is_playing_video

            if self.waitForAbort(UPDATE_INTERVAL):
                break

        if self.client:
            xbmc.log("[DiscordRPC] Beende Service und trenne Verbindung.", xbmc.LOGINFO)
            self.client.disconnect()
            xbmc.log("[DiscordRPC] Verbindung getrennt.", xbmc.LOGINFO)

if __name__ == "__main__":
    service = DiscordHAService()
    service.run()
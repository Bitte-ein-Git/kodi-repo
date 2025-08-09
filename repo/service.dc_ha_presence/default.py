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
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            return r.json().get("state", "")
    except Exception as e:
        xbmc.log(f"[DiscordRPC] Fehler beim Abrufen von {entity_id}: {e}", xbmc.LOG_ERROR)
    return ""

class DiscordHAService(xbmc.Monitor):
    def __init__(self):
        super().__init__()
        self.client = DiscordClient(APP_ID, TOKEN)
        self.client.connect()
        xbmc.log("[DiscordRPC] Service gestartet", xbmc.LOG_INFO)

    def run(self):
        while not self.abortRequested():
            if xbmc.Player().isPlayingVideo():
                xbmc.sleep(3000)  # 3 Sek Delay
                details = get_sensor_state(SENSOR_DETAIL)
                state = get_sensor_state(SENSOR_STATE)
                payload = {
                    "name": "Kodi",
                    "type": 3,
                    "details": details,
                    "state": state,
                    "application_id": APP_ID,
                    "status_display_type": 2
                }
                self.client.send_activity(payload)
            else:
                self.client.clear_activity()

            if self.waitForAbort(UPDATE_INTERVAL):
                break

        self.client.disconnect()

if __name__ == "__main__":
    service = DiscordHAService()
    service.run()
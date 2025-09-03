import xbmc
import xbmcaddon
import xbmcvfs
import os

# --- Addon Objects ---
addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
monitor = xbmc.Monitor()

# --- Helper Functions ---
def log(msg, level=xbmc.LOGINFO):
    xbmc.log(f"[{addon_name}] {msg}", level=level)

def get_current_profile():
    profile_path = xbmcvfs.translatePath('special://profile/addon_data/script.audio.profiles/profile')
    if os.path.exists(profile_path):
        try:
            with open(profile_path, 'r') as f:
                return int(f.read().strip())
        except (IOError, ValueError):
            return 0
    return 0

# --- Main Service ---
log("Service starting with seek method.")
stereo_profile_target = 2
multichannel_profile_target = 1

while not monitor.abortRequested():
    if xbmc.Player().isPlayingVideo():
        try:
            # Attempt to force a refresh with the seek method.
            xbmc.executeJSONRPC('{"jsonrpc":"2.0", "method":"Player.Seek", "params":{"playerid":1, "value":"smallforward"}, "id":1}')
            xbmc.sleep(100)
            
            channels_str = xbmc.getInfoLabel('Player.Process(audiochannels)')
            num_channels = len(channels_str.split(',')) if channels_str else 0
            
            current_active_profile = get_current_profile()
            
            if num_channels == 2 and current_active_profile != stereo_profile_target:
                log(f"ACTION: Stereo detected. Switching to profile {stereo_profile_target}.")
                xbmc.executebuiltin(f"RunScript(script.audio.profiles,{stereo_profile_target})")
            elif num_channels > 2 and current_active_profile != multichannel_profile_target:
                log(f"ACTION: Multichannel detected. Switching to profile {multichannel_profile_target}.")
                xbmc.executebuiltin(f"RunScript(script.audio.profiles,{multichannel_profile_target})")

        except Exception as e:
            log(f"An error occurred during check: {e}", level=xbmc.LOGERROR)

    if monitor.waitForAbort(2):
        break

log("Service stopped.")

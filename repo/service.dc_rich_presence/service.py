# -*- coding: utf-8 -*-
import sys
import os

# Add lib directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
lib_dir = os.path.join(script_dir, 'resources', 'lib')
sys.path.insert(0, lib_dir)

# Now import dependencies
try:
    import websocket
except ImportError:
    import xbmcgui
    xbmcgui.Dialog().ok("Service Error", "Required 'websocket-client' library not found.", "Please install it in resources/lib/", "See addon README.")
    sys.exit(1)

import xbmc
import xbmcaddon
import xbmcgui
from client import DiscordGatewayClient, log

class KodiPlayer(xbmc.Player):
    def __init__(self, gateway_client):
        self.gateway_client = gateway_client
        log("KodiPlayer initialized")

    def onPlayBackStarted(self):
        log("Playback Started", xbmc.LOGINFO)
        if self.isPlayingVideo():
            self.gateway_client.update_status(self, 'play')

    def onPlayBackPaused(self):
        log("Playback Paused", xbmc.LOGINFO)
        if self.isPlayingVideo():
            self.gateway_client.update_status(self, 'pause')

    def onPlayBackResumed(self):
        log("Playback Resumed", xbmc.LOGINFO)
        if self.isPlayingVideo():
            self.gateway_client.update_status(self, 'play')

    def onPlayBackStopped(self):
        log("Playback Stopped", xbmc.LOGINFO)
        self.gateway_client.update_status(self, 'stop')

    def onPlayBackEnded(self):
        log("Playback Ended", xbmc.LOGINFO)
        self.gateway_client.update_status(self, 'stop')

class ServiceMonitor(xbmc.Monitor):
    def __init__(self):
        self.gateway_client = None
        self.player_handler = None
        log("ServiceMonitor initialized")

    def start_service(self):
        token = xbmcaddon.Addon().getSetting('discord_token')
        if not token:
            log("Discord Token not set. Service will not start.", xbmc.LOGWARNING)
            xbmcgui.Dialog().notification("Discord Presence", "Discord Token not set. Addon disabled.", xbmcgui.NOTIFICATION_WARNING)
            return

        log("Starting Discord Gateway Client thread...", xbmc.LOGINFO)
        self.gateway_client = DiscordGatewayClient()
        self.gateway_client.daemon = True
        self.gateway_client.start()
        
        self.player_handler = KodiPlayer(self.gateway_client)
        log("Service started successfully.", xbmc.LOGINFO)

    def stop_service(self):
        if self.gateway_client:
            log("Stopping Discord Gateway Client...", xbmc.LOGINFO)
            self.gateway_client.stop()
            self.gateway_client = None
        
        # Player handler doesn't need explicit stop, remove reference
        self.player_handler = None
        log("Service stopped.", xbmc.LOGINFO)

    def onSettingsChanged(self):
        log("Settings changed. Restarting service...", xbmc.LOGINFO)
        self.stop_service()
        self.start_service()

    def onAbortRequested(self):
        log("Kodi abort requested.", xbmc.LOGINFO)
        self.stop_service()

if __name__ == '__main__':
    monitor = ServiceMonitor()
    monitor.start_service()
    
    # Keep the service alive
    while not monitor.abortRequested():
        if not monitor.gateway_client or not monitor.gateway_client.is_alive():
            if not monitor.abortRequested():
                log("Gateway client thread died. Attempting restart.", xbmc.LOGWARNING)
                monitor.stop_service()
                monitor.start_service()

        if monitor.waitForAbort(5):
            break

    # Final cleanup
    monitor.stop_service()
    log("Service shutting down.", xbmc.LOGINFO)
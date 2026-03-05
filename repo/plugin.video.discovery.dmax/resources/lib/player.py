# -*- coding: utf-8 -*-

from .common import *


class realvitoMonitor(xbmc.Monitor):
	def __init__(self, *args, **kwargs):
		super(realvitoMonitor, self).__init__()

class realvitoPlayer(xbmc.Player):
	def __init__(self, *args, **kwargs):
		super(realvitoPlayer, self).__init__()
		self.finished = False
		self.passage = 0
		self.current = 0
		self.complete = 999999
		debug_MS("(player.discoMaster[1]) -> [PLAYER]: >>> Neue Player Instanz wird erstellt >>>")

	def onAVStarted(self, only_once=3):
		if only_once == 1: # Kodi zwingen nur einmal diese Log-Meldung auszugeben
			only_once += 2
			debug_MS("▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼")
			debug_MS("(player.discoMaster[2]) -> [PLAYER]: >>> Wiedergabe-Monitor mit *5 Sekunden* Verzögerung gestartet >>>")

	def onPlayBackPaused(self):
		debug_MS("(player.discoMaster[00]) -> [PLAYER]: *** Die Wiedergabe wurde durch den Anwender pausiert ***")

	def onPlayBackEnded(self):
		debug_MS("(player.discoMaster[9]) -> [PLAYER]: @@@ Die Wiedergabe wurde regelkonform beendet @@@")
		self.onPlayBackStopped()

	def onPlayBackStopped(self):
		debug_MS("(player.discoMaster[9]) -> [PLAYER]: <<< Die Wiedergabe und der Wiedergabe-Monitor wurden gestoppt <<<")
		debug_MS("▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲")
		self.finished = True
		self.passage = 0
		self.current = 0
		self.complete = 999999
		xbmc.PlayList(1).clear()
		return

class discoMaster():
	def __init__(self, *args, **kwargs):
		self.monitor = realvitoMonitor()
		self.playback = realvitoPlayer()
		self.forcing = self.events_setter()
		self.firstrun = 1
		self.waiting = 2
		self.sizeing = 1
		self.placing = 1

	def events_setter(self):
		self.forcing = (True if addon.getSetting('force_stopping') == 'true' else False)
		return self.forcing

	def start_signal(self, LOADED):
		xbmcplugin.setResolvedUrl(ADDON_HANDLE, True, LOADED)
		time.sleep(5) # 5 Sekunden Verzögerung, sonst wird die Playerinstanz von Kodi nicht erkannt
		self.playback.onAVStarted(self.firstrun)
		if self.forcing is True:
			log("(player.discoMaster[3]) -> [PLAYER]: ••• Der forcierte Player-Stopp wurde vom Anwender aktiviert •••")
			self.start_check()
		else:
			log("(player.discoMaster[3]) -> [PLAYER]: <<< Der forcierte Player-Stopp ist zur Zeit deaktiviert <<<")
			debug_MS("▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲")

	def start_check(self):
		while not self.monitor.abortRequested() and not self.playback.finished:
			self.forcing = self.events_setter()
			if self.forcing is True and xbmc.getCondVisibility('Player.HasVideo') and self.playback.isPlayingVideo(): # *isPlayingVideo* trifft immer zu solange das Video nicht beendet wurde
				if not xbmc.getCondVisibility('Player.Seeking') and xbmc.getCondVisibility('Player.Playing'): # Nur wenn das Video läuft weiter zählen (ausgeschlossen sind: FastForward, FastRewind, Pause)
					self.playback.passage += 1
					self.playback.current = self.playback.getTime()
				if self.playback.complete == 999999:
					self.playback.complete = self.playback.getTotalTime()
					begins_running = f"{convert_times(self.playback.complete, False, 0)}.000" if KODI_un21 else convert_times(self.playback.complete)
					debug_MS(f"(player.discoMaster[4]) -> [PLAYER]: STARTING === COURSE_no : {self.playback.passage} === TOTAL_TIME : {begins_running} -> Modus gesamte Videolaufzeit abrufen ===")
				if self.playback.current != 0 and self.playback.complete != 999999:
					if xbmc.getCondVisibility('Player.Seeking') or not xbmc.getCondVisibility('Player.Playing'): # Wenn das Video durch eine Anwenderaktion unterbrochen wird, die nächsten Schritte überspringen
						continue
					if int(round(self.playback.current*1000)) + 150000 < int(round(self.playback.complete*1000)): # bis maximal 2 min. 30 sek.vor Laufzeitende
						debug_MS(f"(player.discoMaster[5]) -> [PLAYER]: WAITING === COURSE_no : {self.playback.passage} === ACTUAL_TIME : {convert_times(self.playback.current)} -> Modus lange Wartezeit *90 Sekunden* ===")
						self.waiting = 90 # 90 sek.
					elif int(round(self.playback.current*1000)) + 15000 < int(round(self.playback.complete*1000)): # bis maximal 15 sek.vor Laufzeitende
						debug_MS(f"(player.discoMaster[6]) -> [PLAYER]: SLEEPING === COURSE_no : {self.playback.passage} === ACTUAL_TIME : {convert_times(self.playback.current)} -> Modus kurze Wartezeit *2 Sekunden* ===")
						self.waiting = 2 # 2 sek.
					else: # ab 15 sek. Restlaufzeit
						debug_MS(f"(player.discoMaster[7]) -> [PLAYER]: SHORTING === COURSE_no : {self.playback.passage} === ACTUAL_TIME : {convert_times(self.playback.current)} -> Modus schnelle Wartezeit *1 Sekunde* ===")
						self.track_quick(self.playback, self.playback.finished, self.playback.current, self.playback.complete)
						self.waiting = 1 # 1 sek.
				else:
					failing("(player.discoMaster[5]) -> [PLAYER]: ERROR - TIME - ERROR XXXXX FAILURE : Die Laufzeitangaben des Videos sind fehlerhaft !!! XXXXX")
					self.playback.finished = True
			else:
				failing("(player.discoMaster[4]) -> [PLAYER]: ERROR - INTERRUPT - ERROR XXXXX FAILURE : Der forcierte Player-Stopp wurde vom Anwender deaktiviert oder es läuft zur Zeit kein Video !!! XXXXX")
				self.playback.finished = True
			if self.monitor.waitForAbort(self.waiting):
				break

	def track_quick(self, INSTANCE, FINISH, ACTUAL, TOTAL):
		actual_running = int(round(ACTUAL*1000)) + 500 if KODI_un21 else int(ACTUAL*1000) + 500
		if not FINISH and actual_running >= int(TOTAL)*1000: # Plus 500 msek. da die Gesamtlaufzeit in KODI 19+20 keine Millisekunden hat // ab KODI 21 mit Millisekunden
			ending_running = f"{convert_times(TOTAL, False, 0)}.000" if KODI_un21 else convert_times(TOTAL)
			log(f"(player.discoMaster[8]) -> [PLAYER]: FORCE_STOPPING === ACTUAL_TIME : {convert_times(ACTUAL)} || TOTAL_TIME : {ending_running} ===")
			self.playback.finished = True
			try:
				self.sizeing = xbmc.PlayList(1).size()
				self.placing = xbmc.PlayList(1).getposition()+1
			except: pass
			if isinstance(self.sizeing, int) and isinstance(self.placing, int) and self.sizeing > 1 and self.sizeing > self.placing:
				debug_MS(f"(player.discoMaster[8]) -> [PLAYER]: NEXT_PLAYING *** Anforderung nächstes Video der Playliste: No.{self.placing+1} von insgesamt No.{self.sizeing} ***")
				xbmc.executebuiltin('PlayerControl(Next)')
			else:
				debug_MS(f"(player.discoMaster[8]) -> [PLAYER]: STOP_PLAYING ♦♦♦ Es existiert keine Playliste oder das Ende der Playliste wurde erreicht ♦♦♦")
				xbmc.executebuiltin('PlayerControl(Stop)')
		else: pass

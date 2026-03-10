

#2021-07-14
# edit 2025-06-12

import sys
from os import path
import xbmcvfs, xbmc
from resources.lib import control
from resources.lib.tools import cParser

sysaddon = sys.argv[0]
syshandle = int(sys.argv[1]) if len(sys.argv) > 1 else ''
artPath = control.artPath()
addonFanart = control.addonFanart()
addonPath = control.addonPath

# TODO https://kodi.wiki/view/Default_Icons
class navigator:
	def root(self):
		self.addDirectoryItem("Suche Filme", 'moviesSearch', '_movies-search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem("Suche TV-Serien", 'tvshowsSearch', '_series-search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem("Darsteller - Suche nach Person", 'personSearch', '_people-search.png', 'DefaultAddonsSearch.png')
		self.addDirectoryItem("Filme", 'movieNavigator', 'movies.png', 'DefaultMovies.png')
		self.addDirectoryItem("TV-Serien", 'tvNavigator', 'tvshows.png', 'DefaultTVShows.png')
		downloads = True if control.getSetting('downloads') == 'true' and (
				len(control.listDir(control.getSetting('download.movie.path'))[0]) > 0 or len(
			control.listDir(control.getSetting('download.tv.path'))[0]) > 0) else False
		if downloads:
			self.addDirectoryItem("Downloads", 'downloadNavigator', 'downloads.png', 'DefaultFolder.png')
		self.addDirectoryItem("Werkzeuge", 'toolNavigator', 'tools.png', 'DefaultAddonProgram.png')
		if xbmc.getCondVisibility('system.platform.windows'): self.addDirectoryItem("Stream-URL abspielen", 'playURL', 'url.png', 'DefaultAddonWebSkin.png', isFolder=False)
		self._endDirectory(content='',cache=False)  # addons  videos  files

# TODO vote_count vote_average popularity revenue
	def movies(self):
		self.addDirectoryItem("[B]Filme[/B] - Neu", 'listings&media_type=movie&url=kino', 'in-theaters.png', 'DefaultRecentlyAddedMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Jahr", 'movieYears', 'years.png', 'DefaultMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Genres", 'movieGenres', 'genres.png', 'DefaultMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Am populärsten", 'listings&media_type=movie&url=production_status=released%26sort_by=popularity.desc', 'most-popular.png', 'DefaultMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Am besten bewertet", 'listings&media_type=movie&url=production_status=released%26sort_by=vote_average.desc', 'highly-rated.png', 'DefaultMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Meist bewertet", 'listings&media_type=movie&url=production_status=released%26sort_by=vote_count.desc', 'most-voted.png', 'DefaultMovies.png')
		self.addDirectoryItem("[B]Filme[/B] - Bestes Einspielergebnis", 'listings&media_type=movie&url=production_status=released%26sort_by=revenue.desc', 'box-office.png', 'DefaultMovies.png')
		# self.addDirectoryItem("[B]Filme[/B] - Oskar-Gewinner", 'movies&url=oscars', 'oscar-winners.png', 'DefaultMovies.png')
		self._endDirectory()

	def tvshows(self):
		self.addDirectoryItem("[B]Serien[/B] - Genres", 'tvGenres', 'genres.png', 'DefaultTVShows.png')
		self.addDirectoryItem("[B]Serien[/B] - Am populärsten", 'listings&media_type=tv&url=sort_by=popularity.desc', 'most-popular.png', 'DefaultTVShows.png')
		self.addDirectoryItem("[B]Serien[/B] - Am besten bewertet", 'listings&media_type=tv&url=sort_by=vote_average.desc', 'highly-rated.png', 'DefaultTVShows.png')
		self.addDirectoryItem("[B]Serien[/B] - Meist bewertet", 'listings&media_type=tv&url=sort_by=vote_count.desc', 'most-voted.png', 'DefaultTVShows.png')
		# self.addDirectoryItem("[B]Serien[/B] - Suche nach Darstellern/Crew", 'tvPerson', 'people-search.png', 'DefaultTVShows.png', isFolder=False)
		self._endDirectory()

	def tools(self):
		self.addDirectoryItem("[B]Support[/B]: Information anzeigen", 'pluginInfo', 'plugin-info.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem(control.addonName +": EINSTELLUNGEN", 'addonSettings', 'tools.png', 'DefaultAddonProgram.png', isFolder=False)
		# self.addDirectoryItem("[B]"+control.addonName.upper()+"[/B]: Reset Settings (außer Konten)", 'resetSettings', 'nightly_update.png', 'DefaultAddonProgram.png', isFolder=False)
		self.addDirectoryItem("[B]Resolver[/B]: EINSTELLUNGEN", 'resolverSettings', 'resolveurl.png', 'DefaultAddonProgram.png', isFolder=False)
		self._endDirectory()	# addons  videos  files

	def downloads(self):
		movie_downloads = control.getSetting('download.movie.path')
		tv_downloads = control.getSetting('download.tv.path')
		if len(control.listDir(movie_downloads)[0]) > 0:
			self.addDirectoryItem("Filme", movie_downloads, 'movies.png', 'DefaultMovies.png', isAction=False)
		if len(control.listDir(tv_downloads)[0]) > 0:
			self.addDirectoryItem("TV-Serien", tv_downloads, 'tvshows.png', 'DefaultTVShows.png', isAction=False)
		self._endDirectory()

#TODO
	def addDirectoryItem(self, name, query, thumb, icon, context=None, queue=False, isAction=True, isFolder=True):
		url = '%s?action=%s' % (sysaddon, query) if isAction == True else query
		thumb = self.getMedia(thumb, icon)
		#laut kodi doku - ListItem([label, label2, path, offscreen])
		listitem = control.item(name, offscreen=True) # Removed iconImage and thumbnailImage
		listitem.setArt({'poster': thumb, 'icon': icon})
		if not context == None:
			cm = []
			cm.append((context[0], 'RunPlugin(%s?action=%s)' % (sysaddon, context[1])))
			listitem.addContextMenuItems(cm)

		isMatch, sPlot = cParser.parseSingleResult(query, "plot'.*?'([^']+)")
		if not isMatch: sPlot = '[COLOR blue]{0}[/COLOR]'.format(name)
		if isFolder:
			listitem.setInfo('video', {'overlay': 4, 'plot': control.unquote_plus(sPlot)})
			listitem.setIsFolder(True)
		else:
			listitem.setProperty('IsPlayable', 'false')
		self.addFanart(listitem, query)
		control.addItem(syshandle, url, listitem, isFolder)

	def _endDirectory(self, content='', cache=True ): # addons  videos  files
		# https://romanvm.github.io/Kodistubs/_autosummary/xbmcplugin.html#xbmcplugin.setContent
		control.content(syshandle, content)
		control.plugincategory(syshandle, control.addonName + ' / '+ control.addonVersion)
		control.endofdirectory(syshandle, succeeded=True, cacheToDisc=cache)

# ------- ergänzt für xStream V2 -----------
	def addFanart(self, listitem, query):
		if control.getSetting('fanart')=='true':
			isMatch, sFanart = cParser.parseSingleResult(query, "fanart'.*?'([^']+)")
			if isMatch:
				sFanart = self.getMedia(sFanart)
				listitem.setProperty('fanart_image', sFanart)
			else:
				listitem.setProperty('fanart_image', addonFanart)

	def getMedia(self,mediaFile=None, icon=None):
		if xbmcvfs.exists(path.join(artPath, mediaFile)): mediaFile = path.join(artPath, mediaFile)
		elif xbmcvfs.exists(path.join(artPath, 'sites', mediaFile)): mediaFile = path.join(artPath, 'sites', mediaFile)
		elif mediaFile.startswith('http'): return mediaFile
		else: mediaFile = icon
		return mediaFile
	


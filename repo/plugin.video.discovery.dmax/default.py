# -*- coding: utf-8 -*-

'''
    Copyright (C) 2026 realvito

    DMAX Mediathek

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.
'''

from resources.lib.common import *
from resources.lib import navigator
params = dict(parse_qsl(sys.argv[2][1:]))


def run():
	if params:
		if params['mode'] == 'listThemes':
			navigator.listThemes()
		elif params['mode'] == 'listAlphabet':
			navigator.listAlphabet()
		elif params['mode'] == 'listSeries':
			navigator.listSeries(params['url'], params.get('page', '1'), params.get('marker', 'standard'), params.get('transmit', ''))
		elif params['mode'] == 'listEpisodes':
			navigator.listEpisodes(params['url'], params.get('genre', ''), params.get('name', ''))
		elif params['mode'] == 'playVideo':
			navigator.playVideo(params['url'])
		elif params['mode'] == 'listFavorites':
			navigator.listFavorites()
		elif params['mode'] == 'favorit_construct':
			navigator.favorit_construct(**params)
		elif params['mode'] == 'aConfigs':
			addon.openSettings()
			xbmc.executebuiltin('Container.Refresh')
		elif params['mode'] == 'iConfigs':
			xbmcaddon.Addon('inputstream.adaptive').openSettings()
	else: ##### Delete old Files in Userdata-Folder 'settings' to cleanup old Entries #####
		DONE = False ##### [plugin.video.discovery.dmax v.3.0.9+v.3.1.0+v.3.2.8] - 22.03.2021+11.04.2021+21.07.2024 #####
		firstSCRIPT = xbmcvfs.translatePath(os.path.join(f"special://home{os.sep}addons{os.sep}{addon_id}{os.sep}lib{os.sep}")).encode('utf-8').decode('utf-8')
		UNO = xbmcvfs.translatePath(os.path.join(firstSCRIPT, 'only_at_FIRSTSTART'))
		if xbmcvfs.exists(UNO):
			SOURCE = xbmcvfs.translatePath(os.path.join(f"special://home{os.sep}userdata{os.sep}addon_data{os.sep}{addon_id}{os.sep}")).encode('utf-8').decode('utf-8')
			if xbmcvfs.exists(SOURCE):
				OLD_SETTINGS = xbmcvfs.translatePath(os.path.join(SOURCE, 'settings.xml'))
				try:
					xbmc.executeJSONRPC(f'{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{addon_id}","enabled":false}}}}')
					if xbmcvfs.exists(OLD_SETTINGS):
						xbmcvfs.delete(OLD_SETTINGS) # Delete OLD_SETTINGS File
				except: pass
				xbmcvfs.delete(UNO)
				xbmc.executeJSONRPC(f'{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{addon_id}","enabled":true}}}}')
				xbmc.sleep(500)
				DONE = True
			else:
				xbmcvfs.delete(UNO)
				xbmc.sleep(500)
				DONE = True
		else:
			DONE = True
		if DONE is True:
			if not xbmcvfs.exists(os.path.join(dataPath, 'settings.xml')):
				xbmcvfs.mkdirs(dataPath)
				xbmc.executebuiltin(f"Addon.OpenSettings({addon_id})")
			navigator.mainMenu()

run()

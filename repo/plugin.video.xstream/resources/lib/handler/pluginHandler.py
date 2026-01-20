# -*- coding: utf-8 -*-
# Python 3

import json
import os
import sys
import xbmc
import concurrent.futures

from resources.lib.config import cConfig
from xbmc import LOGINFO as LOGNOTICE, LOGERROR, log
from resources.lib import utils
from resources.lib.handler.requestHandler import cRequestHandler
from urllib.parse import urlparse
from xbmcgui import Dialog
from xbmcvfs import translatePath
from resources.lib.tools import platform, infoDialog, getDNS, getRepofromAddonsDB


ADDON_PATH = translatePath(os.path.join('special://home/addons/', '%s'))

class cPluginHandler:
    def __init__(self):
        self.rootFolder = translatePath(cConfig().getAddonInfo('path'))
        self.settingsFile = os.path.join(self.rootFolder, 'resources', 'settings.xml')
        self.profilePath = translatePath(cConfig().getAddonInfo('profile'))
        self.pluginDBFile = os.path.join(self.profilePath, 'pluginDB')

        log(cConfig().getLocalizedString(30166) + ' -> [pluginHandler]: profile folder: %s' % self.profilePath, LOGNOTICE)
        log(cConfig().getLocalizedString(30166) + ' -> [pluginHandler]: root folder: %s' % self.rootFolder, LOGNOTICE)
        self.defaultFolder = os.path.join(self.rootFolder, 'sites')
        log(cConfig().getLocalizedString(30166) + ' -> [pluginHandler]: default sites folder: %s' % self.defaultFolder, LOGNOTICE)

    def getAvailablePlugins(self):
        global globalSearchStatus
        pluginDB = self.__getPluginDB()
        update = False
        fileNames = self.__getFileNamesFromFolder(self.defaultFolder)

        for fileName in fileNames:
            plugin = {'name': '', 'identifier': '', 'icon': '', 'domain': '', 'globalsearch': '', 'modified': 0}
            if fileName in pluginDB:
                plugin.update(pluginDB[fileName])

            try:
                modTime = os.path.getmtime(os.path.join(self.defaultFolder, fileName + '.py'))
            except OSError:
                modTime = 0

            try:
                globalSearchStatus = cConfig().getSetting('global_search_' + fileName)
            except Exception:
                pass

            if fileName not in pluginDB or modTime > plugin['modified'] or globalSearchStatus:
                pluginData = self.__getPluginData(fileName, self.defaultFolder)
                if pluginData:
                    pluginData['globalsearch'] = globalSearchStatus
                    pluginData['modified'] = modTime
                    pluginDB[fileName] = pluginData
                    update = True

        deletions = []
        for pluginID in pluginDB:
            if pluginID not in fileNames:
                deletions.append(pluginID)

        for pid in deletions:
            del pluginDB[pid]

        if update or deletions:
            self.__updatePluginDB(pluginDB)

        return self.getAvailablePluginsFromDB()

    def getAvailablePluginsFromDB(self):
        plugins = []
        iconFolder = os.path.join(self.rootFolder, 'resources', 'art', 'sites')
        pluginDB = self.__getPluginDB()

        for pluginID in pluginDB:
            plugin = pluginDB[pluginID]
            plugin['id'] = pluginID
            plugin['icon'] = os.path.join(iconFolder, plugin.get('icon', ''))

            if cConfig().getSetting('plugin_%s' % pluginID) == 'true':
                plugins.append(plugin)

        return plugins

    def __updatePluginDB(self, data):
        if not os.path.exists(self.profilePath):
            os.makedirs(self.profilePath)
        with open(self.pluginDBFile, 'w') as f:
            json.dump(data, f)

    def __getPluginDB(self):
        if not os.path.exists(self.pluginDBFile):
            return dict()
        try:
            with open(self.pluginDBFile, 'r') as f:
                return json.load(f)
        except Exception:
            return dict()

    def __getFileNamesFromFolder(self, sFolder):
        return [os.path.basename(f[:-3]) for f in os.listdir(sFolder) if f.endswith('.py')]

    def __getPluginData(self, fileName, defaultFolder):
        pluginData = {}
        if defaultFolder not in sys.path:
            sys.path.append(defaultFolder)
        try:
            plugin = __import__(fileName, globals(), locals())
            pluginData['name'] = plugin.SITE_NAME
            pluginData['identifier'] = getattr(plugin, 'SITE_IDENTIFIER', '')
            pluginData['icon'] = getattr(plugin, 'SITE_ICON', '')
            pluginData['domain'] = getattr(plugin, 'DOMAIN', '')
            pluginData['globalsearch'] = getattr(plugin, 'SITE_GLOBAL_SEARCH', True)
            return pluginData
        except Exception:
            return False

    def __getPluginDataDomain(self, fileName, defaultFolder):
        if defaultFolder not in sys.path:
            sys.path.append(defaultFolder)
        plugin = __import__(fileName, globals(), locals())
        return {
            'identifier': plugin.SITE_IDENTIFIER,
            'domain': getattr(plugin, 'DOMAIN', '')
        }

    def checkDomain(self):
        log(cConfig().getLocalizedString(30166) + ' -> [checkDomain]: Query status code of the provider', LOGNOTICE)
        fileNames = self.__getFileNamesFromFolder(self.defaultFolder)

        tasks = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for fileName in fileNames:
                try:
                    pluginDataDomain = self.__getPluginDataDomain(fileName, self.defaultFolder)
                    provider = pluginDataDomain['identifier']

                    if provider == 'api_all':
                        continue

                    domain = cConfig().getSetting(
                        'plugin_' + provider + '.domain',
                        pluginDataDomain['domain']
                    )
                    base_link = 'http://' + domain + '/'

                    wrongDomain = ('site-maps.cc', 'www.drei.at', 'notice.cuii.info')
                    if domain in wrongDomain:
                        cConfig().setSetting('plugin_' + provider + '.domain', '')
                        cConfig().setSetting('plugin_' + provider + '_status', '')
                        continue

                    if cConfig().getSetting('plugin_' + provider) == 'false':
                        cConfig().setSetting('global_search_' + provider, 'false')
                        cConfig().setSetting('plugin_' + provider + '_checkdomain', 'false')
                        cConfig().setSetting('plugin_' + provider + '.domain', '')
                        cConfig().setSetting('plugin_' + provider + '_status', '')
                        continue

                    if cConfig().getSetting('plugin_' + provider + '_checkdomain') == 'true':
                        tasks.append(
                            executor.submit(self._checkdomain, provider, base_link)
                        )

                except Exception:
                    pass

            for future in concurrent.futures.as_completed(tasks):
                try:
                    future.result()
                except Exception:
                    pass

        log(cConfig().getLocalizedString(30166) + ' -> [checkDomain]: Domains for all available Plugins updated', LOGNOTICE)
        #infoDialog("Domain-Überprüfung aller Plugins abgeschlossen", sound=False, icon='INFO', time=6000)

    def _checkdomain(self, provider, base_link):
        try:
            oRequest = cRequestHandler(base_link, caching=False, ignoreErrors=True)
            oRequest.request()
            status_code = int(oRequest.getStatus())

            cConfig().setSetting('plugin_' + provider + '_status', str(status_code))

            if 403 <= status_code <= 503:
                cConfig().setSetting('global_search_' + provider, 'false')

            elif 300 <= status_code <= 400:
                url = oRequest.getRealUrl()
                cConfig().setSetting('plugin_' + provider + '.domain', urlparse(url).hostname)
                cConfig().setSetting('global_search_' + provider, 'true')

            elif status_code == 200:
                cConfig().setSetting('plugin_' + provider + '.domain', urlparse(base_link).hostname)
                cConfig().setSetting('global_search_' + provider, 'true')

            else:
                cConfig().setSetting('global_search_' + provider, 'false')
                cConfig().setSetting('plugin_' + provider + '.domain', '')

        except Exception:
            cConfig().setSetting('global_search_' + provider, 'false')
            cConfig().setSetting('plugin_' + provider + '.domain', '')

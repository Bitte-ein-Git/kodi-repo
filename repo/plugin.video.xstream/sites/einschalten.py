# -*- coding: utf-8 -*-
# Python 3


# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showEntries:    6 Stunden
# showEpisodes:   4 Stunden

from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'einschalten'
SITE_NAME = 'Einschalten'
SITE_ICON = 'einschalten.png'

# Global search function is thus deactivated!
if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'false':
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'einschalten.in') # Domain Auswahl über die xStream Einstellungen möglich
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status') # Status Code Abfrage der Domain
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER) # Ob Plugin aktiviert ist oder nicht

URL_MAIN = 'https://' + DOMAIN
URL_NEW_MOVIES = URL_MAIN + '/movies/new'
URL_LAST_MOVIES = URL_MAIN + '/movies/recently-added'
URL_COLLECTIONS = URL_MAIN + '/collections'
URL_SEARCH = URL_MAIN + '/search?query=%s'
URL_THUMBNAIL = URL_MAIN + '/api/image/poster'


def load(): # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_NEW_MOVIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30541), SITE_IDENTIFIER, 'showEntries'), params)  # New Movies
    params.setParam('sUrl', URL_LAST_MOVIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30549), SITE_IDENTIFIER, 'showEntriesLast'), params)  # Recently added movies
    params.setParam('sUrl', URL_COLLECTIONS)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30543), SITE_IDENTIFIER, 'showCollections'), params)  # Collections
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'), params)   # Search
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    iPage = int(params.getValue('page'))
    
    # Check if URL already has parameters to decide between ? and &
    separator = '&' if '?' in entryUrl else '?'
    sUrl = entryUrl + separator + 'page=' + str(iPage) if iPage > 0 else entryUrl
    
    oRequest = cRequestHandler(sUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    pattern = '{"id":([^,"]+).*?title":"([^"]+).*?Date":"([^-]+).*?"posterPath":"([^"]+).*?collectionId":([^}]+)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sName, sYear, sThumbnail, sDummy in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setYear(sYear)
        oGuiElement.setThumbnail(URL_THUMBNAIL + sThumbnail)
        oGuiElement.setMediaType('movie')
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)
    if not sGui and not sSearchText:
        sPageNr = int(params.getValue('page'))
        if sPageNr == 0:
            sPageNr = 2
        else:
            sPageNr += 1
        params.setParam('page', int(sPageNr))
        params.setParam('sUrl', entryUrl)
        oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showCollections(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    iPage = int(params.getValue('page'))
    
    separator = '&' if '?' in entryUrl else '?'
    sUrl = entryUrl + separator + 'page=' + str(iPage) if iPage > 0 else entryUrl
    
    oRequest = cRequestHandler(sUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    pattern = '{"id":([^,"]+).*?name":"([^"]+).*?"posterPath":"([^"]+)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sName, sThumbnail in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER,'showCollectionEntries')
        oGuiElement.setThumbnail(URL_THUMBNAIL + sThumbnail)
        oGuiElement.setMediaType('movie')
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, total)
    if not sGui and not sSearchText:
        sPageNr = int(params.getValue('page'))
        if sPageNr == 0:
            sPageNr = 2
        else:
            sPageNr += 1
        params.setParam('page', int(sPageNr))
        params.setParam('sUrl', entryUrl)
        oGui.addNextPage(SITE_IDENTIFIER, 'showCollections', params)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showCollectionEntries(sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    entryUrl = URL_COLLECTIONS + '/' + params.getValue('entryUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    sHtmlContent = oRequest.request()
    pattern = '{"id":([^,"]+).*?title":"([^"]+).*?Date":"([^-]+).*?"posterPath":"([^"]+).*?collectionId":([^}]+)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return
    total = len(aResult)
    for sUrl, sName, sYear, sThumbnail, sDummy in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setYear(sYear)
        oGuiElement.setThumbnail(URL_THUMBNAIL + sThumbnail)
        oGuiElement.setMediaType('movie')
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)
    if not sGui and not sSearchText:
        params.setParam('sUrl', entryUrl)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showEntriesLast(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    iPage = int(params.getValue('page'))
    
    separator = '&' if '?' in entryUrl else '?'
    sUrl = entryUrl + separator + 'page=' + str(iPage) if iPage > 0 else entryUrl
    
    oRequest = cRequestHandler(sUrl, ignoreErrors=(sGui is not False))
    sHtmlContent = oRequest.request()
    pattern = '{"id":([^,"]+).*?title":"([^"]+).*?Date":"([^-]+).*?"posterPath":"([^"]+).*?collectionId":([^}]+)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sName, sYear, sThumbnail, sDummy in aResult:
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setYear(sYear)
        oGuiElement.setThumbnail(URL_THUMBNAIL + sThumbnail)
        oGuiElement.setMediaType('movie')
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('entryUrl', sUrl)
        oGui.addFolder(oGuiElement, params, False, total)
    if not sGui and not sSearchText:
        sPageNr = int(params.getValue('page'))
        if sPageNr == 0:
            sPageNr = 2
        else:
            sPageNr += 1
        params.setParam('page', int(sPageNr))
        params.setParam('sUrl', entryUrl)
        oGui.addNextPage(SITE_IDENTIFIER, 'showEntriesLast', params)
        oGui.setView('movies')
        oGui.setEndOfDirectory()


def showHosters():
    params = ParameterHandler()
    entryUrl = params.getValue('entryUrl')
    hosters = []
    sUrl = URL_MAIN + '/api/movies/' + entryUrl + '/watch'
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    pattern = 'streamUrl":"([^"]+)'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch: return
    sQuality = '720'
    for sUrl in aResult:
        sName = cParser.urlparse(sUrl)
        if cConfig().isBlockedHoster(sName)[0]: continue # Hoster aus settings.xml oder deaktivierten Resolver ausschließen
        hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I][%sp][/I]' % (sName, sQuality), 'quality': sQuality}
        hosters.append(hoster)
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def getHosterUrl(sUrl=False):
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30287))
    if not sSearchText: return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)

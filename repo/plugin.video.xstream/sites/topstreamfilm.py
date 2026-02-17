# -*- coding: utf-8 -*-
# Python 3

# Always pay attention to the translations in the menu!
# HTML LangzeitCache hinzugefügt
# showValue:     48 Stunden
# showEntries:    6 Stunden
# showEpisodes:   4 Stunden
    
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui

SITE_IDENTIFIER = 'topstreamfilm'
SITE_NAME = 'Topstreamfilm'
SITE_ICON = 'topstreamfilm.png'

# Global search function is thus deactivated!
if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'false':
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'topstreamfilm.live') # Domain Auswahl über die xStream Einstellungen möglich
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status') # Status Code Abfrage der Domain
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER) # Ob Plugin aktiviert ist oder nicht

URL_MAIN = 'https://' + DOMAIN
# URL_MAIN = 'https://www.topstreamfilm.live'

URL_ALL = URL_MAIN + '/filme-online-sehen/'
URL_MOVIES = URL_MAIN + '/beliebte-filme-online/'
URL_KINO = URL_MAIN + '/kinofilme/'
URL_SERIES = URL_MAIN + '/serien/'
URL_SEARCH = URL_MAIN + '/?story=%s&do=search&subaction=search'

#

def load(): # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_ALL)
    cGui().addFolder(cGuiElement('Alle Filme', SITE_IDENTIFIER, 'showEntries'), params)
    params.setParam('sUrl', URL_MOVIES)
    cGui().addFolder(cGuiElement('Kürzlich hinzugefügt', SITE_IDENTIFIER, 'showEntries'), params)  # Neue Uploads
    params.setParam('sUrl', URL_KINO)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30501), SITE_IDENTIFIER, 'showEntries'), params)  # Kinofilme
    params.setParam('Value', 'KATEGORIEN')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showValue'), params)    # Genre
    params.setParam('Value', 'LAND')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30538), SITE_IDENTIFIER, 'showValue'), params)  # Country
    cGui().addFolder(cGuiElement('Jahr', SITE_IDENTIFIER, 'showYearSearch'))  # New Year entry
    params.setParam('sUrl', URL_SERIES)
    cGui().addFolder(cGuiElement('Serien', SITE_IDENTIFIER, 'showEntries'), params)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'), params)   # Search
    cGui().setEndOfDirectory()


def showValue():
    params = ParameterHandler()
    oRequest = cRequestHandler(URL_MAIN)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 48  # 48 Stunden
    sHtmlContent = oRequest.request()
    pattern = '>{0}</a>(.*?)</ul>'.format(params.getValue('Value'))
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if not isMatch:
        pattern = '>{0}</(.*?)</ul>'.format(params.getValue('Value'))
        isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        isMatch, aResult = cParser.parse(sHtmlContainer, 'href="([^"]+).*?>([^<]+)')
    if not isMatch:
        cGui().showInfo()
        return

    for sUrl, sName in aResult:
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl
        params.setParam('sUrl', sUrl)
        cGui().addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False, sSearchPageText = False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    isTvshow = False
    if not entryUrl: entryUrl = params.getValue('sUrl')
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False))
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    sHtmlContent = oRequest.request()
    pattern = 'TPostMv">.*?href="([^"]+).*?data-src="([^"]+).*?Title">([^<]+)(.*?)</li>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    for sUrl, sThumbnail, sName, sDummy in aResult:
        if sName:
            sName = sName.split('- Der Film')[0].strip() # Name nach dem - abschneiden und Array [0] nutzen
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        isYear, sYear = cParser.parseSingleResult(sDummy, r'Year">([\d]+)</span>')  # Release Jahr
        isDuration, sDuration = cParser.parseSingleResult(sDummy, r'time">([\d]+)')  # Laufzeit
        if int(sDuration) <= int('70'): # Wenn Laufzeit kleiner oder gleich 70min, dann ist es eine Serie.
            isTvshow = True
        else:
            from resources.lib.tmdb import cTMDB
            oMetaget = cTMDB()
            if not oMetaget:
                isTvshow = False
            else:
                if isYear:
                    meta = oMetaget.search_movie_name(sName, year=sYear)
                else:
                    meta = oMetaget.search_movie_name(sName)
                if meta and 'id' in meta:
                    isTvshow = False
                else:
                    isTvshow = True
        if 'South Park: The End Of Obesity' in sName:
            isTvshow = False
        isQuality, sQuality = cParser.parseSingleResult(sDummy, 'Qlty">([^<]+)</span>')  # Qualität
        isDesc, sDesc = cParser.parseSingleResult(sDummy, 'Description"><p>([^<]+)')  # Beschreibung
        sThumbnail = URL_MAIN + sThumbnail
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showSeasons' if isTvshow else 'showHosters')
        if isYear:
            oGuiElement.setYear(sYear)
        if isDuration:
            oGuiElement.addItemValue('duration', sDuration)
        if isQuality:
            oGuiElement.setQuality(sQuality)
        if isDesc:
            oGuiElement.setDescription(sDesc)
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        oGuiElement.setThumbnail(sThumbnail)
        params.setParam('entryUrl', sUrl)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('sDesc', sDesc)
        oGui.addFolder(oGuiElement, params, isTvshow, total)
    if not sGui and not sSearchText and not sSearchPageText:
        isMatchNextPage, sNextUrl = cParser.parseSingleResult(sHtmlContent, 'href="([^"]+)">Next')

        # Start Page Function
        isMatchSiteSearch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, 'class="wp-pagenavi">(.*?)Next')
        if isMatchSiteSearch:
            isMatch, aResult = cParser.parse(sHtmlContainer, r'<span>([\d]+)</span>.*?nav_ext">.*?">([\d]+)</a>.*?href="([^"]+)')
            for sPageActive, sPageLast, sNextPage in aResult:
                #sPageName = '[I]Seitensuche starten  >>> [/I] Seite ' + str(sPageActive) + ' von ' + str(sPageLast) + ' Seiten  [I]<<<[/I]'
                sPageName = cConfig().getLocalizedString(30284) + str(sPageActive) + cConfig().getLocalizedString(30285) + str(sPageLast) + cConfig().getLocalizedString(30286)
                params.setParam('sNextPage', sNextPage)
                params.setParam('sPageLast', sPageLast)
                oGui.searchNextPage(sPageName, SITE_IDENTIFIER, 'showSearchPage', params)
        # End Page Function

        if isMatchNextPage:
            params.setParam('sUrl', sNextUrl)
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows' if isTvshow else 'movies')
        oGui.setEndOfDirectory()


def showSeasons():
    params = ParameterHandler()
    # Parameter laden
    sUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue('sThumbnail')
    isDesc = params.getValue('sDesc')
    oRequest = cRequestHandler(sUrl)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # HTML Cache Zeit 6 Stunden
    sHtmlContent = oRequest.request()
    pattern = '<div class="tt_season">(.*)</ul>'
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        isMatch, aResult = cParser.parse(sHtmlContainer, r'"#season-(\d+)')
    if not isMatch:
        cGui().showInfo()
        return
    total = len(aResult)
    for sSeason in aResult:
        oGuiElement = cGuiElement('Staffel ' + str(sSeason), SITE_IDENTIFIER, 'showEpisodes')
        oGuiElement.setSeason(sSeason)
        oGuiElement.setMediaType('season')
        oGuiElement.setThumbnail(sThumbnail)
        if isDesc:
            oGuiElement.setDescription(isDesc)
        cGui().addFolder(oGuiElement, params, True, total)
    cGui().setView('seasons')
    cGui().setEndOfDirectory()


def showEpisodes():
    params = ParameterHandler()
    # Parameter laden
    entryUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue('sThumbnail')
    sSeason = params.getValue('season')
    isDesc = params.getValue('sDesc')
    oRequest = cRequestHandler(entryUrl)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 4  # HTML Cache Zeit 4 Stunden
    sHtmlContent = oRequest.request()
    pattern = 'id="season-%s(.*?)</ul>' % sSeason
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        isMatch, aResult = cParser.parse(sHtmlContainer, r'data-title="Episode\s(\d+)')
    if not isMatch:
        cGui().showInfo()
        return

    total = len(aResult)
    for sEpisode in aResult:
        oGuiElement = cGuiElement('Episode ' + str(sEpisode), SITE_IDENTIFIER, 'showEpisodeHosters')
        oGuiElement.setThumbnail(sThumbnail)
        if isDesc:
            oGuiElement.setDescription(isDesc)
        oGuiElement.setMediaType('episode')
        params.setParam('entryUrl', entryUrl)
        params.setParam('season', sSeason)
        params.setParam('episode', sEpisode)
        cGui().addFolder(oGuiElement, params, False, total)
    cGui().setView('episodes')
    cGui().setEndOfDirectory()


def showEpisodeHosters():
    hosters = []
    params = ParameterHandler()
    # Parameter laden
    sUrl = params.getValue('entryUrl')
    sSeason = params.getValue('season')
    sEpisode = params.getValue('episode')
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    pattern = 'id="season-%s">(.*?)</ul>' % sSeason
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        pattern = '>%s</a>(.*?)</li>' % sEpisode
        isMatch, sHtmlLink = cParser.parseSingleResult(sHtmlContainer, pattern)
        if isMatch:
            isMatch, aResult = cParser.parse(sHtmlLink, 'data-link="([^"]+)')
            if isMatch:
                sQuality = '720'
                for sUrl in aResult:
                    if 'youtube' in sUrl:
                        continue
                    elif sUrl.startswith('//'):
                        sUrl = 'https:' + sUrl
                    sName = cParser.urlparse(sUrl).split('.')[0].strip()
                    if cConfig().isBlockedHoster(sName)[0]: continue  # Hoster aus settings.xml oder deaktivierten Resolver ausschließen
                    hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I][%sp][/I]' % (sName, sQuality), 'quality': sQuality}
                    hosters.append(hoster)
    if hosters:
        hosters.append('getHosterUrl')
    return hosters


def showHosters():
    hosters = []
    params = ParameterHandler()
    sUrl = params.getValue('entryUrl')
    sHtmlContent = cRequestHandler(sUrl, caching=False).request()
    pattern = '<iframe.*?src="([^"]+)'
    isMatch, hUrl = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        sHtmlContainer = cRequestHandler(hUrl).request()
        isMatch, aResult = cParser.parse(sHtmlContainer, 'data-link="([^"]+)')
        if isMatch:
            sQuality = '720'
            for sUrl in aResult:
                if 'youtube' in sUrl:
                    continue
                elif sUrl.startswith('//'):
                    sUrl = 'https:' + sUrl
                sName = cParser.urlparse(sUrl).split('.')[0].strip()
                if cConfig().isBlockedHoster(sName)[0]: continue  # Hoster aus settings.xml oder deaktivierten Resolver ausschließen
                hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I][%sp][/I]' % (sName, sQuality), 'quality': sQuality}
                hosters.append(hoster)
        if hosters:
            hosters.append('getHosterUrl')
        return hosters


def getHosterUrl(sUrl=False):
    return [{'streamUrl': sUrl, 'resolved': False}]


def showSearch():
    sSearchText = cGui().showKeyBoard(sHeading=cConfig().getLocalizedString(30281))
    if not sSearchText: return
    _search(False, sSearchText)
    cGui().setEndOfDirectory()


def _search(oGui, sSearchText):
    showEntries(URL_SEARCH % cParser.quotePlus(sSearchText), oGui, sSearchText)


def showSearchPage(): # Suche für die Page Funktion
    params = ParameterHandler()
    sNextPage = params.getValue('sNextPage') # URL mit nächster Seite
    sPageLast = params.getValue('sPageLast') # Anzahl gefundener Seiten
    #sHeading = 'Bitte eine Zahl zwischen 1 und ' + str(sPageLast) + ' wählen.'
    sHeading = cConfig().getLocalizedString(30282) + str(sPageLast)
    sSearchPageText = cGui().showKeyBoard(sHeading=sHeading)
    if not sSearchPageText: return
    sNextSearchPage = sNextPage.split('page/')[0].strip() + 'page/' + sSearchPageText + '/'
    showEntries(sNextSearchPage)
    cGui().setEndOfDirectory()


def showYearSearch():
    sYear = cGui().showKeyBoard(sHeading="Jahr eintragen (z.B., 2017)")
    if not sYear: return
    searchUrl = URL_MAIN + '/xfsearch/' + sYear
    showEntries(searchUrl)
    cGui().setEndOfDirectory()
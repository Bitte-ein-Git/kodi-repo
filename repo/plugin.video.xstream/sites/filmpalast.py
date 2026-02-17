# -*- coding: utf-8 -*-
# Python 3

# Always pay attention to the translations in the menu!
# Sprachauswahl für Filme
# HTML LangzeitCache hinzugefügt
# showValue:     24 Stunden
# showEntries:    6 Stunden
# showEpisodes:   4 Stunden

import re
from resources.lib.handler.ParameterHandler import ParameterHandler
from resources.lib.handler.requestHandler import cRequestHandler
from resources.lib.tools import logger, cParser
from resources.lib.gui.guiElement import cGuiElement
from resources.lib.config import cConfig
from resources.lib.gui.gui import cGui


SITE_IDENTIFIER = 'filmpalast'
SITE_NAME = 'FilmPalast'
SITE_ICON = 'filmpalast.png'

# Global search function is thus deactivated!
if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'false':
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'filmpalast.to') # Domain Auswahl über die xStream Einstellungen möglich
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status') # Status Code Abfrage der Domain
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER) # Ob Plugin aktiviert ist oder nicht

URL_MAIN = 'https://' + DOMAIN
# URL_MAIN = 'https://filmpalast.to'
URL_MOVIES = URL_MAIN + '/movies/%s'
URL_ENGLISH = URL_MAIN + '/search/genre/Englisch'
URL_SEARCH = URL_MAIN + '/search/title/%s'
URL_SERIES = URL_MAIN + '/serien/view'


def load(): # Menu structure of the site plugin
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    sLanguage = cConfig().getSetting('prefLanguage')
    
    # Logic moved from showMovieMenu to main load function
    if sLanguage == '0' or '1':    # Alle Sprachen oder Deutsch
        params.setParam('sUrl', URL_MOVIES % 'new')
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30502), SITE_IDENTIFIER, 'showEntries'), params)   # Filme
        params.setParam('sUrl', URL_MOVIES % 'top')
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30509), SITE_IDENTIFIER, 'showEntries'), params)  # Top movies
        params.setParam('sUrl', URL_MOVIES % 'imdb')
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30510), SITE_IDENTIFIER, 'showEntries'), params) # IMDB rating
        if sLanguage == '0': # Nur bei Alle Sprachen
            params.setParam('sUrl', URL_ENGLISH)
            cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30104), SITE_IDENTIFIER, 'showEntries'), params) # English
        params.setParam('sUrl', URL_MOVIES % 'new')
        params.setParam('value', 'genre')
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showValue'), params)    # Genre
        params.setParam('value', 'movietitle')
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30517), SITE_IDENTIFIER, 'showValue'), params)  # From A-Z
        
    if sLanguage == '2':    # English
        params.setParam('sUrl', URL_ENGLISH)
        cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30104), SITE_IDENTIFIER, 'showEntries'), params) # English
        
    elif sLanguage == '3':    # Japanisch
        cGui().showLanguage()

    # Add Serien entry above search
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30511), SITE_IDENTIFIER, 'showSeriesMenu'))  # Serien

    # Search added at the bottom
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'), params)   # Search
    cGui().setEndOfDirectory()


def showValue():
    params = ParameterHandler()
    value = params.getValue("value")
    oRequest = cRequestHandler(params.getValue('sUrl'), bypass_dns=True)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 24 # HTML Cache Zeit 1 Tag
    sHtmlContent = oRequest.request()
    pattern = '<section[^>]id="%s">(.*?)</section>' % value # Suche in der Section Einträge
    isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if isMatch:
        isMatch, aResult = cParser.parse(sContainer, 'href="([^"]+)">([^<]+)')
        aResult = sorted(aResult, key=lambda x: x[1].lower())  # Sort alphabetically by name (case-insensitive)
        for sUrl, sName in aResult:
            params.setParam('sUrl', sUrl)
            cGui().addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEntries'), params)
    if not isMatch:
        cGui().showInfo()
        return
    cGui().setEndOfDirectory()


def showEntries(entryUrl=False, sGui=False, sSearchText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    if not entryUrl: entryUrl = params.getValue('sUrl')
    isTvshow = False
    oRequest = cRequestHandler(entryUrl, ignoreErrors=(sGui is not False), bypass_dns=True)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # 6 Stunden
    sHtmlContent = oRequest.request()
    pattern = r'<article[^>]*>\s*<a href="([^"]+)" title="([^"]+)">\s*<img src=["\']([^"\']+)["\'][^>]*>(.*?)</article>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        pattern = r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"[^>]*>[^<]*<img[^>]*src=["\']([^"\']*)["\'][^>]*>\s*</a>(\s*)</article>'
        isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    seen_tv_shows = set()
    
    # SORTING CHANGE: Removed the check for '/movies/new'
    # Now everything is sorted alphabetically
    aResult = sorted(aResult, key=lambda x: x[1].lower())  # Sort alphabetically by name (case-insensitive)
    
    for sUrl, sName, sThumbnail, sDummy in aResult:
        isTvshow, _ = cParser.parse(sName, r'S\d\dE\d\d')
        # seriesname should not be crippled here!
        if sSearchText and not cParser.search(sSearchText, sName):
            continue

        if isTvshow:
            # Clean the name (e.g. "ABCDE S01E02" -> "ABCDE")
            cleanNameMatch = re.search(r'(.*?)\s*S\d+E\d+', sName, re.IGNORECASE)
            if cleanNameMatch:
                cleanName = cleanNameMatch.group(1).strip()
                # If we have already seen this show in this loop, skip it
                if cleanName in seen_tv_shows:
                    continue
                # Mark as seen and update the display name to the clean title
                seen_tv_shows.add(cleanName)
                sName = cleanName

        if sThumbnail.startswith('/'):
            sThumbnail = URL_MAIN + sThumbnail
        ### ÄNDERUNG ANFANG ###
        isYear, sYear = cParser.parseSingleResult(sDummy, r'Jahr:[^>]([\d]+)')
        isDuration, sDuration = cParser.parseSingleResult(sDummy, r'(?:Laufzeit|Spielzeit):[^>]([\d]+)')
        isRating, sRating = cParser.parseSingleResult(sDummy, 'Imdb:[^>]([^/]+)')
        ### ÄNDERUNG ENDE ###
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showSeasons' if isTvshow else 'showHosters')
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        oGuiElement.setThumbnail(sThumbnail)
        if isYear:
            oGuiElement.setYear(sYear)
        if isDuration:
            oGuiElement.addItemValue('duration', sDuration)
        if isRating:
            oGuiElement.addItemValue('rating', sRating.replace(',', '.'))
        # Parameter übergeben
        if sUrl.startswith('//'):
            params.setParam('entryUrl', 'https:' + sUrl)
        else:
            params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        oGui.addFolder(oGuiElement, params, isTvshow, total)
    if not sGui and not sSearchText:
        pattern = r'<a class="pageing[^"]*"\s*href=([^>]+)>[^\+]+\+</a>\s*</div>'
        isMatchNextPage, sNextUrl = cParser.parseSingleResult(sHtmlContent, pattern)
        if isMatchNextPage:
            sNextUrl = sNextUrl.replace("'", "").replace('"', '')
            if sNextUrl.startswith('/'):
                sNextUrl = URL_MAIN + sNextUrl
            params.setParam('sUrl', sNextUrl)
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        oGui.setView('tvshows' if isTvshow else 'movies')
        oGui.setEndOfDirectory()


def showSeasons():
    params = ParameterHandler()
    # Parameter laden
    sUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue("sThumbnail")
    sName = params.getValue('sName')
    oRequest = cRequestHandler(sUrl, bypass_dns=True)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 6  # HTML Cache Zeit 6 Stunden
    sHtmlContent = oRequest.request()
    pattern = r'<a[^>]*class="staffTab"[^>]*data-sid="(\d+)"[^>]*>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    if not isMatch:
        cGui().showInfo()
        return
    isDesc, sDesc = cParser.parseSingleResult(sHtmlContent, '"description">([^<]+)')
    total = len(aResult)
    for sSeason in aResult:
        oGuiElement = cGuiElement('Staffel ' + str(sSeason), SITE_IDENTIFIER, 'showEpisodes')
        oGuiElement.setTVShowTitle(sName)
        oGuiElement.setSeason(sSeason)
        oGuiElement.setMediaType('season')
        oGuiElement.setThumbnail(sThumbnail)
        if isDesc:
            oGuiElement.setDescription(sDesc)
        cGui().addFolder(oGuiElement, params, True, total)
    cGui().setView('seasons')
    cGui().setEndOfDirectory()


def showEpisodes():
    params = ParameterHandler()
    # Parameter laden
    sUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue("sThumbnail")
    sSeason = params.getValue('season')
    sShowName = params.getValue('TVShowTitle')
    oRequest = cRequestHandler(sUrl, bypass_dns=True)
    if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'true':
        oRequest.cacheTime = 60 * 60 * 4  # HTML Cache Zeit 4 Stunden
    sHtmlContent = oRequest.request()
    pattern = r'<div[^>]*class="staffelWrapperLoop[^"]*"[^>]*data-sid="%s">(.*?)</ul></div>' % sSeason
    isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    if not isMatch:
        cGui().showInfo()
        return

    pattern = 'href="([^"]+)'
    isMatch, aResult = cParser.parse(sContainer, pattern)
    isDesc, sDesc = cParser.parseSingleResult(sHtmlContent, '"description">([^<]+)')
    total = len(aResult)
    for sUrl in aResult:
        isMatch, sName = cParser.parseSingleResult(sUrl, r'e(\d+)')
        oGuiElement = cGuiElement('Episode ' + str(sName), SITE_IDENTIFIER, 'showHosters')
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setTVShowTitle(sShowName)
        oGuiElement.setSeason(sSeason)
        oGuiElement.setEpisode(sName)
        oGuiElement.setMediaType('episode')
        if sUrl.startswith('//'):
            params.setParam('entryUrl', 'https:' + sUrl)
        else:
            params.setParam('entryUrl', sUrl)
        if isDesc:
            oGuiElement.setDescription(sDesc)
        cGui().addFolder(oGuiElement, params, False, total)
    cGui().setView('episodes')
    cGui().setEndOfDirectory()


def showHosters():
    params = ParameterHandler()
    sUrl = params.getValue('entryUrl')
    if '-english' in sUrl: sLang = '(EN)'
    else: sLang = ''
    sHtmlContent = cRequestHandler(sUrl, caching=False, bypass_dns=True).request()
    pattern = 'hostName">([^<]+).*?(http[^"]+)' # Hoster Link
    releaseQuality = r'class="rb">.*?(\d\d\d+)p\.' # Release Qualität
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    isQuality, sQuality = cParser.parseSingleResult(sHtmlContent, releaseQuality)  # sReleaseQuality auslesen z.B. 1080
    if not isQuality: sQuality = '720'
    hosters = []
    if isMatch:
        for sName, sUrl in aResult:
            sName = sName.split(' HD')[0].strip()
            if 'Filemoon' in sName or 'Swiftload' in sName or 'Vidhide' in sName:
                sUrl = sUrl + '$$https://filmpalast.to/' # Referer hinzugefügt
                if cConfig().isBlockedHoster(sName)[0]: continue  # Hoster aus settings.xml oder deaktivierten Resolver ausschließen
                hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I]%s [%sp][/I]' % (sName, sLang, sQuality), 'languageCode': sLang, 'quality': sQuality}  # Qualität Anzeige aus Release Eintrag
                hosters.append(hoster)
            else:
                if cConfig().isBlockedHoster(sName)[0]: continue # Hoster aus settings.xml oder deaktivierten Resolver ausschließen
                hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I]%s [%sp][/I]' % (sName, sLang, sQuality), 'languageCode': sLang, 'quality': sQuality} # Qualität Anzeige aus Release Eintrag
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


def showSeriesMenu(): # Menu structure of series menu
    params = ParameterHandler()
    params.setParam('sUrl', URL_SERIES)
    cGui().addFolder(cGuiElement('Alle ' + cConfig().getLocalizedString(30511), SITE_IDENTIFIER, 'showEntries'), params) # Alle Serien
    params.setParam('value', 'movietitle')
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30517), SITE_IDENTIFIER, 'showValue'), params) # Von A bis Z
    cGui().setEndOfDirectory()

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
import urllib.parse

SITE_IDENTIFIER = 'megakino'
SITE_NAME = 'Megakino'
SITE_ICON = 'megakino.png'

# Global search function is thus deactivated!
if cConfig().getSetting('global_search_' + SITE_IDENTIFIER) == 'false':
    SITE_GLOBAL_SEARCH = False
    logger.info('-> [SitePlugin]: globalSearch for %s is deactivated.' % SITE_NAME)

# Domain Abfrage
DOMAIN = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '.domain', 'megakino1.to')
STATUS = cConfig().getSetting('plugin_' + SITE_IDENTIFIER + '_status')
ACTIVE = cConfig().getSetting('plugin_' + SITE_IDENTIFIER)

URL_MAIN = 'https://' + DOMAIN + '/'
URL_KINO = URL_MAIN + 'kinofilme/'
URL_MOVIES = URL_MAIN + 'films/'
URL_SERIES = URL_MAIN + 'serials/'
URL_ANIMATION = URL_MAIN + 'multfilm/'
URL_DOKU = URL_MAIN + 'documentary/'
URL_SEARCH = URL_MAIN + '?do=search&subaction=search&story=%s'

def load():
    logger.info('Load %s' % SITE_NAME)
    params = ParameterHandler()
    params.setParam('sUrl', URL_MAIN)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30500), SITE_IDENTIFIER, 'showEntries'), params)  # New
    params.setParam('sUrl', URL_KINO)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30501), SITE_IDENTIFIER, 'showEntries'), params)  # Current films in the cinema  
    params.setParam('sUrl', URL_MOVIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30502), SITE_IDENTIFIER, 'showEntries'), params)  # Movies
    params.setParam('sUrl', URL_ANIMATION)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30504), SITE_IDENTIFIER, 'showEntries'), params)  # Animated Films
    params.setParam('sUrl', URL_SERIES)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30511), SITE_IDENTIFIER, 'showEntries'), params)  # Series 
    params.setParam('sUrl', URL_DOKU)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30505), SITE_IDENTIFIER, 'showEntries'), params)  # Documentations
    params.setParam('sUrl', URL_MAIN)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30543), SITE_IDENTIFIER, 'showCollection'), params)  # Collections
    params.setParam('sUrl', URL_MAIN)
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30506), SITE_IDENTIFIER, 'showGenre'), params)    # Genre
    cGui().addFolder(cGuiElement(cConfig().getLocalizedString(30520), SITE_IDENTIFIER, 'showSearch'), params)   # Search
    cGui().setEndOfDirectory()

def showGenre():
    params = ParameterHandler()
    entryUrl = params.getValue('sUrl')
    sHtmlContent = getHtmlContent(entryUrl)
    
    if not sHtmlContent:
        cGui().showInfo()
        return
    
    pattern = '<div class="side-block__title">Genres</div>.*?<ul class="side-block__content side-block__menu"(.*?)</ul>'
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    
    if not isMatch:
        cGui().showInfo()
        return

    pattern = 'href="([^"]+)">([^<]+)</a>'
    isMatch, aResult = cParser.parse(sHtmlContainer, pattern)
    
    if not isMatch:
        cGui().showInfo()
        return

    for sUrl, sName in aResult:
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl[1:]
        params.setParam('sUrl', sUrl)
        cGui().addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()

def showCollection():
    params = ParameterHandler()
    entryUrl = params.getValue('sUrl')
    sHtmlContent = getHtmlContent(entryUrl)
    
    if not sHtmlContent:
        cGui().showInfo()
        return
    
    pattern = '<div class="side-block__title">Sammlung</div>.*?<div class="side-block__content collection-scroll">(.*?)</div>'
    isMatch, sHtmlContainer = cParser.parseSingleResult(sHtmlContent, pattern)
    
    if not isMatch:
        cGui().showInfo()
        return

    pattern = 'href="([^"]+)"[^>]*>.*?<div class="custom-collection-title">([^<]+)</div>'
    isMatch, aResult = cParser.parse(sHtmlContainer, pattern)
    
    if not isMatch:
        cGui().showInfo()
        return

    for sUrl, sName in aResult:
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl[1:]
        params.setParam('sUrl', sUrl)
        cGui().addFolder(cGuiElement(sName, SITE_IDENTIFIER, 'showEntries'), params)
    cGui().setEndOfDirectory()

def getHtmlContent(url):
    """Hilfsfunktion zum Abrufen von HTML-Inhalten mit Token-Umgehung"""
    logger.info(f'[megakino] Getting HTML content for: {url}')
    
    # Erster Versuch: Direkter Aufruf
    oRequest = cRequestHandler(url, bypass_dns=True)
    oRequest.cacheTime = 0
    oRequest.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    oRequest.addHeaderEntry('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
    oRequest.addHeaderEntry('Accept-Language', 'de-DE,de;q=0.9,en;q=0.8')
    oRequest.addHeaderEntry('Referer', URL_MAIN)
    
    sHtmlContent = oRequest.request()
    
    # Prüfen ob Token-Redirect erforderlich ist
    if sHtmlContent and 'yg=token' in sHtmlContent:
        logger.info('[megakino] Token redirect detected, getting token...')
        
        # Token URL erstellen
        token_url = URL_MAIN + 'index.php?yg=token'
        
        # Token abrufen
        oTokenRequest = cRequestHandler(token_url, bypass_dns=True)
        oTokenRequest.cacheTime = 0
        oTokenRequest.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        oTokenRequest.addHeaderEntry('Accept', '*/*')
        oTokenRequest.addHeaderEntry('Accept-Language', 'de-DE,de;q=0.9,en;q=0.8')
        oTokenRequest.addHeaderEntry('Referer', url)
        oTokenRequest.addHeaderEntry('X-Requested-With', 'XMLHttpRequest')
        
        token_response = oTokenRequest.request()
        logger.info(f'[megakino] Token response: {token_response}')
        
        # Nach Token-Abruf die ursprüngliche URL erneut aufrufen
        oRequest2 = cRequestHandler(url, bypass_dns=True)
        oRequest2.cacheTime = 0
        oRequest2.addHeaderEntry('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        oRequest2.addHeaderEntry('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8')
        oRequest2.addHeaderEntry('Accept-Language', 'de-DE,de;q=0.9,en;q=0.8')
        oRequest2.addHeaderEntry('Referer', URL_MAIN)
        
        sHtmlContent = oRequest2.request()
    
    if sHtmlContent and len(sHtmlContent) > 1000:
        logger.info(f'[megakino] Successfully retrieved HTML content, length: {len(sHtmlContent)}')
        return sHtmlContent
    else:
        logger.error(f'[megakino] Failed to retrieve valid HTML content, length: {len(sHtmlContent) if sHtmlContent else 0}')
        return None

def showEntries(entryUrl=False, sGui=False, sSearchText=False, sSearchPageText=False):
    oGui = sGui if sGui else cGui()
    params = ParameterHandler()
    isTvshow = False
    if not entryUrl: entryUrl = params.getValue('sUrl')
    
    logger.info(f'[megakino] Loading URL: {entryUrl}')
    
    sHtmlContent = getHtmlContent(entryUrl)
    
    if not sHtmlContent:
        logger.error('[megakino] No valid HTML content received')
        if not sGui: oGui.showInfo()
        return
    
    # Vereinfachtes Pattern für die Einträge
    pattern = '<a class="poster grid-item[^>]*href="([^"]+)"[^>]*>.*?<img[^>]*data-src="([^"]+)"[^>]*alt="([^"]+)"[^>]*>.*?<div class="poster__label">([^<]*)</div>.*?<h3 class="poster__title[^>]*>([^<]*)</h3>.*?<div class="poster__text[^>]*>([^<]*)</div>'
    isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    
    if not isMatch:
        logger.error('[megakino] No items found with main pattern')
        # Fallback Pattern
        pattern = '<a class="poster grid-item[^>]*href="([^"]+)"[^>]*>.*?<img[^>]*data-src="([^"]+)"[^>]*alt="([^"]+)"'
        isMatch, aResult = cParser.parse(sHtmlContent, pattern)
    
    if not isMatch or not aResult:
        logger.error('[megakino] No items found with any pattern')
        if not sGui: oGui.showInfo()
        return

    total = len(aResult)
    logger.info(f'[megakino] Found {total} items')
    
    for entry in aResult:
        if len(entry) >= 6:
            # Vollständiges Pattern
            sUrl = entry[0]
            sThumbnail = entry[1]
            sAltName = entry[2]
            sQuality = entry[3]
            sName = entry[4]
            sDesc = entry[5]
        else:
            # Einfaches Pattern
            sUrl = entry[0]
            sThumbnail = entry[1]
            sName = entry[2]
            sQuality = ''
            sDesc = ''
        
        if sSearchText and not cParser.search(sSearchText, sName):
            continue
        
        # Relative URLs korrigieren
        if sUrl.startswith('/'):
            sUrl = URL_MAIN + sUrl[1:]
        if sThumbnail.startswith('/'):
            sThumbnail = URL_MAIN + sThumbnail[1:]
        elif sThumbnail.startswith('//'):
            sThumbnail = 'https:' + sThumbnail
        
        # TV Show Erkennung
        isTvshow = 'staffel' in sName.lower() or 'season' in sName.lower() or 'serials' in entryUrl
        
        oGuiElement = cGuiElement(sName, SITE_IDENTIFIER, 'showEpisodes' if isTvshow else 'showHosters')
        
        if sQuality:
            oGuiElement.setQuality(sQuality)
        
        if sDesc:
            oGuiElement.setDescription(sDesc)
        
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setMediaType('tvshow' if isTvshow else 'movie')
        
        params.setParam('entryUrl', sUrl)
        params.setParam('sName', sName)
        params.setParam('sThumbnail', sThumbnail)
        params.setParam('sDesc', sDesc)
        
        oGui.addFolder(oGuiElement, params, isTvshow, total)
    
    # Nächste Seite suchen
    if not sGui and not sSearchText and not sSearchPageText:
        pattern = '<div class="pagination__btn-loader[^>]*>.*?<a href="([^"]+)"[^>]*>'
        isMatchNextPage, sNextUrl = cParser.parseSingleResult(sHtmlContent, pattern)
        
        if isMatchNextPage and sNextUrl:
            if sNextUrl.startswith('/'):
                sNextUrl = URL_MAIN + sNextUrl[1:]
            params.setParam('sUrl', sNextUrl)
            oGui.addNextPage(SITE_IDENTIFIER, 'showEntries', params)
        
        oGui.setView('tvshows' if isTvshow else 'movies')
        oGui.setEndOfDirectory()

def showEpisodes():
    params = ParameterHandler()
    sUrl = params.getValue('entryUrl')
    sThumbnail = params.getValue("sThumbnail")
    sName = params.getValue('sName')
    sDesc = params.getValue('sDesc')
    
    logger.info(f'[megakino] Loading episodes for: {sName}')
    
    sHtmlContent = getHtmlContent(sUrl)
    
    if not sHtmlContent:
        logger.error('[megakino] No valid HTML content for episodes')
        cGui().showInfo()
        return
    
    # Episoden Patterns
    patterns = [
        r'<option\s+value="ep([^"]+)">([^<]+)</option>',
        '<option[^>]*value="ep([^"]+)"[^>]*>([^<]+)</option>'
    ]
    
    aResult = []
    for pattern in patterns:
        isMatch, aResult = cParser.parse(sHtmlContent, pattern)
        if isMatch and aResult:
            break
    
    if not isMatch:
        logger.error('[megakino] No episodes found')
        cGui().showInfo()
        return

    total = len(aResult)
    for episode, episodeName in aResult:
        params.setParam('episodeId', episode)
        oGuiElement = cGuiElement(str(episodeName), SITE_IDENTIFIER, 'showEpisodeHosters')
        
        # Thumbnail URL korrigieren
        if sThumbnail.startswith('/'):
            sThumbnail = URL_MAIN + sThumbnail[1:]
        elif sThumbnail.startswith('//'):
            sThumbnail = 'https:' + sThumbnail
            
        oGuiElement.setThumbnail(sThumbnail)
        oGuiElement.setDescription(sDesc)
        oGuiElement.setTVShowTitle(sName)
        oGuiElement.setMediaType('episode')
        cGui().addFolder(oGuiElement, params, False, total)
    
    cGui().setView('episodes')
    cGui().setEndOfDirectory()

def showHosters():
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    sHtmlContent = getHtmlContent(sUrl)
    
    if not sHtmlContent:
        return hosters
    
    # Iframe Patterns
    patterns = [
        r'<iframe.*?src=([^\s]+)',
        '<iframe[^>]*src="([^"]+)"'
    ]
    
    aResult = []
    for pattern in patterns:
        isMatch, aResult = cParser.parse(sHtmlContent, pattern)
        if isMatch and aResult:
            break
    
    if isMatch:
        for sUrl in aResult:
            sQuality = '720'
            sUrl = sUrl.replace('"', '').replace("'", "").strip()
            if not sUrl.startswith('http'):
                continue
            if 'youtube' in sUrl: continue  # Youtube Trailer
            sName = cParser.urlparse(sUrl).split('.')[0].replace('https://', '').replace('http://', '')
            if 'Watch' in sName: sName = sName.replace('Watch', 'GXPlayer')
            if cConfig().isBlockedHoster(sName)[0]: continue
            hoster = {'link': sUrl, 'name': sName, 'displayedName': '%s [I][%sp][/I]' % (sName, sQuality), 'quality': sQuality}
            hosters.append(hoster)
    
    if hosters:
        hosters.append('getHosterUrl')
    return hosters

def showEpisodeHosters():
    hosters = []
    sUrl = ParameterHandler().getValue('entryUrl')
    episodeId = 'ep' + ParameterHandler().getValue('episodeId')
    sHtmlContent = getHtmlContent(sUrl)
    
    if not sHtmlContent:
        return hosters
    
    patterns = [
        '<select[^>]*id="%s"[^>]*>(.*?)</select>' % episodeId
    ]
    
    sContainer = None
    for pattern in patterns:
        isMatch, sContainer = cParser.parseSingleResult(sHtmlContent, pattern)
        if isMatch:
            break
    
    if isMatch:
        pattern = 'value="([^"]+)"'
        isMatch, aResult = cParser.parse(sContainer, pattern)
        
        if isMatch:
            for sUrl in aResult:
                sQuality = '720'
                if 'youtube' in sUrl: continue
                sName = cParser.urlparse(sUrl).split('.')[0].replace('https://', '').replace('http://', '')
                if cConfig().isBlockedHoster(sName)[0]: continue
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

def showSearchPage():
    params = ParameterHandler()
    sNextPage = params.getValue('sNextPage')
    sPageLast = params.getValue('sPageLast')
    sHeading = cConfig().getLocalizedString(30282) + str(sPageLast)
    sSearchPageText = cGui().showKeyBoard(sHeading=sHeading)
    if not sSearchPageText: return
    sNextSearchPage = sNextPage.split('page/')[0].strip() + 'page/' + sSearchPageText + '/'
    showEntries(sNextSearchPage)
    cGui().setEndOfDirectory()
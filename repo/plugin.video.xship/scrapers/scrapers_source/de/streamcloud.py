
# streamcloud
# 2023-08-01
# edit 2024-12-14

from resources.lib.utils import isBlockedHoster
from scrapers.modules.tools import cParser
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle, dom_parser
from resources.lib.control import getSetting, setSetting

SITE_IDENTIFIER = 'streamcloud'
SITE_DOMAIN = 'streamcloud.my'   # https://topstreamfilm.live/   https://meinecloud.click/movie/tt1630029
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        self.search_link = self.base_link + '/index.php?story=%s&do=search&subaction=search'
        self.sources = []


    def run(self, titles, year, season=0, episode=0, imdb=''):
        try:
            if season == 0:
                ## https://meinecloud.click/movie/tt1477834
                oRequest = cRequestHandler('https://meinecloud.click/movie/%s' % imdb, caching=True)
                sHtmlContent = oRequest.request()
                isMatch, aResult = cParser.parse(sHtmlContent, 'data-link="([^"]+)')
                for sUrl in aResult:
                    if sUrl.startswith('/'): sUrl = 'https:' + sUrl
                    isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl)
                    if isBlocked: continue
                    if url:
                        self.sources.append({'source': hoster, 'quality': '720p', 'language': 'de', 'url': url, 'direct': True, 'prioHoster': prioHoster})

            else:
                oRequest = cRequestHandler(self.search_link % imdb, caching=True)
                sHtmlContent = oRequest.request()
                pattern = 'class="thumb".*?title="([^"]+).*?href="([^"]+).*?_year">([^<]+)'
                isMatch, aResult = cParser.parse(sHtmlContent, pattern)
                if not isMatch: return self.sources

                sName, sUrl, sYear = aResult[0]
                oRequest = cRequestHandler(sUrl, caching=True)
                sHtmlContent = oRequest.request()
                pattern = '%sx%s\s.*?/>' % (str(season), str(episode))
                isMatch, sLinkContainer = cParser.parseSingleResult(sHtmlContent, pattern)
                pattern = 'href="([^"]+)'
                isMatch, aResult = cParser.parse(sLinkContainer, pattern)
                if not isMatch: return self.sources
                for sUrl in aResult:
                    if sUrl.startswith('/'): sUrl = 'https:' + sUrl
                    isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl)
                    if isBlocked: continue
                    if url:
                        self.sources.append({'source': hoster, 'quality': '720p', 'language': 'de', 'url': url, 'direct': True, 'prioHoster': prioHoster})

            return self.sources
        except:
            return self.sources

    def resolve(self, url):
        return url
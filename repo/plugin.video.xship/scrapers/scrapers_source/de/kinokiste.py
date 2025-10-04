
# kinokiste
# 2023-01-27
# edit 2024-12-14

from resources.lib.utils import isBlockedHoster
from scrapers.modules.tools import cParser
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle
from resources.lib.control import getSetting, setSetting, urljoin

SITE_IDENTIFIER = 'kinokiste'
SITE_DOMAIN = 'kinokiste.cloud'
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        # self.search_link = self.base_link + '/index.php?do=search&subaction=search&titleonly=3&story=%s'
        self.search_link = self.base_link + '/?do=search&subaction=search&titleonly=3&story=%s'
        self.sources = []

    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        sources = []
        t = set([cleantitle.get(i) for i in set(titles) if i])
        #years = (year, year+1, year-1, 0)
        links = []
        for sSearchText in titles:
            try:
                oRequest = cRequestHandler(self.search_link % sSearchText)
                # oRequest.addParameters('do', 'search')
                # oRequest.addParameters('subaction', 'search')
                # oRequest.addParameters('story', sSearchText)
                # oRequest.addParameters('titleonly', '3')
                sHtmlContent = oRequest.request()
                pattern = 'class="new_movie\d+">\s*<a\s+href="([^"]+)">[^<]*</a>.*?alt="([^"]+)".*?class="fl-quality[^"]+">([^<]+)'
                isMatch, aResult = cParser.parse(sHtmlContent, pattern)
                if not isMatch: continue
                for i in aResult:
                    if season == 0:
                        if cleantitle.get(i[1]) in t: # sName
                            if i not in links: links.append(i)
                    else:
                        if cleantitle.get(i[1].split('-')[0].strip()) in t and str(season) in i[1].split('-')[1]:
                            if i not in links: links.append(i)
                if len(links) > 0: break
            except:
                continue

        if len(links) == 0: return sources
        elif len(links) >= 1:
            for link in links:
                self.getStreams(link, year, season, episode, hostDict)
        return self.sources

    def getStreams(self, data, year, season, episode, hostDict):
        sHtmlContent = cRequestHandler(data[0]).request()
        isMatch, aYear = cParser.parse(sHtmlContent, 'l-year">(\d+)')
        if not int(aYear[0]) == year and season == 0: return
        if season == 0: pattern = '<a\s+href="#"\s+data-link="([^"]+)'
        else: pattern = '<a\s+href="#"\s+id="[^"]+_%s"\s+data-link="([^"]+)' % episode
        isMatch, aResult = cParser.parse(sHtmlContent, pattern)
        if not isMatch: return
        for i in aResult:
            sUrl = i
            if sUrl.startswith('/'): sUrl = urljoin('https:', sUrl)
            isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl)
            if isBlocked: continue
            if url: self.sources.append({'source': hoster, 'quality': data[2], 'language': 'de', 'url': url, 'direct': True, 'prioHoster': prioHoster})

    def resolve(self, url):
        try:
            return url
        except:
            return
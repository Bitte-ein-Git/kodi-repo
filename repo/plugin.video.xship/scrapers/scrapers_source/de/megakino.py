
# megakino
# 2022-07-19
# edit 2024-12-14

from resources.lib.utils import isBlockedHoster
import re
from scrapers.modules.tools import cParser  # re - alternative
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle, dom_parser
from resources.lib.control import getSetting, quote, quote_plus

SITE_IDENTIFIER = 'megakino'
SITE_DOMAIN = 'megakino.fi'
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        self.sources = []

    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        sources = []
        try:
            t = set([cleantitle.get(i) for i in set(titles) if i])
            #years = (year, year+1, year-1, 0)
            links = []
            for sSearchText in titles:
                try:
                    # url = self.search_link % (sSearchText)
                    oRequest = cRequestHandler(self.base_link)
                    oRequest.addParameters('do', 'search')
                    oRequest.addParameters('subaction', 'search')
                    #oRequest.addParameters('search_start', '0')
                    #oRequest.addParameters('full_search', '0')
                    #oRequest.addParameters('result_from', '1')
                    oRequest.addParameters('story', quote_plus(sSearchText))
                    # oRequest.addParameters('titleonly', '3')
                    sHtmlContent = oRequest.request()
                    r = dom_parser.parse_dom(sHtmlContent, 'div', attrs={'id': 'dle-content'})[0].content
                    #a = dom_parser.parse_dom(r, 'a')
                    #pattern = '<a\s+class=[^>]*href="([^"]+)">.*?alt="([^"]+)">\s*<div\s+class="poster__label">([^<]+).*?<li>.*?(\d{4}).*?</a>'
                    if season != 0:pattern = '<a\s+class="poster[^>]*href="([^"]+).*?alt="([^"]+)'
                    else: pattern = '<a\s+class="poster[^>]*href="([^"]+).*?alt="([^"]+)">.*?<li>.*?(\d{4}).*?</a>'
                    isMatch, aResult = cParser.parse(r, pattern)
                    if not isMatch: continue

                    if season == 0:
                        for sUrl, sName, sYear in aResult:  # sUrl, sName, sQuality, sYear
                            if not int(sYear) == year: continue
                            #if '1080' in sQuality: sQuality = '1080p'
                            if cleantitle.get(sName) in t:
                                links.append({'url': sUrl, 'name': sName, 'quality': 'HD', 'year': sYear})

                    elif season > 0:
                        for sUrl, sName in aResult:
                            sYear = ''
                            if cleantitle.get(sName.split('- S')[0].strip()) in t and str(season) in sName.split('- S')[1]:
                                links.append({'url': sUrl, 'name': sName.split('- S')[0].strip(), 'quality': 'HD', 'year': sYear})

                    if len(links) == 0 and season == 0:
                        for sUrl, sName, sYear in aResult:
                            if not int(sYear) == year: continue
                            #if '1080' in sQuality: sQuality = '1080p'
                            for a in t:
                                if any([a in cleantitle.get(sName)]):
                                    links.append({'url': sUrl, 'name': sName, 'quality': 'HD', 'year': sYear})
                                    break


                    if len(links) > 0: break

                except:
                    continue

            if len(links) == 0: return sources

            for link in links:
                sHtmlContent = cRequestHandler(link['url']).request()

                if season > 0:
                    self.quality = link['quality']
                    pattern = '<select\s+name="pmovie__select-items"\s+class="[^"]+"\s+style="[^"]+"\s+id="ep%s">\s*(.*?)\s*</select>' % str(episode)
                    isMatch, sHtmlContent = cParser.parseSingleResult(sHtmlContent, pattern)
                    isMatch, aResult = cParser().parse(sHtmlContent, 'value="([^"]+)')
                    if not isMatch: return sources
                else:
                    pattern = 'poster__label">([^/|<]+)'
                    isMatch, sQuality = cParser.parseSingleResult(sHtmlContent, pattern)
                    if '1080' in sQuality: sQuality = '1080p'
                    quality = sQuality if isMatch else link['quality']

                    # pattern = '<iframe\s+id="film_main"\s+data-src="([^"]+)"'
                    pattern = '<iframe.*?src=(?:"|)([^"|\s]+)'
                    isMatch, aResult = cParser().parse(sHtmlContent, pattern)
                    if not isMatch: return sources
                    for sUrl in aResult:
                        if sUrl.startswith('/'): sUrl = re.sub('//', 'https://', sUrl)
                        if sUrl.startswith('/'): sUrl = 'https:/' + sUrl
                        isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl)
                        if isBlocked: continue
                        if url: self.sources.append({'source': hoster, 'quality': quality, 'language': 'de', 'url': url, 'direct': True, 'prioHoster': prioHoster})

            return self.sources
        except:
            return self.sources


    def resolve(self, url):
        try:
            return url
        except:
            return
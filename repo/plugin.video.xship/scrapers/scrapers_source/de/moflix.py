

#2023-07-28
# edit 2024-12-30

import json
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle, dom_parser
from resources.lib.control import getSetting, quote
from resources.lib.utils import isBlockedHoster

SITE_IDENTIFIER = 'moflix'
SITE_DOMAIN = 'moflix-stream.xyz'
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        # self.search_link = self.base_link + '/secure/search/%s?type=&limit=8&provider='
        self.search_link = self.base_link + '/api/v1/search/%s?query=%s&limit=8'
        self.sources = []

    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        try:
            t = set([cleantitle.get(i) for i in set(titles) if i])
            links = []
            for title in titles:
                title = quote(title)
                oRequest = cRequestHandler(self.search_link % (title, title))
                oRequest.addHeaderEntry('Referer', self.base_link + '/')
                jSearch = json.loads(oRequest.request())  # .values()
                # if not 'success' in jSearch['status']: continue
                if not jSearch: continue
                aResults = jSearch['results']
                for i in aResults:
                    if 'imdb_id' in i and i['imdb_id'] == imdb:
                        links.append({'id': i['id'], 'name': i['name']})
                        break
                    elif season == 0:
                        if 'is_series' in i and i['is_series']: continue
                        if 'year' in i and year != i['year']: continue
                        if cleantitle.get(i['name']) in t:
                            links.append({'id': i['id'], 'name': i['name']})
                    else:
                        if 'is_series' in i and not i['is_series']: continue
                        if cleantitle.get(i['name']) in t:
                            id = i['id']
                            url = self.base_link + '/api/v1/titles/%s?load=images,genres,productionCountries,keywords,videos,primaryVideo,seasons,compactCredits' % id
                            oRequest = cRequestHandler(url)
                            oRequest.addHeaderEntry('Referer', url)
                            jSearch = json.loads(oRequest.request())
                            links.append({'id': jSearch['title']['id'], 'name': i['name']})

                if len(links) > 0: break
                #
            if len(links) == 0: return self.sources
            for link in links:
                id = link['id']
                if season == 0:
                    # url = self.base_link + '/secure/titles/%s?titleId=%s' % (id, id)
                    url = self.base_link + '/api/v1/titles/%s?load=images,genres,productionCountries,keywords,videos,primaryVideo,seasons,compactCredits' % id
                else:
                    # url = self.base_link + '/secure/titles/%s?titleId=%sseasonNumber=%s&episodeNumber=%s' % (id, id, season, episode)
                    url = self.base_link + '/api/v1/titles/%s/seasons/%s/episodes/%s?load=videos,compactCredits,primaryVideo' % (id, season, episode)
                oRequest = cRequestHandler(url)
                oRequest.addHeaderEntry('Referer', url)
                jSearch = json.loads(oRequest.request())
                # if not 'success' in jSearch['status']: continue
                if not jSearch: continue
                if season == 0:
                    jVideos = jSearch['title']['videos']
                else:
                    jVideos = jSearch['episode']['videos']

                for j in jVideos:
                    quality = j['quality'] if j['quality'] else 'SD'
                    quality = '1080p' if '1080' in quality else '720p'
                    sUrl = j['src']
                    isBlocked, sHoster, url, prioHoster = isBlockedHoster(sUrl)
                    if 'poophq' in sHoster: sHoster = 'Veev'
                    elif 'moflix-stream.click' in sHoster: sHoster = 'FileLions'
                    elif 'moflix-stream.day' in sHoster: sHoster = 'VidGuard'
                    if isBlocked: continue
                    if url:
                        self.sources.append({'source': sHoster, 'quality': quality, 'language': 'de', 'url': url, 'info': j['language'], 'direct': True, 'prioHoster': prioHoster})

            return self.sources
        except:
            return self.sources

    def resolve(self, url):
        try:
            return url
        except:
            return
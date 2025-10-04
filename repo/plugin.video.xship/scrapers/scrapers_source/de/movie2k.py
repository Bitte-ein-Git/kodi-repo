
# megakino to (clone)  # https://movie2k.at/
# 2022-11-04
# edit 2024-12-14

from resources.lib.utils import isBlockedHoster
import re, json
from resources.lib.control import getSetting
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules.tools import cParser

SITE_IDENTIFIER = 'movie2k'
SITE_DOMAIN = 'www2.movie2k.ch' # https://www3.hdfilme.me/  https://kinokiste.eu/
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        # self.api = 'api.' + self.domain
        #self.search_link = 'https://'+ self.api +'/data/browse?lang=2&keyword=%s&year=%s&rating=&votes=&genre=&country=&cast=&directors=&type=%s&order_by=&page=1' # 'browse?c=movie&m=filter&year=%s&keyword=%s'
        #self.search_link = 'https://api.movie2k.ch/data/search/?lang=2&keyword=%s'
        # https://api.movie2k.ch/data/browse?keyword=mulan
        # https://movie2k.ch/browse?c=movie&m=filter&keyword=mulan
        #self.search_link = 'https://api.movie2k.ch/data/browse?lang=2&keyword=%s&year=%s&rating=&votes=&genre=&country=&cast=&directors=&type=%s&order_by=&page=1'
        self.search_link = 'https://movie2k.ch/data/browse/?lang=2&keyword=%s&year=%s&type=%s&page=1'   # (title, year, mtype)
        self.sources = []

    def run(self, titles, year, season=0, episode=0, imdb=''):
        jSearch = self.search(titles, year, season, episode)
        if jSearch == [] or jSearch == 0: return
        jSearch = sorted(jSearch, key=lambda k: k['added'], reverse=True)
        total = 0
        loop = 0
        for i in range(len(jSearch) -1, -1, -1):
            sUrl = jSearch[i]['stream']
            if 'streamtape' in sUrl: continue
            loop += 1
            print (str(loop)+' '+ sUrl)
            if loop == 20:
                break
            quality = 'HD'
            if jSearch[i].get('release', False) and '1080p' in jSearch[i].get('release'): quality = '1080p'
            isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl)
            if isBlocked: continue
            if url:
                # quality = 'HD'
                # if i.get('release', False) and '1080p' in i.get('release'): quality = '1080p'
                self.sources.append({'source': hoster, 'quality': quality, 'language': 'de', 'url': url, 'direct': True, 'prioHoster': prioHoster})
                total += 1
                if total == 3: break

        return self.sources

    def resolve(self, url):
        return  url

    def search(self, titles, year, season, episode):
        jSearch = []
        mtype = 'movies'
        if season > 0:
            year = ''
            mtype = 'tvseries'
        for title in titles:
            try:
                query = self.search_link % (title, year, mtype)
                oRequest = cRequestHandler(query)
                Search = oRequest.request()
                if '"success":false' in Search: continue
                Search = re.sub(r'\\\s+\\', '\\\\',   Search) # error - Rick and Morty
                jSearch = json.loads(Search)['movies']
                if jSearch == []:  continue
                if season > 0:
                    for i in jSearch:
                        isMatch, sSeason = cParser.parseSingleResult(i.get('title'), 'Staffel.*?(\d+)')
                        if sSeason == str(season):
                            id = i.get('_id', False)
                            if id: break
                else:
                    for i in jSearch:
                        if i.get('year', False) and  not i.get('year') == year: continue
                        id = i.get('_id', False)
                        if id: break
                oRequest = cRequestHandler('https://movie2k.ch/data/watch/?_id=%s'  % id)
                jSearch = json.loads(oRequest.request())
                if season > 0:
                    jSearch = jSearch['streams']
                    #jSearch = sorted(jSearch, key=lambda k: k['e'], reverse=False)
                    jSearchNew = []
                    for i in jSearch:
                        if not i.get('e', False): continue
                        elif not str(i.get('e')) == str(episode): continue
                        jSearchNew.append(i)
                    return jSearchNew
                else:
                    return jSearch['streams']
            except:
                continue
        return jSearch

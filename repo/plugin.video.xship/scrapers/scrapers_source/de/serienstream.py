
#2023-03-20
# edit 2025-06-14

import re
import datetime
from resources.lib.control import  getSetting, urljoin, setSetting
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle, dom_parser
from resources.lib.utils import isBlockedHoster

try:
    from scrapers.modules.jsnprotect import cHelper
except:
    pass

SITE_IDENTIFIER = 'serienstream'
SITE_DOMAIN = 's.to'
SITE_NAME = SITE_IDENTIFIER.upper()
#date = datetime.date.today()
#current_year = int(date.strftime("%Y"))

class source:
    def __init__(self):
        self.priority = 2
        self.language = ['de']
        # self.domains = ['serienstream.to']
        #self.base_link = 'https://s.to' # 186.2.175.5
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain
        self.search_link = '/serien'
        #self.search_link = '/ajax/seriesSearch?keyword=%s'
        # https://s.to/ajax/seriesSearch?keyword=rick%20and
        # https://186.2.175.5/ajax/seriesSearch?keyword=rick%20and
        self.sources = []

    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        aLinks = []
        if season == 0: return self.sources
        try:
            t = [cleantitle.get(i) for i in titles if i]
            url = urljoin(self.base_link, self.search_link)
            oRequest = cRequestHandler(url)
            oRequest.cacheTime = 60*60*24*7
            sHtmlContent = oRequest.request()
            links = dom_parser.parse_dom(sHtmlContent, "div", attrs={"class": "genre"})
            links = dom_parser.parse_dom(links, "a")
            links = [(i.attrs["href"], i.content) for i in links]
            for i in links:
                for a in t:
                    try:
                        if any([a in cleantitle.get(i[1])]):
                            aLinks.append({'source': i[0]})
                            break
                    except:
                        pass
            if len(aLinks) == 0: return self.sources
            for i in aLinks:
                url = i['source']
                self.run2(url, year, season=season, episode=episode, hostDict=hostDict, imdb=imdb)
        except:
            return self.sources
        return self.sources

    def run2(self, url, year, season=0, episode=0, hostDict=None, imdb=None):
        try:
            url = url[:-1] if url.endswith('/') else url
            if "staffel" in url:
                url = re.findall("(.*?)staffel", url)[0]
            url += '/staffel-%d/episode-%d' % (int(season), int(episode))
            url = urljoin(self.base_link, url)
            sHtmlContent = cRequestHandler(url).request()

            #startDate = dom_parser.parse_dom(sHtmlContent, 'span', attrs={'itemprop': 'startDate'})
            #startDate = int(dom_parser.parse_dom(startDate[0].content, 'a')[0].content)
            # endDate = dom_parser.parse_dom(sHtmlContent, 'span', attrs={'itemprop': 'endDate'})
            # endDate = dom_parser.parse_dom(endDate[0].content, 'a')[0].content
            # endDate = current_year if endDate == 'Heute' else int(endDate)
            # if not startDate <= year <= endDate: return
            # if not startDate == year: return

            a = dom_parser.parse_dom(sHtmlContent, 'a', attrs={'class': 'imdb-link'}, req='href')
            foundImdb = a[0].attrs["data-imdb"]
            if not foundImdb == imdb: return

            lr = dom_parser.parse_dom(sHtmlContent, 'div', attrs={'class': 'hosterSiteVideo'})
            r = dom_parser.parse_dom(lr, 'li', attrs={'data-lang-key': re.compile('[1]')}) #- only german
            if r == []: r = dom_parser.parse_dom(lr, 'li', attrs={'data-lang-key': re.compile('[1|2|3]')})

            r = [(i.attrs['data-link-target'], dom_parser.parse_dom(i, 'h4'),
                  'subbed' if i.attrs['data-lang-key'] == '3' else '' if i.attrs['data-lang-key'] == '1' else 'English/OV' if i.attrs['data-lang-key'] == '2' else '') for i
                 in r]
            r = [(i[0], re.sub('\s(.*)', '', i[1][0].content), 'HD' if 'hd' in i[1][0][1].lower() else 'SD', i[2]) for i in r]

            login, password = self._getLogin()
            import requests
            requests.packages.urllib3.disable_warnings()
            s = requests.Session()
            URL_LOGIN = 'https://186.2.175.5/login'
            payload = {'email': login, 'password': password}
            res = requests.get(URL_LOGIN, verify=False)
            s.post(URL_LOGIN, data=payload, cookies=res.cookies, verify=False)

            for url, host, quality, info in r:
                try:
                    sUrl = s.get('https://186.2.175.5' + url, verify=False).url
                except:
                    sUrl = 'https://186.2.175.5'

                quality = 'HD' # temp
                isBlocked, hoster, url, prioHoster = isBlockedHoster(sUrl, isResolve=True)
                if isBlocked: continue
                self.sources.append(
                    {'source': host, 'quality': quality, 'language': 'de', 'url': url , 'info': info, 'direct': True, 'priority': self.priority, 'prioHoster': prioHoster})
            return self.sources
        except:
            return self.sources

    def resolve(self, url):
        return url
        # login, password = self._getLogin()
        # import requests
        # requests.packages.urllib3.disable_warnings()
        # s = requests.Session()
        # URL_LOGIN = 'https://186.2.175.5/login'
        # payload = {'email': login, 'password': password}
        # r = requests.get(URL_LOGIN, verify = False)
        # s.post(URL_LOGIN, data=payload, cookies = r.cookies, verify = False)
        #
        # try: sUrl = s.get('https://186.2.175.5' + url, verify = False).url
        # except: sUrl = 'https://186.2.175.5'
        # if 'https://186.2.175.5' in sUrl:
        #     import xbmcgui, xbmcaddon
        #     AddonName = xbmcaddon.Addon().getAddonInfo('name')
        #     xbmcgui.Dialog().ok(AddonName, "- GeschÃ¼tzter Link - \nIn den Einstellungen die Kontodaten (Login) fÃ¼r Serienstream Ã¼berprÃ¼fen")
        #     return
        # else:
        #     return sUrl

    @staticmethod
    def _getLogin():
        login = ''
        password = ''
        try:
            login = cHelper.UserName
            password = cHelper.PassWord
            setSetting('serienstream.user', login)
            setSetting('serienstream.pass', password)
        except:
            login = getSetting(SITE_IDENTIFIER + '.user')
            password = getSetting(SITE_IDENTIFIER + '.pass')
        finally:
            if login == '' or password == '':
                import xbmcgui, xbmcaddon
                AddonName = xbmcaddon.Addon().getAddonInfo('name')
                xbmcgui.Dialog().ok(AddonName,
                                    "In den Einstellungen die Kontodaten (Login) fÃ¼r %s eintragen / Ã¼berprÃ¼fen\nBis dahin wird %s von der Suche ausgeschlossen. Es erfolgt kein erneuter Hinweis!" % (
                                    SITE_NAME, SITE_NAME))
                setSetting('provider.' + SITE_IDENTIFIER, 'false')
                exit()
            else:
                return login, password



# edit 2025-06-14

from resources.lib.utils import isBlockedHoster
import re, random, base64, ast, binascii, json, requests, string, hashlib, pyaes
from resources.lib.control import quote_plus, unquote_plus, infoDialog, urlparse, getSetting
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import dom_parser, cleantitle
from scrapers.modules.tools import cParser, cUtil
from resources.lib import log_utils

SITE_IDENTIFIER = 'kinoger'
SITE_DOMAIN = 'kinoger.com'
SITE_NAME = SITE_IDENTIFIER.upper()

class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain
        self.search = self.base_link + '/index.php?do=search&subaction=search&search_start=1&full_search=0&result_from=1&titleonly=3&story=%s'
        self.sources = []
        #self.search = self.base_link + '?do=search&subaction=search&titleonly=3&story=%s&x=5&y=11&submit=submit'
        # http://kinoger.to/index.php?do=search&subaction=search&search_start=1&full_search=0&result_from=1&titleonly=3&story=Captain%20Marvel


    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        sources = []
        items = []
        url = ''
        try:
            t = [cleantitle.get(i) for i in titles  if i]
            years = [str(year), str(year + 1)] if season == 0 else ['']
            for title in titles:
                try:
                    sUrl = self.search % title
                    oRequest = cRequestHandler(sUrl)
                    oRequest.removeBreakLines(False)
                    oRequest.removeNewLines(False)
                    oRequest.cacheTime = 60 * 60 * 12
                    sHtmlContent = oRequest.request()

                    search_results = dom_parser.parse_dom(sHtmlContent, 'div', attrs={'class': 'title'})
                    search_results = dom_parser.parse_dom(search_results, 'a')
                    search_results = [(i.attrs['href'], i.content) for i in search_results]
                    search_results = [(i[0], re.findall('(.*?)\((\d+)', i[1])[0]) for i in search_results]

                    if season > 0:
                        for x in range(0, len(search_results)):
                            title = cleantitle.get(search_results[x][1][0])
                            if 'staffel' in title and any(k in title for k in t):
                                url = search_results[x][0]
                    else:
                        for x in range(0, len(search_results)):
                            title = cleantitle.get(search_results[x][1][0])
                            if any(k in title for k in t) and search_results[x][1][1] in years:
                                url = search_results[x][0]
                                break
                    if url != '': break
                except:
                    pass

            if url == '': return sources

            oRequest = cRequestHandler(url)
            oRequest.cacheTime = 60 * 60 * 12
            sHtmlContent = oRequest.request()
            quali = re.findall('title="Stream.(.+?)"', sHtmlContent)
            links = re.findall('.show.+?,(\[\[.+?\]\])', sHtmlContent)
            if len(links) == 0: return sources

            if season > 0 and episode > 0:
                season = season - 1
                episode = episode - 1

            for i in range(0, len(links)):
                if 'playerx' in links[i]: continue #ka temp off
                elif 'kinoger.ru' in links[i]: continue
                elif 'wolfstream.tv' in links[i]: continue  # Offline

                direct = True
                pw = ast.literal_eval(links[i])
                url = (pw[season][episode]).strip()

                isBlocked, hoster, url, prioHoster = isBlockedHoster(url, isResolve=False)
                if isBlocked: direct = False
                quality = quali[i]
                if quality == '': quality = 'SD'
                if quality == 'HD': quality = '720p'
                if quality == 'HD+': quality = '1080p'
                items.append({'source': hoster, 'quality': quality, 'url': url, 'direct': direct, 'prioHoster': prioHoster})

            headers = '&Accept-Language=de%2Cen-US%3Bq%3D0.7%2Cen%3Bq%3D0.3&Accept=%2A%2F%2A&User-Agent=Mozilla%2F5.0+%28Windows+NT+10.0%3B+Win64%3B+x64%3B+rv%3A99.0%29+Gecko%2F20100101+Firefox%2F99.0'
            for item in items:
                try:
                    if item['source'] == 'kinoger.ru': #continue
                        def content_decryptor(html_content, passphrase):
                            match = re.compile(r'''JScripts = '(.+?)';''', re.DOTALL).search(html_content)
                            if match:
                                # Parse the JSON string
                                json_obj = json.loads(match.group(1))

                                # Extract the salt, iv, and ciphertext from the JSON object
                                salt = binascii.unhexlify(json_obj["s"])
                                iv = binascii.unhexlify(json_obj["iv"])
                                ct = base64.b64decode(json_obj["ct"])

                                # Concatenate the passphrase and the salt
                                concated_passphrase = passphrase.encode() + salt

                                # Compute the MD5 hashes
                                md5 = [hashlib.md5(concated_passphrase).digest()]
                                result = md5[0]
                                i = 1
                                while len(result) < 32:
                                    md5.append(hashlib.md5(md5[i - 1] + concated_passphrase).digest())
                                    result += md5[i]
                                    i += 1

                                # Extract the key from the result
                                key = result[:32]

                                # Decrypt the ciphertext using AES-256-CBC
                                aes = pyaes.AESModeOfOperationCBC(key, iv)
                                decrypter = pyaes.Decrypter(aes)
                                plain_text = decrypter.feed(ct)
                                plain_text += decrypter.feed()

                                # Return the decrypted data as a JSON object
                                return json.loads(plain_text.decode())
                            else:
                                return None

                        sUrl = item['url']
                        oRequest = cRequestHandler(sUrl, caching=False, ignoreErrors=True)
                        oRequest.addHeaderEntry('Referer', 'https://kinoger.com/')
                        sHtmlContent = oRequest.request()
                        decryptHtmlContent = content_decryptor(sHtmlContent, 'H&5+Tx_nQcdK{U,.')  # Decrypt Content

                        isMatch, hUrl = cParser.parseSingleResult(decryptHtmlContent, 'sources.*?file.*?(http[^"]+)')

                        if isMatch:
                            hUrl = hUrl.replace('\\', '')
                            oRequest = cRequestHandler(hUrl, caching=False, ignoreErrors=True)
                            oRequest.addHeaderEntry('Referer', 'https://kinoger.ru/')
                            oRequest.addHeaderEntry('Origin', 'https://kinoger.ru')
                            oRequest.removeNewLines(False)
                            sHtmlContent = oRequest.request()
                            pattern = 'RESOLUTION=\d+x(\d+).*?\n([^#"]+)'
                            isMatch, aResult = cParser.parse(sHtmlContent, pattern)
                            if not isMatch: continue
                            for sQualy, sUrl in aResult:
                                sUrl = (hUrl.split('video')[0].strip() + sUrl.strip())
                                sUrl = sUrl + '|Origin=https%3A%2F%2Fkinoger.ru&Referer=https%3A%2F%2Fkinoger.ru%2F' + headers
                                #hoster = {'link': sUrl, 'name': 'Kinoger.ru ' + sQualy, 'resolveable': True}
                                sources.append({'source': item['source'], 'quality': sQualy + 'p', 'language': 'de', 'url': sUrl, 'direct': item['direct']})


                    elif 'kinoger.be' in item['source']:    # One Piece Film: Red / Elemental (2023) / Thanksgiving 2023
                        url = item['url']
                        # url = url.replace('kinoger.be', 'streamhide.to')
                        # sources.append({'source': item['source'], 'quality': item['quality'], 'language': 'de', 'url': url, 'direct': False})
                        oRequest = cRequestHandler(url, ignoreErrors=True)
                        oRequest.addHeaderEntry('Referer', 'https://kinoger.com/')
                        sHtmlContent = oRequest.request()
                        sHtmlContent += cUtil.get_packed_data(sHtmlContent)
                        pattern = r'''sources:\s*\[{file:\s*["'](?P<url>[^"']+)'''
                        isMatch, sUrl = cParser.parseSingleResult(sHtmlContent, pattern)
                        if not isMatch: continue
                        sMaster_m3u8 = cRequestHandler(sUrl).request()
                        pattern = 'RESOLUTION=([^,]+).*?(index.*?.m3u8)'
                        isMatch, aResult = cParser.parse(sMaster_m3u8, pattern)
                        if not isMatch: continue
                        for sQualy, sIndex in aResult:
                            sQualy = self._quality(sQualy)
                            hUrl  = sUrl.replace('master.m3u8',sIndex )
                            sources.append({'source': item['source'], 'quality': sQualy, 'language': 'de', 'url': hUrl, 'direct': item['direct'], 'prioHoster': 50})

                    else:
                        isBlocked, hoster, url, prioHoster = isBlockedHoster(item['url'], isResolve=True)
                        if isBlocked: continue
                        sources.append({'source': item['source'], 'quality': item['quality'], 'language': 'de','url': url, 'direct': item['direct'], 'prioHoster': item['prioHoster']})

                except:
                    continue


            if len(sources) == 0:
                log_utils.log('Kinoger: kein Provider - %s ' % titles[0], log_utils.LOGINFO)
            else:
                for source in sources:
                    if source not in self.sources: self.sources.append(source)
                return self.sources
        except:
            return sources


    def resolve(self, url):
        try:
            return url
        except:
            return


    def _quality(self, q): # Kinoger.be Quality
        hl = q.split('x')
        h = int(hl[0])
        l = int(hl[1])
        if h >= 1920: return '1080p'
        elif l >= 720 or h >= 1080: return '720p'
        else: return 'SD'
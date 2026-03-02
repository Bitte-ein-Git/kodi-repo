# -*- coding: utf-8 -*-
# Python 3
# xShip source provider for SerienStream (s.to)
# Rewritten from xStream browser plugin to xShip source class (Issue #50)

from resources.lib.control import getSetting, urlparse
from resources.lib.requestHandler import cRequestHandler
from resources.lib.utils import isBlockedHoster, getHostDict
from scrapers.modules import cleantitle
from scrapers.modules.tools import cParser
from resources.lib import log_utils

SITE_IDENTIFIER = 'serienstream'
SITE_DOMAIN = 's.to'
SITE_NAME = 'SerienStream'


class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        if self.domain == '186.2.175.5':
            self.base_link = 'http://' + self.domain
        else:
            self.base_link = 'https://' + self.domain
        self._session = None

    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        sources = []
        try:
            # s.to is TV only — skip movies
            if not season or not episode:
                return sources

            # Check credentials
            username = getSetting('serienstream.user')
            password = getSetting('serienstream.pass')
            if not username or not password:
                log_utils.log('SerienStream: No credentials configured', log_utils.LOGWARNING)
                return sources

            # Build clean title set for matching
            t = set(cleantitle.get(i) for i in titles if i)

            # Step 1: Fetch series list and find matching show
            oRequest = cRequestHandler(self.base_link + '/serien')
            oRequest.cacheTime = 60 * 60 * 24
            sHtmlContent = oRequest.request()
            if not sHtmlContent:
                return sources

            pattern = r'<li[^>]*class="series-item"[^>]*>\s*<a[^>]*href="(/serie/[^"]*)"[^>]*>([^<]+)</a>'
            isMatch, aResult = cParser.parse(sHtmlContent, pattern)
            if not isMatch:
                log_utils.log('SerienStream: Could not parse series list', log_utils.LOGWARNING)
                return sources

            show_url = None
            for sUrl, sName in aResult:
                if cleantitle.get(sName.strip()) in t:
                    show_url = sUrl
                    break

            if not show_url:
                log_utils.log('SerienStream: No title match found', log_utils.LOGDEBUG)
                return sources

            # Step 2: Fetch show page, find matching season
            oRequest = cRequestHandler(self.base_link + show_url)
            oRequest.cacheTime = 60 * 60 * 24
            sHtmlContent = oRequest.request()
            if not sHtmlContent:
                return sources

            pattern = r'<nav[^>]*id="season-nav"[^>]*>(.*?)</nav>'
            isMatch, aResult_nav = cParser.parse(sHtmlContent, pattern)
            if not isMatch or not aResult_nav:
                return sources

            pattern = r'<a[^>]*href="(/serie/[^"]*)"[^>]*data-season-pill="(\d+)"'
            isMatch, aResult = cParser.parse(aResult_nav[0], pattern)
            if not isMatch:
                return sources

            season_url = None
            for sUrl, sNr in aResult:
                if int(sNr) == int(season):
                    season_url = sUrl
                    break

            if not season_url:
                log_utils.log('SerienStream: Season %s not found' % season, log_utils.LOGDEBUG)
                return sources

            # Step 3: Fetch season page, find matching episode
            oRequest = cRequestHandler(self.base_link + season_url)
            oRequest.cacheTime = 60 * 60 * 4
            sHtmlContent = oRequest.request()
            if not sHtmlContent:
                return sources

            pattern = r'<table[^>]*class="[^"]*episode-table[^"]*"[^>]*>(.*?)</table>'
            isMatch, aResult_table = cParser.parse(sHtmlContent, pattern)
            if not isMatch or not aResult_table:
                return sources

            pattern = r"onclick=\"window\.location='([^']+)'[^>]*>.*?episode-number-cell[^>]*>\s*(\d+)"
            isMatch, aResult = cParser.parse(aResult_table[0], pattern)
            if not isMatch:
                return sources

            episode_url = None
            for sUrl, sEpNr in aResult:
                if int(sEpNr) == int(episode):
                    episode_url = sUrl
                    break

            if not episode_url:
                log_utils.log('SerienStream: Episode %s not found' % episode, log_utils.LOGDEBUG)
                return sources

            # Step 4: Fetch episode page, parse hoster buttons
            ep_full_url = episode_url if episode_url.startswith('http') else self.base_link + episode_url
            oRequest = cRequestHandler(ep_full_url)
            oRequest.cacheTime = 60 * 60  # 1 hour
            sHtmlContent = oRequest.request()
            if not sHtmlContent:
                return sources

            pattern = r'data-play-url="([^"]+)"[^>]*data-auto-embed="[^"]*"[^>]*data-provider-name="([^"]+)"[^>]*data-language-label="[^"]*"[^>]*data-language-id="([^"]+)"'
            isMatch, aResult = cParser.parse(sHtmlContent, pattern)
            if not isMatch:
                return sources

            hostblockDict = getHostDict()
            for play_url, provider_name, lang_id in aResult:
                # German only
                if lang_id != '1':
                    continue

                # Check against blocked hoster list
                if any(h and h.lower() in provider_name.lower() for h in hostblockDict):
                    continue

                compound_url = play_url + '|||' + ep_full_url
                sources.append({
                    'source': provider_name,
                    'quality': '720p',
                    'url': compound_url,
                    'direct': True,
                    'language': 'de'
                })

            return sources
        except Exception as e:
            log_utils.log('SerienStream run error: %s' % e, log_utils.LOGERROR)
            return sources

    def _get_session(self, referer):
        """Return a logged-in requests session, reusing across resolve() calls."""
        if self._session is not None:
            self._session.headers.update({'Referer': referer})
            return self._session

        import requests as req
        req.packages.urllib3.disable_warnings()

        username = getSetting('serienstream.user')
        password = getSetting('serienstream.pass')

        session = req.Session()
        session.headers.update({
            'User-Agent': cRequestHandler.RandomUA(),
            'Referer': referer,
            'Upgrade-Insecure-Requests': '1'
        })
        session.verify = False

        login_url = self.base_link + '/login'
        session.post(login_url, data={'email': username, 'password': password}, timeout=5)
        log_utils.log('SerienStream: login done, cookies=%d' % len(session.cookies), log_utils.LOGWARNING)

        self._session = session
        return session

    def resolve(self, url):
        try:
            # Parse compound URL (play_url|||referer)
            parts = url.split('|||')
            play_url = parts[0]
            referer = parts[1] if len(parts) > 1 else self.base_link
            log_utils.log('SerienStream resolve: play_url=%s referer=%s' % (play_url, referer), log_utils.LOGWARNING)

            full_play_url = play_url if play_url.startswith('http') else self.base_link + play_url

            # Follow play URL; retry once with fresh login if session expired
            for attempt in range(2):
                session = self._get_session(referer)
                r = session.get(full_play_url, timeout=5)
                sUrl = r.url
                # Session expired — got redirected back to s.to (login page etc.)
                if self.domain in urlparse(sUrl).hostname:
                    log_utils.log('SerienStream resolve: session expired, re-login (attempt %d)' % (attempt + 1), log_utils.LOGWARNING)
                    self._session = None
                    continue
                break
            else:
                log_utils.log('SerienStream resolve: login failed after retry', log_utils.LOGWARNING)
                return None

            log_utils.log('SerienStream resolve: final URL=%s' % sUrl, log_utils.LOGWARNING)

            # Resolve hoster URL via resolveurl to get direct stream URL
            # (done here so sourcesResolve with direct=True skips its own resolve call,
            #  which hangs in the background thread without respecting the deadline)
            hostname = urlparse(sUrl).hostname

            # VOE pseudo-domain normalization: unknown VOE domains → voe.sx
            if hostname and 'voe' in hostname.lower():
                isBlocked, sDomain, sCleanUrl, prioHoster = isBlockedHoster(sUrl, isResolve=False)
                if isBlocked:
                    sUrl = sUrl.replace(hostname, 'voe.sx')
                    log_utils.log('SerienStream resolve: VOE normalized to %s' % sUrl, log_utils.LOGWARNING)

            try:
                import resolveurl
                hmf = resolveurl.HostedMediaFile(url=sUrl, include_disabled=True, include_universal=False)
                if hmf.valid_url():
                    resolved = hmf.resolve()
                    if resolved:
                        log_utils.log('SerienStream resolve: resolveurl -> %s' % resolved, log_utils.LOGWARNING)
                        return resolved
            except Exception as e:
                log_utils.log('SerienStream resolve: resolveurl failed: %s' % e, log_utils.LOGWARNING)

            return sUrl
        except Exception as e:
            log_utils.log('SerienStream resolve error: %s' % e, log_utils.LOGERROR)
            return None

# -*- coding: utf-8 -*-

from .common import *


class clientMaster():
	def __init__(self, *args, **kwargs):
		super(clientMaster, self).__init__()
		self.expire_public = 3595 # max. Token-Time (Seconds) before clear the Token and delete Token-File [3595 = 60 Minutes]
		self.tempSTORE = tempSTORE
		self.savePUBLIC = publicSECRET

	def main_menu(self):
		for title, action in[(30601, {'mode': 'list_favorites'}), (30602, {'mode': 'list_series', 'link': AURA_HOME, 'marker': 'news_Series', 'phase': 'aktuelle highlights'}),
			(30603, {'mode': 'list_episodes', 'link': AURA_HOME, 'marker': 'news_Episodes', 'phase': 'aktuelle highlights'}),
			(30604, {'mode': 'list_series', 'link': AURA_HOME, 'marker': 'last_Chance', 'phase': 'noch kurze zeit online'}),
			(30605, {'mode': 'list_themes'}), (30606, {'mode': 'list_alphabet', 'link': AURA_NORM, 'phase': 'sendungen'}),
			(30607,{'mode': 'list_series', 'link': AURA_NORM, 'marker': 'revise_Series', 'phase': 'sendungen'})]:
			self.add_views(action, create_entries({'Title': translation(title), 'Image': f"{artpic}favourites.png" if title == 30601 else icon}))
		if enable_tune:
			self.add_views({'mode': 'antuning'}, create_entries({'Title': translation(30608), 'Image': f"{artpic}settings.png"}), False)
			if plugin_operate('inputstream.adaptive'):
				self.add_views({'mode': 'ietuning'}, create_entries({'Title': translation(30609), 'Image': f"{artpic}settings.png"}), False)
		xbmcplugin.endOfDirectory(ADDON_HANDLE)

	def list_themes(self):
		debug_MS("(navigator.list_themes) ------------------------------------------------ START = list_themes -----------------------------------------------")
		for item in [{'name': 'Alaska', 'slug': 'alaska'},{'name': 'Alltagshelden', 'slug': 'alltagshelden'},{'name': 'Auktion', 'slug': 'auction'},
			{'name': 'Australien', 'slug': 'australien'},{'name': 'Blaulicht', 'slug': 'blaulicht'},{'name': 'Camping', 'slug': 'camping'},
			{'name': 'Crime', 'slug': 'crime'},{'name': 'DMAX Originals', 'slug': 'dmax-originals'},{'name': 'Fisch und Meer', 'slug': 'fisch-und-meer'},
			{'name': 'Gold', 'slug': 'gold'},{'name': 'Handwerk', 'slug': 'tool-time'},{'name': 'Jobs', 'slug': 'jobs'},{'name': 'Monster & Aliens', 'slug': 'monster-aliens'},
			{'name': 'Polizei', 'slug': 'police'},{'name': 'Reisen', 'slug': 'reisen'},{'name': 'Schatzsucher', 'slug': 'schatzsucher'},
			{'name': 'Survival', 'slug': 'survival'},{'name': 'Traumautos', 'slug': 'traumautos'},{'name': 'Trucks', 'slug': 'motors'},{'name': 'Wissen', 'slug': 'wissen'}]:
			FETCH_UNO = create_entries({'Title': item['name'], 'Image': f"{artpic}standard.png"})
			self.add_views({'mode': 'list_series', 'link': AURA_SEARCH.format(item['slug']), 'marker': 'revise_Themes', 'phase': 'taxonomies'}, FETCH_UNO)
			debug_MS(f"(navigator.list_themes[1]) ##### NAME : {item['name']} || SLUG : {item['slug']} #####")
		xbmcplugin.endOfDirectory(ADDON_HANDLE)

	def list_alphabet(self, target, phase):
		debug_MS("(navigator.list_alphabet) ------------------------------------------------ START = list_alphabet -----------------------------------------------")
		UNIKAT, letters = set(), ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
		for block in self.track_content(target).get('blocks', []):
			if re.sub(r'([^\w\s]|_)', '', block.get('title', 'unknown').lower()).endswith(phase): # Entferne alles ausser Wörtern und Leerzeichen = sendungen; sendungen:
				for item in sorted(block.get('items', []), key=lambda fix: fix.get('firstLetter', 'a')[:1]):
					if item.get('pageType') == 'showpage' or item.get('type') == 'showpage' and item.get('firstLetter', '') in letters and item['firstLetter'] not in UNIKAT: # Nach Alphabet filtern
						UNIKAT.add(item['firstLetter'])
						FETCH_UNO = create_entries({'Title': item['firstLetter'].upper(), 'Image': f"{alppic}{item['firstLetter'].upper().replace('#', '0-9')}.jpg"})
						self.add_views({'mode': 'list_series', 'link': AURA_NORM, 'marker': 'revise_Alphabet', 'phase': 'sendungen', 'extra': item['firstLetter']}, FETCH_UNO)
						debug_MS(f"(navigator.list_alphabet[1]) ##### LETTER : {item['firstLetter'].upper()} || LINK : {AURA_NORM} || PHASE : sendungen #####")
		xbmcplugin.endOfDirectory(ADDON_HANDLE)

	def list_series(self, target, marker, phase, extra): # 'revise_Favorites'; 'revise_Series'; 'revise_Themes'; 'revise_Alphabet'; 'news_Series'; 'last_Chance'
		debug_MS("(navigator.list_series) ------------------------------------------------ START = list_series -----------------------------------------------")
		debug_MS(f"(navigator.list_series) ### LINK = {target} ### MARKER = {marker} ### CATEGORY/FILTER = {phase} ### EXTRA = {extra} ###")
		ISOLATE, (COMBI_UNO, COMBI_DUE, COMBI_TRE) = set(), ([] for _ in range(3))
		COMBI_UNO, COMBI_TRE = self.list_aurora(target, marker, phase, extra)
		if marker in ['revise_Favorites', 'news_Series', 'last_Chance']:
			content, serve, adjust = 'publishEnd' if marker == 'last_Chance' else 'publishStart', '2026-01-01T00:01', False if marker == 'last_Chance' else True
			for each_due in sorted(self.fetch_pages(COMBI_UNO), key=lambda asx: asx.get(content, serve)[:16], reverse=adjust):
				ser_slug = each_due.get('auraTicket', {}).get('secCipher', '')
				ser_title = (each_due.get('show', {}).get('title', '') or each_due.get('item', {}).get('show', {}).get('title', '')) # get('show').get('title') oder get('item').get('show').get('title')
				if ser_slug not in ISOLATE: # Nur jeweils einen Teil einer Serie behalten
					ISOLATE.add(ser_slug)
					COMBI_DUE.append([ser_slug, ser_title, each_due])
		if COMBI_TRE:
			if marker in ['revise_Series', 'revise_Themes', 'revise_Alphabet']: RESULT = COMBI_TRE
			else: RESULT = [av + bv for av in COMBI_DUE for bv in COMBI_TRE if av[0] == bv[2]]
			if marker in ['revise_Favorites', 'revise_Series', 'revise_Themes', 'revise_Alphabet']:
				RESULT = sorted(RESULT, key=lambda vox: clear_umlaut(vox[1]))
			for xev in RESULT:
				debug_MS("---------------------------------------------")
				debug_MS(f"(navigator.list_series[2]) ##### Anzahl : {len(xev)} || Eintrag : {xev} #####")
				if len(xev) >= 11 : ### Liste1+Liste2 ist gleich Nummer:12 ###
					SeriesSlug1, SeriesTitle1, riders, operation = xev[0], xev[1], xev[2], 'adding'
					counter, SeriesTitle2, full_name, SeriesSlug2, parent, idd, infos, thumb, cover, plot = xev[3], xev[4], xev[4], xev[5], xev[6], xev[7], xev[8],  xev[9], xev[10], xev[11]
				elif len(xev) == 9:
					SeriesSlug1, SeriesTitle1, riders, operation = None, None, {}, 'adding'
					counter, SeriesTitle2, full_name, SeriesSlug2, parent, idd, infos, thumb, cover, plot = xev[0], xev[1], xev[1], xev[2], xev[3], xev[4], xev[5], xev[6], xev[7], xev[8]
				if isinstance(riders, (dict, list)) and str(riders.get('auraTicket', {}).get('secPoints', '')).isdecimal():
					full_name = translation(30620).format(full_name, riders.get('auraTicket', {}).get('secPoints'))
				if marker == 'last_Chance' and isinstance(riders, (dict, list)) and str(riders.get('publishEnd'))[:4].isdecimal():
					if convert_region(riders.get('publishEnd')) > (datetime.now() + timedelta(days=7, hours=2)): continue # Plus 7 Tage und 2 Stunden (LOCAL-Zeit)
					elif convert_region(riders.get('publishEnd')) < (datetime.now() + timedelta(days=7, hours=2)):
						full_name = translation(30621).format(full_name)
				if marker == 'news_Series' and isinstance(riders, (dict, list)) and str(riders.get('publishStart'))[:4].isdecimal():
					if convert_region(riders.get('publishStart')) < (datetime.now() - timedelta(days=7, hours=2)): continue # Minus 7 Tage und 2 Stunden (LOCAL-Zeit)
				if marker in ['revise_Favorites', 'news_Series'] and isinstance(riders, (dict, list)) and str(riders.get('publishStart'))[:4].isdecimal():
					if convert_region(riders.get('publishStart')) > (datetime.now() - timedelta(days=7, hours=2)):
						full_name = translation(30622).format(full_name)
				if marker != 'revise_Favorites' and preserve(FAVORIT_FILE) is not None:
					for present in preserve(FAVORIT_FILE):
						if present.get('Code') == idd or present.get('Slug') == SeriesSlug2: operation = 'skipping'
				elif marker == 'revise_Favorites': operation = 'removing'
				debug_MS(f"(navigator.list_series[2]) ##### NAME : {SeriesTitle2} || SER_CODE : {idd} || SER_SLUG : {SeriesSlug2} || THUMB : {thumb if thumb else cover} || FAV_HANDLE : {operation} #####")
				FETCH_UNO = context = {'Code': idd, 'Slug': SeriesSlug2, 'Clearname': SeriesTitle2, 'Title': full_name, 'Plot': plot, 'Image': thumb, 'Cover': cover}
				self.add_views({'mode': 'list_episodes', 'link': AURA_VIDEOS.format(SeriesSlug2), 'marker': marker, 'phase': phase, 'show': SeriesTitle2}, create_entries(FETCH_UNO), True, context, operation)
		xbmcplugin.endOfDirectory(ADDON_HANDLE)

	def list_episodes(self, target, marker, phase, tvshow): # 'news_Episodes'
		debug_MS("(navigator.list_episodes) ------------------------------------------------ START = list_episodes -----------------------------------------------")
		debug_MS(f"(navigator.list_episodes) ### LINK = {target} ### MARKER = {marker} ### CATEGORY/FILTER = {phase} ### SHOW = {tvshow} ###")
		ISOLATE, (COMBI_UNO, COMBI_DUE, COMBI_TRE) = set(), ([] for _ in range(3))
		if marker == 'news_Episodes':
			COMBI_UNO, COMBI_TRE = self.list_aurora(target, marker, phase, "")
			for each_due in sorted(self.fetch_pages(COMBI_UNO), key=lambda asx: asx.get('publishStart', '2026-01-01T00:01')[:16], reverse=True):
				ser_slug = each_due.get('auraTicket', {}).get('secCipher', '')
				ser_title = (each_due.get('show', {}).get('title', '') or each_due.get('item', {}).get('show', {}).get('title', '')) # get('show').get('title') oder get('item').get('show').get('title')
				if ser_slug not in ISOLATE: # Nur jeweils einen Teil einer Serie behalten
					ISOLATE.add(ser_slug)
					COMBI_DUE.append({'SeriesSlug': ser_slug, 'SeriesTitle': ser_title, 'Contents': each_due})
		else:
			packs = self.track_content(target, headers=DEFAULT_HEADERS)
			if packs is not None and packs.get('blocks', []) and len(packs['blocks']) > 1 and packs.get('blocks', [])[-1].get('items', {}):
				block_table, genres = packs.get('blocks', {})[-1].get('items', {}), packs.get('blocks', {})[0].get('show', {}).get('taxonomies', {})
				ser_slug, ser_title = packs.get('slug', {}), packs.get('title', {})
				if courses == 0: block_table = sorted(block_table, key=lambda asx: (int(asx.get('seasonNumber', 1)), int(asx.get('episodeNumber', 1))), reverse=True)
				for each_due in block_table:
					each_due['taxonomies'] = genres # Kopiere Taxonomies-Ordner in 2. Ebene zu 'each_due'
					COMBI_DUE.append({'SeriesSlug': ser_slug, 'SeriesTitle': ser_title, 'Contents': each_due})
		if COMBI_DUE:
			debug_MS("---------------------------------------------")
			debug_MS(f"(navigator.list_episodes[2]) XXXXX COMBI_DUE-02 : {COMBI_DUE} XXXXX")
			if courses == 1 and marker != 'news_Episodes':
				for method in get_sorting(): xbmcplugin.addSortMethod(ADDON_HANDLE, method)
			for number, items in enumerate(COMBI_DUE, 1):
				if marker == 'news_Episodes' and str(items.get('Contents', {}).get('publishStart'))[:4].isdecimal():
					if convert_region(items['Contents']['publishStart']) < (datetime.now() - timedelta(days=7, hours=2)): continue # Beiträge älter als 7 Tage ausblenden
				self.add_views({'mode': 'play_video', 'url': items.get('Contents', {}).get('id')}, create_entries(items, 'COLLATE', number), False)
		else:
			message = 'Neue Sendungen' if marker == 'news_Episodes' else tvshow
			failing(f'(navigator.list_episodes) ##### NO EPISODES-LIST - NO ENTRY FOR: "{message}" FOUND #####')
			return dialog.notification(translation(30525), translation(30526).format(message), icon, 10000)
		xbmcplugin.endOfDirectory(ADDON_HANDLE)

	def list_aurora(self, target, marker, phase, extra):
		UNIKAT, (COMBI_AURO, COMBI_LINKS) = set(), ([] for _ in range(2))
		mediathek = self.track_content(target, headers=DEFAULT_HEADERS)
		block_table = mediathek.get('blocks', []) if 'blocks' in mediathek and isinstance(mediathek.get('blocks', []), list) else [mediathek]
		for block in block_table:
			if re.sub(r'([^\w\s]|_)', '', block.get('title', 'unknown').lower()).endswith(phase) or marker == 'revise_Themes': # Entferne alles ausser Wörtern und Leerzeichen = aktuelle highlights; neue folgen online sehen:; noch kurze zeit online; sendungen; sendungen:
				post_table = block.get('data', []) if marker == 'revise_Themes' else block.get('items', [])
				for num, each_uno in enumerate(post_table, 1):
					if each_uno.get('pageType') == 'showpage' or each_uno.get('type') in ['showpage', 'video']:
						teaser, (photo, portrait) = "", (None for _ in range(2))
						title = each_uno['title']
						showSlug = (each_uno.get('slug', None) or each_uno.get('url', None))
						if showSlug is None and each_uno.get('show', {}).get('title', ''):
							title, showSlug = cleaning(each_uno['show']['title']), clear_invalid(each_uno['show']['title']).lower()
						parentSlug = (each_uno.get('parentSlug', '') or each_uno.get('parentUrl', '') or each_uno.get('parentPage', {}).get('slug', ''))
						showID = (each_uno.get('attributes', {}).get('showId', '') or each_uno.get('show', {}).get('id', '') or each_uno.get('showId', '') or None)
						infos = (each_uno.get('attributes', {}).get('tuneinInfo', '') or each_uno.get('tuneinInfo', ''))
						if (showSlug is None and showID is None) or (marker == 'revise_Themes' and parentSlug == 'mediathek'): continue # Teilweise sind in den Genre-Shows Titel von Tele5 enthalten ('parentSlug'='mediathek')
						if marker == 'revise_Alphabet' and each_uno.get('firstLetter', '') != extra: continue # Nach Alphabet filtern
						if marker == 'revise_Favorites':
							match = [ics for ics in extra if ics.get('Code') == showID or ics.get('Slug') == showSlug]
							if not match: continue # Nach vorhandenen Favoriten filtern
						if 'NUR IM TV' not in infos.upper() and showSlug not in UNIKAT:
							UNIKAT.add(showSlug)
							debug_MS("* * * * * * * * * * * * * * * * * * * * * * *")
							debug_MS(f"(navigator.list_aurora[1]) xxxxx POSITION-01 : {num} || EACH-01 : {each_uno} xxxxx")
							if each_uno.get('metaMedia', '') and len(each_uno['metaMedia']) > 0:
								photo = [pox.get('media', {}).get('url', '') for pox in each_uno.get('metaMedia') if pox.get('role') == 'default'][0]
								portrait = [ptx.get('media', {}).get('url', '') for ptx in each_uno.get('metaMedia') if ptx.get('role') == 'preview'][0]
							if portrait is None and each_uno.get('image', '') and each_uno['image'].get('url', ''):
								portrait = each_uno['image']['url']
							if portrait is None and each_uno.get('poster', '') and each_uno['poster'].get('src', ''):
								photo = each_uno['poster']['src']
							if each_uno.get('articleContent', '') and len(each_uno['articleContent']) > 20:
								teaser = cleaning(each_uno['articleContent'])
							if marker in ['revise_Favorites', 'news_Series', 'news_Episodes', 'last_Chance']: 
								COMBI_LINKS.append([int(num), showSlug, AURA_VIDEOS.format(showSlug.lower())])
							COMBI_AURO.append([int(num), title, showSlug, parentSlug, showID, infos, photo, portrait, teaser])
		return COMBI_LINKS, COMBI_AURO

	def play_video(self, video_id):
		debug_MS("(navigator.play_video) ------------------------------------------------ START = play_video -----------------------------------------------")
		debug_MS(f"(navigator.play_video) ### LINK = {AURA_PLAYER} ### PLID = {video_id} ###")
		STREAM, FINAL_URL, DRM_GUARD, DRM_SPECIES = (False for _ in range(4))
		coident = self.check_authtoken()
		payload = {'deviceInfo': {'adBlocker': False, 'drmSupported': True, 'hdrCapabilities': [], 'hwDecodingCapabilities': [], 'soundCapabilities': []}, 'wisteriaProperties': {}, 'videoId': str(video_id)}
		package = self.track_content(AURA_PLAYER, 'POST', 'JSON', {**STONE_HEADERS, **{'Authorization': f"Bearer {coident}"}}, data=json.dumps(payload, indent=2))
		for riders in package['data']['attributes']['streaming']:
			if riders.get('protection', {}).get('drmEnabled', False) is True and riders.get('type') =='dash':
				STREAM, MIME, FINAL_URL = 'MPD', 'application/dash+xml', riders['url']
				DRM_GUARD, DRM_TOKEN = riders['protection']['schemes']['widevine']['licenseUrl'], riders['protection']['drmToken']
				debug_MS("(navigator.play_video[1]) ***** TAKE - Inputstream (mpd) - FILE *****")
			if FINAL_URL is False and riders.get('type') == 'hls':
				STREAM, MIME, FINAL_URL = 'HLS', 'application/vnd.apple.mpegurl', riders['url']
				debug_MS("(navigator.play_video[1]) ***** TAKE - Inputstream (hls) - FILE *****")
		if FINAL_URL and STREAM and plugin_operate('inputstream.adaptive'):
			LPM = xbmcgui.ListItem(path=FINAL_URL, offscreen=True)
			IA_NAME, IA_SYSTEM = 'inputstream.adaptive', 'com.widevine.alpha'
			IA_VERSION = re.sub(r'(~[a-z]+(?:.[0-9]+)?|\+[a-z]+(?:.[0-9]+)?$|[.^]+)', '', xbmcaddon.Addon(IA_NAME).getAddonInfo('version'))[:4]
			DRM_HEADERS = {'PreAuthorization': DRM_TOKEN, 'Content-Type': 'application/octet-stream', 'User-Agent': HEAD_WEB} if DRM_GUARD else {}
			LPM.setMimeType(MIME); LPM.setProperty('inputstream', IA_NAME)
			if KODI_BUILD in [19, 20]: LPM.setProperty(f"{IA_NAME}.manifest_type", STREAM.lower()) # DEPRECATED ON Kodi v21, because the manifest type is now auto-detected.
			PHRASE = 'stream' if KODI_BUILD == 19 else 'manifest' if KODI_BUILD in [20, 21] else 'common'
			LPM.setProperty(f"{IA_NAME}.{PHRASE}_headers", f"User-Agent={HEAD_WEB}") # 'stream_headers' ON KODI v19 // 'manifest_headers' ON KODI v20 and v21 // 'common_headers' ON KODI v22 and above
			if int(IA_VERSION) >= 2150 and STREAM in ['HLS', 'MPD']:
				DRM_SPECIES = {'DRM_System': 'org.w3.clearkey'} if STREAM == 'HLS' else {'DRM_System': IA_SYSTEM}
				if STREAM == 'MPD' and DRM_GUARD:
					DRM_SPECIES = {'DRM_System': IA_SYSTEM, 'License_Link': DRM_GUARD, 'License_Headers': urlencode(DRM_HEADERS)}
				LPM.setProperty(f"{IA_NAME}.drm_legacy", '|'.join(DRM_SPECIES.values())) # Available from v.21.5.0 / Kodi 21 (Omega) - NEW simple method to configure a single DRM
			elif int(IA_VERSION) < 2150 and STREAM == 'MPD':
				LPM.setProperty(f"{IA_NAME}.license_type", IA_SYSTEM)
				if DRM_GUARD:
					DRM_SPECIES = {'License_Link': DRM_GUARD, 'License_Headers': urlencode(DRM_HEADERS), 'Post_Data': 'R{SSM}|'}
					LPM.setProperty(f"{IA_NAME}.license_key", '|'.join(DRM_SPECIES.values())) # Below v.21.5.0 / Kodi 19+20 - OLD method to configure a single DRM
			if DRM_SPECIES: log(f"(navigator.play_video[2]) INPUTSTREAM_VERSION: {IA_VERSION} >>>>> LICENSE : {'|'.join(DRM_SPECIES.values())} <<<<<")
			log(f"(navigator.play_video) {STREAM}_stream : {FINAL_URL}|User-Agent={HEAD_WEB}")
			from .player import discoMaster
			discoMaster().start_signal(LPM)
		else:
			failing(f"(navigator.play_video) ##### Abspielen des Streams NICHT möglich ##### PLID : {video_id} #####\n ########## KEINEN Stream-Eintrag gefunden !!! ##########")
			xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
			xbmc.PlayList(1).clear()
			return dialog.notification(translation(30521).format('PLAYER'), translation(30527), icon, 10000)

	def fetch_pages(self, templates):
		package = self.track_several(templates, 'GET', timeout=20)
		if package:
			combies = json.loads(package)
			for article in combies:
				if article is not None and article.get('blocks', []) and len(article['blocks']) > 1 and article.get('blocks', {})[-1].get('items', {}):
					number, codes, points, genres = article.get('Position', 0), article.get('NaviCode', 'unknown'), len(article.get('blocks', {})[-1].get('items', {})), article.get('blocks', {})[0].get('show', {}).get('taxonomies', {})
					for scraps in article.get('blocks', {})[-1].get('items', {}):
						seconds = (scraps.get('videoDuration', '') or scraps.get('item', {}).get('videoDuration', ''))
						if not str(seconds).isdecimal() or codes == 'unknown': continue # get('videoDuration) oder get('item).get('videoDuration) für Series
						scraps['taxonomies'] = genres # Kopiere Taxonomies-Ordner in 2. Ebene zu 'scraps'
						embrace = {**scraps, **{'auraTicket': {'secCount': number, 'secCipher': codes, 'secPoints': points}}}
						yield embrace

	def track_content(self, url, method='GET', queries='JSON', headers={}, redirects=True, data=None, json=None, timeout=30):
		attempts, ANSWER, headers = 0, None, {**headers, **{'User-Agent': HEAD_WEB}}
		while not ANSWER and attempts < 2: # 2 x Pingversuche für den Request ::: zur Überprüfung der Verfügbarkeit der URL
			attempts += 1
			try:
				response = requests.request(method, url, headers=headers, allow_redirects=redirects, data=data, json=json, timeout=timeout)
				ANSWER = response.json() if queries == 'JSON' else response.text if queries == 'TEXT' else response
				debug_MS(f"(navigator.track_content) === CALLBACK === STATUS : {response.status_code} || URL : {response.url} || HEADER : {response.request.headers} || DATA : {data} ===")
				if queries == 'JSON' and not isinstance(ANSWER, list) and ANSWER.get('errors', {}):
					message = (ANSWER.get('errors', {})[0].get('detail', '') or 'NO DETAILS FOUND')
					failing(f"(navigator.track_content) ERROR - RESPONSE - ERROR ##### URL : {url} === DETAILS : {message} #####")
					dialog.notification(translation(30521).format('URL'), translation(30523).format(message), icon, 12000)
					return sys.exit(0)
				response.raise_for_status()
			except Exception as exc: # No JSON object could be decoded
				failing(f"(navigator.track_content) ERROR - EXEPTION - ERROR ##### URL : {url} === FAILURE : {exc} #####")
				dialog.notification(translation(30521).format('URL'), translation(30523).format(exc), icon, 12000)
				time.sleep(2)
				if attempts >= 2: return sys.exit(0)
		return ANSWER

	def track_several(self, stacks, method='GET', queries='JSON', redirects=True, timeout=5, workers=20):
		COMBI_NEW, number, counter, fixation, = [], len(stacks), 0, requests.Session()
		fixation.mount('https://', HTTPAdapter(pool_connections=int(number), pool_maxsize=int(number), pool_block=True)) # Pool-Verbindungen und -Grösse auf tatsächlichen Inhalt festlegen, um Fehlermeldungen zu vermeiden
		def download(pos, code, link, coident):
			heading = {**STONE_HEADERS, **{'User-Agent': HEAD_WEB, 'Authorization': f"Bearer {coident}"}}
			try:
				response = fixation.request(method, link, headers=heading, allow_redirects=redirects, timeout=timeout)
				response.raise_for_status()
				debug_MS(f"(navigator.track_several[1]) === POS : {pos} || STATUS : {response.status_code} || URL : {response.url} || HEADER : {response.request.headers} ===")
				return f'{{"Position":{pos},"NaviCode":"{code}","Demand":"{link}",{response.text[1:-1]}}}'
			except Exception as exc_uno:
				failing(f"(navigator.track_several[1]) ERROR - RESPONSE - ERROR ##### POS : {pos} === URL : {link} === FAILURE : {exc_uno} #####")
				return f'{{"Position":{pos},"Status":"ERROR"}}'
		with ThreadPoolExecutor(max_workers=workers) as executor:
			debug_MS("+++++++++++++++++++++++++++++++++++++++++++++")
			coident = self.check_authtoken()
			picker = [executor.submit(download, pos, code, link, coident) for pos, code, link in stacks]
			wait(picker, timeout=30, return_when=ALL_COMPLETED)
			for future, section in zip(as_completed(picker), stacks):
				counter += 1
				try:
					COMBI_NEW.append(json.loads(future.result()))
				except Exception as exc_due:
					if counter == 1: dialog.notification(translation(30521).format('DETAILS'), translation(30523).format(exc_due), f"{artpic}icon.png", 12000)
					failing(f"(navigator.track_several[2]) ERROR - EXEPTION - ERROR ##### POS : {section[0]} === URL : {section[2]} === FAILURE : {exc_due} #####")
					executor.shutdown()
			if COMBI_NEW:
				matching = [flop for flop in COMBI_NEW[:] if flop.get('Status', 'OOKAY') == 'ERROR']
				if len(matching) == number or len(matching) > 6:
					dialog.notification(translation(30521).format('DETAILS'), translation(30524), f"{artpic}icon.png", 12000)
		return json.dumps(COMBI_NEW, indent=2)

	def convert_epoch(self, epoch):
		CIPHER = datetime(1970,1,1) + timedelta(seconds=int(epoch))
		return CIPHER.strftime('%d.%m.%Y - %H:%M:%S')

	def check_authtoken(self):
		CODING, forceRenew, SWITCH = False, False, None
		GUARDIA, SECURITY, self.TIME_UTC = self.tempSTORE, self.savePUBLIC, time.time()
		if SECURITY is not None and os.path.isfile(SECURITY):
			try:
				self.TOKEN_UTC = (os.path.getmtime(SECURITY) + self.expire_public)
				debug_MS(f"(navigator.check_authtoken) ### SESSION-Time (utc NOW) = {self.convert_epoch(self.TIME_UTC)} || VALID until (utc SESSION) = {self.convert_epoch(self.TOKEN_UTC)} ###")
				if self.TIME_UTC < self.TOKEN_UTC and preserve(SECURITY) is not None:
					SWITCH = preserve(SECURITY)['data']['attributes']['token']
					debug_MS("(navigator.check_authtoken) ### NOTHING CHANGED - TOKENFILE IS OKAY ###")
				else:
					debug_MS("(navigator.check_authtoken) ### TIMEOUT FOR TOKEN - DELETE TOKENFILE ###")
					forceRenew = True
			except:
				failing("(navigator.check_authtoken) XXXXX !!! ERROR = TOKENFILE [TOKENFORMAT IS INVALID] = ERROR !!! XXXXX")
				forceRenew = True
		else:
			debug_MS("(navigator.check_authtoken) ### NOTHING FOUND - CREATE TOKENFILE FOR DISCOVERY ###")
			forceRenew = True
		if forceRenew:
			if SECURITY is not None and os.path.isfile(SECURITY):
				shutil.rmtree(GUARDIA, ignore_errors=True)
			CODING = self.track_content(AURA_ACCESS, headers=STONE_HEADERS)
			if CODING:
				debug_MS(f"(navigator.check_authtoken) ***** NEW TOKENFILE CREATED : {CODING} *****")
				if not xbmcvfs.exists(GUARDIA) and not os.path.isdir(GUARDIA):
					xbmcvfs.mkdirs(GUARDIA)
				preserve(SECURITY, CODING)
				SWITCH = CODING['data']['attributes']['token']
		return SWITCH

	def list_favorites(self, WATCHING=[]):
		debug_MS("(navigator.list_favorites) ------------------------------------------------ START = list_favorites -----------------------------------------------")
		if preserve(FAVORIT_FILE) is not None:
			for each in preserve(FAVORIT_FILE): # Liste alle Favoriten - gehe direkt zum 'list_series' Ordner
				debug_MS(f"(navigator.list_favorites[1]) ##### NAME : {each.get('Clearname')} || CODE : {each.get('Code')} || SLUG : {each.get('Slug')} || IMAGE : {(each.get('Cover') or each.get('Image'))} #####")
				WATCHING.append({'Code': each.get('Code'), 'Slug': each.get('Slug'), 'Title': each.get('Clearname'), 'Plot': each.get('Plot')})
			if WATCHING:
				return self.list_series(AURA_NORM, 'revise_Favorites', 'sendungen', WATCHING)
		return dialog.notification(translation(30528), translation(30529), icon, 8000)

	def favorit_construct(self, **kwargs):
		TOPS = []
		if preserve(FAVORIT_FILE) is not None:
			TOPS = preserve(FAVORIT_FILE)
		if kwargs['action'] == 'ADD':
			kwargs.pop('mode', None); kwargs.pop('action', None); kwargs.pop('Title', None); kwargs.pop('Genre', None)
			TOPS.append({key: value for key, value in kwargs.items() if value not in ['', 'None', None]})
			preserve(FAVORIT_FILE, TOPS)
			xbmc.sleep(500)
			dialog.notification(translation(30530), translation(30531).format(kwargs['Clearname']), icon, 10000)
		elif kwargs['action'] == 'DEL':
			TOPS = [xs for xs in TOPS if xs.get('Slug') != kwargs.get('Slug')]
			preserve(FAVORIT_FILE, TOPS)
			xbmc.executebuiltin('Container.Refresh')
			xbmc.sleep(1000)
			dialog.notification(translation(30530), translation(30532).format(kwargs['Clearname']), icon, 10000)

	def add_views(self, params, listitem, folder=True, context={}, handling='default'):
		uws, entries = build_mass(params), []
		listitem.setPath(uws)
		if handling == 'adding' and context:
			entries.append([translation(30651), f"RunPlugin({build_mass({**context, **{'mode': 'favorit_construct', 'action': 'ADD'}})})"])
		if handling == 'removing' and context:
			entries.append([translation(30652), f"RunPlugin({build_mass({**context, **{'mode': 'favorit_construct', 'action': 'DEL'}})})"])
		if len(entries) > 0: listitem.addContextMenuItems(entries)
		return xbmcplugin.addDirectoryItem(ADDON_HANDLE, uws, listitem, folder)

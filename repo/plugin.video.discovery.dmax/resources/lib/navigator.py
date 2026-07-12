# -*- coding: utf-8 -*-

from .common import *
from .utilities import clientHelper


def main_menu():
	for title, action in[(30601, {'mode': 'list_favorites'}), (30602, {'mode': 'list_series', 'link': AURA_NORM, 'marker': 'news_Series', 'phase': 'sendungen'}),
		(30603, {'mode': 'list_episodes', 'link': AURA_NORM, 'marker': 'news_Episodes', 'phase': 'sendungen'}),
		(30604, {'mode': 'list_series', 'link': AURA_NORM, 'marker': 'last_Chance', 'phase': 'sendungen'}),
		(30605, {'mode': 'list_themes'}), (30606, {'mode': 'list_alphabet', 'link': AURA_NORM, 'phase': 'sendungen'}),
		(30607,{'mode': 'list_series', 'link': AURA_NORM, 'marker': 'revise_Series', 'phase': 'sendungen'})]:
		add_views(action, create_entries({'Title': translation(title), 'Image': f"{artpic}favourites.png" if title == 30601 else icon}))
	if enable_tune:
		add_views({'mode': 'antuning'}, create_entries({'Title': translation(30608), 'Image': f"{artpic}settings.png"}), False)
		if plugin_operate('inputstream.adaptive'):
			add_views({'mode': 'ietuning'}, create_entries({'Title': translation(30609), 'Image': f"{artpic}settings.png"}), False)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def list_themes():
	debug_MS("(navigator.list_themes) ------------------------------------------------ START = list_themes -----------------------------------------------")
	for item in [{'name': 'Alaska', 'slug': 'alaska'},{'name': 'Alltagshelden', 'slug': 'alltagshelden'},{'name': 'Auktion', 'slug': 'auction'},
		{'name': 'Australien', 'slug': 'australien'},{'name': 'Blaulicht', 'slug': 'blaulicht'},{'name': 'Camping', 'slug': 'camping'},
		{'name': 'Crime', 'slug': 'crime'},{'name': 'DMAX Originals', 'slug': 'dmax-originals'},{'name': 'Fisch und Meer', 'slug': 'fisch-und-meer'},
		{'name': 'Gold', 'slug': 'gold'},{'name': 'Handwerk', 'slug': 'tool-time'},{'name': 'Jobs', 'slug': 'jobs'},{'name': 'Monster & Aliens', 'slug': 'monster-aliens'},
		{'name': 'Polizei', 'slug': 'police'},{'name': 'Reisen', 'slug': 'reisen'},{'name': 'Schatzsucher', 'slug': 'schatzsucher'},
		{'name': 'Survival', 'slug': 'survival'},{'name': 'Traumautos', 'slug': 'traumautos'},{'name': 'Trucks', 'slug': 'motors'},{'name': 'Wissen', 'slug': 'wissen'}]:
		fetch_items = create_entries({'Title': item['name'], 'Image': f"{artpic}standard.png"})
		add_views({'mode': 'list_series', 'link': AURA_SEARCH.format(item['slug']), 'marker': 'revise_Themes', 'phase': 'taxonomies'}, fetch_items)
		debug_MS(f"(navigator.list_themes[1]) ##### NAME : {item['name']} || SLUG : {item['slug']} #####")
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def list_alphabet(target, phase):
	debug_MS("(navigator.list_alphabet) ------------------------------------------------ START = list_alphabet -----------------------------------------------")
	unikat, letters = set(), ['#', 'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z']
	for block in clientHelper().track_content(target, headers=DEFAULT_HEADERS).get('blocks', []):
		if re.sub(r'([^\w\s]|_)', '', block.get('title', 'unknown').lower()).endswith(phase): # Entferne alles ausser Wörtern und Leerzeichen = sendungen; sendungen:
			for item in sorted(block.get('items', []), key=lambda fix: fix.get('firstLetter', 'a')[:1]):
				if item.get('pageType') == 'showpage' or item.get('type') == 'showpage' and item.get('firstLetter', '') in letters and item['firstLetter'] not in unikat: # Nach Alphabet filtern
					unikat.add(item['firstLetter'])
					fetch_items = create_entries({'Title': item['firstLetter'].upper(), 'Image': f"{alppic}{item['firstLetter'].upper().replace('#', '0-9')}.jpg"})
					add_views({'mode': 'list_series', 'link': AURA_NORM, 'marker': 'revise_Alphabet', 'phase': 'sendungen', 'extra': item['firstLetter']}, fetch_items)
					debug_MS(f"(navigator.list_alphabet[1]) ##### LETTER : {item['firstLetter'].upper()} || LINK : {AURA_NORM} || PHASE : sendungen #####")
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def list_series(target, marker, phase, extra): # 'revise_Favorites'; 'revise_Series'; 'revise_Themes'; 'revise_Alphabet'; 'news_Series'; 'last_Chance'
	debug_MS("(navigator.list_series) ------------------------------------------------ START = list_series -----------------------------------------------")
	debug_MS(f"(navigator.list_series) ### LINK = {target} ### MARKER = {marker} ### CATEGORY/FILTER = {phase} ### EXTRA = {extra} ###")
	isolate, merging, (combo_links, combo_uno, combo_due) = set(), {}, ([] for _ in range(3))
	combo_links, combo_uno = _fetch_aurora(target, marker, phase, extra)
	content, serve, adjust = 'publishEnd' if marker == 'last_Chance' else 'publishStart', '2026-01-01T00:01', False if marker == 'last_Chance' else True
	if marker in ['revise_Favorites', 'news_Series', 'last_Chance']:
		for each_due in sorted(_fetch_pages(combo_links), key=lambda asx: asx.get(content, serve)[:16], reverse=adjust):
			if each_due.get('Slug_2', None) not in isolate: # Nur jeweils einen Teil einer Serie behalten
				isolate.add(each_due['Slug_2'])
				combo_due.append(each_due)
	if combo_uno:
		merging = [{**uno, **next(iter([due for due in combo_due if due.get('Slug_2') == uno.get('Slug_1')]), {})} for uno in combo_uno] # Merge List1 and List2 (dictionaries) by specific value if value exists else only List1 !!!
		if merging: # https://stackoverflow.com/questions/56658669/combine-two-lists-of-dictionaries-by-value-of-key-in-dictionaries
			if marker in ['revise_Favorites', 'revise_Series', 'revise_Themes', 'revise_Alphabet']:
				merging = sorted(merging, key=lambda vox: clear_umlaut(vox.get('ShowTitle', 'zorro')).lower())
			else: merging = sorted(merging, key=lambda vox: vox.get(content, serve)[:16], reverse=adjust)
			for shows in merging:
				debug_MS("---------------------------------------------")
				debug_MS(f"(navigator.list_series[2]) ##### Anzahl : {len(shows)} || Eintrag : {shows} #####") # Keine neuen Serien oder Letzte Chance vorhanden wenn Liste2 fehlt !
				if (marker in ['news_Series', 'last_Chance'] and len(shows) < 13) or len(shows) < 10: continue ### Liste1+Liste2 ist gleich Nummer:32 // Liste1 separat ist gleich Nummer:10 ###
				full_name = translation(30620).format(shows['ShowTitle'], shows['TotalTracks']) if str(shows.get('TotalTracks')).isdecimal() else shows['ShowTitle']
				if marker == 'last_Chance' and str(shows.get('publishEnd'))[:4].isdecimal():
					if convert_region(shows.get('publishEnd')) > (datetime.now() + timedelta(days=7, hours=2)): continue # Plus 7 Tage und 2 Stunden (LOCAL-Zeit)
					elif convert_region(shows.get('publishEnd')) < (datetime.now() + timedelta(days=7, hours=2)):
						full_name = translation(30621).format(full_name)
				if marker == 'news_Series' and str(shows.get('publishStart'))[:4].isdecimal():
					if convert_region(shows.get('publishStart')) < (datetime.now() - timedelta(days=7, hours=2)): continue # Minus 7 Tage und 2 Stunden (LOCAL-Zeit)
				if marker in ['revise_Favorites', 'news_Series'] and str(shows.get('publishStart'))[:4].isdecimal():
					if convert_region(shows.get('publishStart')) > (datetime.now() - timedelta(days=7, hours=2)):
						full_name = translation(30622).format(full_name)
				thumb = (shows.get('show', {}).get('image', {}).get('url', None) or shows.get('ShowImage', None))
				if thumb: thumb = CLOUD_ARTS+base64.urlsafe_b64encode(CLOUD_TVIS.replace('{code}', thumb.split('media-de/')[1]).replace('{size}', '1920').encode()).decode()
				poster = (shows.get('show', {}).get('poster', {}).get('url', None) or shows.get('ShowPoster', None))
				if poster: poster = CLOUD_ARTS+base64.urlsafe_b64encode(CLOUD_TVIS.replace('{code}', poster.split('media-de/')[1]).replace('{size}', '500').encode()).decode()
				story = shows['show']['description'] if shows.get('show', {}).get('description', None) else ""
				teaser, operation = cleaning(story) if len(story) > 20 else shows.get('ShowTeaser', ''), 'adding'
				if marker != 'revise_Favorites' and preserve(FAVORIT_FILE) is not None:
					for present in preserve(FAVORIT_FILE):
						if present.get('Code') == shows.get('ShowCID') or present.get('Slug') == shows.get('Slug_1'): operation = 'skipping'
				elif marker == 'revise_Favorites': operation = 'removing'
				debug_MS(f"(navigator.list_series[2]) ##### NAME : {shows['ShowTitle']} || SER_CODE : {shows.get('ShowCID')} || SER_SLUG : {shows.get('Slug_1')} || THUMB : {thumb} || FAV_HANDLE : {operation} #####")
				fetch_items = context = {'Code': shows.get('ShowCID'), 'Slug': shows.get('Slug_1'), 'Clearname': shows['ShowTitle'], 'Title': full_name, 'Plot': teaser, 'Image': thumb, 'Cover': poster}
				add_views({'mode': 'list_episodes', 'link': shows.get('Slug_1'), 'marker': marker, 'phase': phase, 'show': shows['ShowTitle']}, create_entries(fetch_items), True, context, operation)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def list_episodes(target, marker, phase, tvshow): # 'news_Episodes'
	debug_MS("(navigator.list_episodes) ------------------------------------------------ START = list_episodes -----------------------------------------------")
	debug_MS(f"(navigator.list_episodes) ### LINK = {target} ### MARKER = {marker} ### CATEGORY/FILTER = {phase} ### SHOW = {tvshow} ###")
	isolate, found, (combo_links, combo_uno, combo_due) = set(), 0, ([] for _ in range(3))
	if marker == 'news_Episodes':
		combo_links, combo_uno = _fetch_aurora(target, marker, phase, "")
		contents = sorted(_fetch_pages(combo_links), key=lambda asx: asx.get('publishStart', '2026-01-01T00:01')[:16], reverse=True)
	else:
		combo_links.append({'Count_1': int(1), 'Slug_1': target, 'Link_1': AURA_ITEMS.format(target)})
		if courses == 1:
			contents = _fetch_pages(combo_links)
			for method in get_sorting(): xbmcplugin.addSortMethod(ADDON_HANDLE, method)
		else: contents = sorted(_fetch_pages(combo_links), key=lambda asx: (int(asx.get('seasonNumber', 1)), int(asx.get('episodeNumber', 1))), reverse=True)
	for each_due in contents:
		if marker == 'news_Episodes' and str(each_due.get('publishStart'))[:4].isdecimal():
			if convert_region(each_due['publishStart']) < (datetime.now() - timedelta(days=7, hours=2)): continue # Beiträge älter als 7 Tage ausblenden
		if each_due.get('id', None) not in isolate:
			isolate.add(each_due['id'])
			debug_MS("---------------------------------------------")
			counter, found = each_due.get('Count_2'), found.__add__(1)
			debug_MS(f"(navigator.list_episodes[1]) xxxxx COUNT-02 : {counter} || EACH-02 : {each_due} xxxxx")
			fetch_items = create_entries(each_due, 'NEWEST' if marker == 'news_Episodes' else 'COLLECT', counter)
			add_views({'mode': 'play_video', 'url': each_due.get('id')}, fetch_items, False)
	if found == 0:
		message = 'Neue Sendungen' if marker == 'news_Episodes' else tvshow
		failing(f'(navigator.list_episodes) ##### NO EPISODES-LIST - NO ENTRY FOR: "{message}" FOUND #####')
		return dialog.notification(translation(30525), translation(30526).format(message), icon, 10000)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def _fetch_aurora(target, marker, phase, extra):
	unikat, (primodo, secondo) = set(), ([] for _ in range(2))
	mediathek = clientHelper().track_content(target, headers=DEFAULT_HEADERS)
	block_table = mediathek.get('blocks', []) if 'blocks' in mediathek and isinstance(mediathek.get('blocks', []), list) else [mediathek]
	for block in block_table:
		if re.sub(r'([^\w\s]|_)', '', block.get('title', 'unknown').lower()).endswith(phase) or marker == 'revise_Themes': # Entferne alles ausser Wörtern und Leerzeichen = aktuelle highlights; neue folgen online sehen:; noch kurze zeit online; sendungen; sendungen:
			post_table = block.get('data', []) if marker == 'revise_Themes' else block.get('items', [])
			for num, each_uno in enumerate(post_table, 1):
				if each_uno.get('pageType') == 'showpage' or each_uno.get('type') in ['showpage', 'video']:
					teaser, (thumb, cover) = "", (None for _ in range(2))
					title = each_uno['title']
					slug = (each_uno.get('slug', None) or each_uno.get('url', None))
					if slug is None and each_uno.get('show', {}).get('title', ''):
						title, slug = cleaning(each_uno['show']['title']), clear_invalid(each_uno['show']['title']).lower()
					parent = (each_uno.get('parentSlug', '') or each_uno.get('parentUrl', '') or each_uno.get('parentPage', {}).get('slug', ''))
					showCID = (each_uno.get('attributes', {}).get('showId', '') or each_uno.get('show', {}).get('id', '') or each_uno.get('showId', '') or None)
					infos = (each_uno.get('attributes', {}).get('tuneinInfo', '') or each_uno.get('tuneinInfo', ''))
					if (slug is None and showCID is None) or (marker == 'revise_Themes' and parent == 'mediathek'): continue # Teilweise sind in den Genre-Shows Titel von Tele5 enthalten ('parentSlug'='mediathek')
					if marker == 'revise_Alphabet' and each_uno.get('firstLetter', '') != extra: continue # Nach Alphabet filtern
					if marker == 'revise_Favorites':
						match = [ics for ics in extra if ics.get('Code') == showCID or ics.get('Slug') == slug]
						if not match: continue # Nach vorhandenen Favoriten filtern
					if 'NUR IM TV' not in infos.upper() and slug not in unikat:
						unikat.add(slug)
						debug_MS("* * * * * * * * * * * * * * * * * * * * * * *")
						debug_MS(f"(navigator.fetch_aurora[1]) xxxxx COUNT-01 : {num} || EACH-01 : {each_uno} xxxxx")
						if each_uno.get('metaMedia', '') and len(each_uno['metaMedia']) > 0:
							thumb = [pmb.get('media', {}).get('url', None) for pmb in each_uno.get('metaMedia') if pmb.get('role') == 'default'][0]
							cover = [per.get('media', {}).get('url', None) for per in each_uno.get('metaMedia') if per.get('role') == 'preview'][0]
						if cover is None and each_uno.get('image', '') and each_uno['image'].get('url', ''):
							cover = each_uno['image']['url']
						if cover is None and each_uno.get('poster', '') and each_uno['poster'].get('src', ''):
							thumb = each_uno['poster']['src']
						if each_uno.get('articleContent', '') and len(each_uno['articleContent']) > 20:
							teaser = cleaning(each_uno['articleContent'])
						transition = AURA_ITEMS.format(slug.lower())
						if marker in ['revise_Favorites', 'news_Series', 'news_Episodes', 'last_Chance']: 
							primodo.append({'Count_1': int(num), 'Slug_1': slug, 'Link_1': transition})
						secondo.append({'Count_1': int(num), 'Slug_1': slug, 'Link_1': transition, 'ShowTitle': title, 'parentSlug': parent, \
							'ShowCID': showCID, 'Infos': infos, 'ShowImage': thumb, 'ShowPoster': cover, 'ShowTeaser': teaser})
	return primodo, secondo

def _fetch_pages(templates):
	package = clientHelper().track_several(templates, 'GET', timeout=20)
	if package:
		for article in json.loads(package):
			if article is not None and article.get('blocks', []) and len(article['blocks']) > 0 and any(sonic.get('type') in ['sonicShowBlock', 'seoSonicShowBlock'] for sonic in article.get('blocks', {})):
				show_table = next(filter(lambda sox: sox.get('type') == 'showHeaderBlock' and sox.get('show', {}), article['blocks']), None) # Suche nach den Inhalten im 'show' Ordner
				for bodies in article['blocks']:
					if bodies.get('type') in ['sonicShowBlock', 'seoSonicShowBlock'] and bodies.get('items', {}):
						points = len(bodies.get('items', {}))
						for scraps in bodies.get('items', {}):
							if not str(scraps.get('videoDuration')).isdecimal(): continue
							if scraps.get('show', {}) and show_table:
								scraps['show'].update({key: value for key, value in show_table['show'].items() if value not in ['', 'None', None]}) # Kopiere Show-Ordner in 2. Ebene zu 'show'
							scraps.pop('schedule', None); scraps.pop('features', None); scraps.pop('contentDescriptors', None); scraps.pop('package', None)
							embrace = {**scraps, **{'Count_2': article.get('Count_2'), 'Slug_2': article.get('Slug_2'), 'Link_2': article.get('Link_2'), 'TotalTracks': points}}
							yield embrace

def play_video(video_id):
	debug_MS("(navigator.play_video) ------------------------------------------------ START = play_video -----------------------------------------------")
	debug_MS(f"(navigator.play_video) ### LINK = {AURA_PLAYER} ### PLID = {video_id} ###")
	STREAM, FINAL_URL, DRM_GUARD, DRM_SPECIES = (False for _ in range(4))
	payload = {'deviceInfo': {'adBlocker': False, 'drmSupported': True, 'hdrCapabilities': [], 'hwDecodingCapabilities': [], 'soundCapabilities': []}, 'wisteriaProperties': {}, 'videoId': str(video_id)}
	package = clientHelper().track_content(AURA_PLAYER, 'POST', headers=STONE_HEADERS, data=json.dumps(payload, indent=2))
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
		DRM_HEADERS = {'PreAuthorization': DRM_TOKEN, 'Content-Type': 'application/octet-stream', 'User-Agent': WEB_AGENT} if DRM_GUARD else {}
		LPM.setMimeType(MIME); LPM.setProperty('inputstream', IA_NAME)
		if KODI_BUILD in [19, 20]: LPM.setProperty(f"{IA_NAME}.manifest_type", STREAM.lower()) # DEPRECATED ON Kodi v21, because the manifest type is now auto-detected.
		PHRASE = 'stream' if KODI_BUILD == 19 else 'manifest' if KODI_BUILD in [20, 21] else 'common'
		LPM.setProperty(f"{IA_NAME}.{PHRASE}_headers", f"User-Agent={WEB_AGENT}") # 'stream_headers' ON KODI v19 // 'manifest_headers' ON KODI v20 and v21 // 'common_headers' ON KODI v22 and above
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
		log(f"(navigator.play_video) {STREAM}_stream : {FINAL_URL}|User-Agent={WEB_AGENT}")
		from .player import discoMaster
		discoMaster().start_signal(LPM)
	else:
		failing(f"(navigator.play_video) ##### Abspielen des Streams NICHT möglich ##### PLID : {video_id} #####\n ########## KEINEN Stream-Eintrag gefunden !!! ##########")
		xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem())
		xbmc.PlayList(1).clear()
		return dialog.notification(translation(30521).format('PLAYER'), translation(30527), icon, 10000)

def list_favorites(watching=[]):
	debug_MS("(navigator.list_favorites) ------------------------------------------------ START = list_favorites -----------------------------------------------")
	if preserve(FAVORIT_FILE) is not None:
		for each in preserve(FAVORIT_FILE): # Liste alle Favoriten - gehe direkt zum 'list_series' Ordner
			debug_MS(f"(navigator.list_favorites[1]) ##### NAME : {each.get('Clearname')} || CODE : {each.get('Code')} || SLUG : {each.get('Slug')} || IMAGE : {(each.get('Cover') or each.get('Image'))} #####")
			watching.append({'Code': each.get('Code'), 'Slug': each.get('Slug'), 'Title': each.get('Clearname'), 'Plot': each.get('Plot')})
		if watching:
			return list_series(AURA_NORM, 'revise_Favorites', 'sendungen', watching)
	return dialog.notification(translation(30528), translation(30529), icon, 8000)

def favorit_construct(**kwargs):
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

def add_views(params, listitem, folder=True, context={}, handling='default'):
	uws, entries = build_mass(params), []
	listitem.setPath(uws)
	if handling == 'adding' and context:
		entries.append([translation(30651), f"RunPlugin({build_mass({**context, **{'mode': 'favorit_construct', 'action': 'ADD'}})})"])
	if handling == 'removing' and context:
		entries.append([translation(30652), f"RunPlugin({build_mass({**context, **{'mode': 'favorit_construct', 'action': 'DEL'}})})"])
	if len(entries) > 0: listitem.addContextMenuItems(entries)
	return xbmcplugin.addDirectoryItem(ADDON_HANDLE, uws, listitem, folder)

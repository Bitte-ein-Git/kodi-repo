# -*- coding: utf-8 -*-

from .common import *
from .utilities import Transmission


def mainMenu():
	for TITLE, PATH in [(30601, {'mode': 'listFavorites'}), (30602, {'mode': 'listSeries', 'url': f"{EUAPI_SHOWS}&sort=-newestEpisodePublishStart&filter[hasNewEpisodes]=true", 'marker': 'newest_Series'}),
		(30603, {'mode': 'listEpisodes', 'url': f"{EUAPI_VIDEOS}&sort=-earliestPlayableStart&filter[primaryChannel.id]={DISCO_CHANNEL}"}),
		(30604, {'mode': 'listSeries', 'url': f"{EUAPI_SHOWS}&sort=publishEnd&filter[hasExpiringEpisodes]=true", 'marker': 'last_Chance'}),
		(30605, {'mode': 'listThemes'}), (30606, {'mode': 'listAlphabet'}), (30607, {'mode': 'listSeries', 'url': f"{EUAPI_SHOWS}&sort=name", 'marker': 'listing_Series'})]:
		FETCH_UNO = create_entries({'Title': translation(TITLE), 'Image': f"{artpic}favourites.png" if TITLE == 30601 else icon})
		addDir(PATH, FETCH_UNO)
	if enableADJUSTMENT:
		addDir({'mode': 'aConfigs'}, create_entries({'Title': translation(30608), 'Image': f"{artpic}settings.png"}), folder=False)
		if plugin_operate('inputstream.adaptive'):
			addDir({'mode': 'iConfigs'}, create_entries({'Title': translation(30609), 'Image': f"{artpic}settings.png"}), folder=False)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listThemes():
	debug_MS("(navigator.listThemes) ------------------------------------------------ START = listThemes -----------------------------------------------")
	for item in [{'name': 'Alaska', 'slug': 'alaska'},{'name': 'Alltagshelden', 'slug': 'alltagshelden'},{'name': 'Australien', 'slug': 'australien'},{'name': 'Blaulicht', 'slug': 'blaulicht'},
		{'name': 'Camping', 'slug': 'camping'},{'name': 'Crime', 'slug': 'crime'},{'name': 'DMAX Originals', 'slug': 'dmax-originals'},{'name': 'Fisch und Meer', 'slug': 'fisch-und-meer'},
		{'name': 'Gold', 'slug': 'gold'},{'name': 'Handwerk', 'slug': 'tool-time'},{'name': 'Modellbauer', 'slug': 'modellbauer'},{'name': 'Polizei', 'slug': 'police'},
		{'name': 'Reisen', 'slug': 'reisen'},{'name': 'Schatzsucher', 'slug': 'schatzsucher'},{'name': 'Survival', 'slug': 'survival'},{'name': 'Traumautos', 'slug': 'traumautos'},
		{'name': 'Trucks', 'slug': 'motors'},{'name': 'Wissen', 'slug': 'wissen'}]:
		FETCH_UNO = create_entries({'Title': item['name'], 'Image': f"{artpic}standard.png"})
		addDir({'mode': 'listSeries', 'url': f"{EUAPI_SHOWS}&sort=name", 'marker': 'overview_Themes', 'transmit': item['slug']}, FETCH_UNO)
		debug_MS(f"(navigator.listThemes[1]) ##### NAME : {item['name']} || SLUG : {item['slug']} #####")
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listAlphabet():
	debug_MS("(navigator.listAlphabet) ------------------------------------------------ START = listAlphabet -----------------------------------------------")
	for letter in ['0-9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']:
		NEW_URL = f"{EUAPI_SHOWS}&sort=name&filter[name.startsWith]={letter.replace('0-9', '1')}"
		FETCH_UNO = create_entries({'Title': letter, 'Image': f"{alppic}{letter}.jpg"})
		addDir({'mode': 'listSeries', 'url': NEW_URL, 'marker': 'overview_Alphabet'}, FETCH_UNO)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listSeries(TARGET, PAGE, MARKER, FILTER):
	debug_MS("(navigator.listSeries) ------------------------------------------------ START = listSeries -----------------------------------------------")
	debug_MS(f"(navigator.listSeries) ### URL = {TARGET} ### PAGE = {PAGE} ### MARKER = {MARKER} ### CATEGORY/FILTER = {FILTER} ###")
	(UNIKAT, ISOLATE), (DATA_ONE, COMBI_PAGES, COMBI_SERIES, COMBI_FIRST, COMBI_SECOND) = (set() for _ in range(2)), ([] for _ in range(5))
	if MARKER in ['newest_Series', 'last_Chance', 'overview_Themes', 'overview_Favorites']:
		START, HIGHEST = 1, 12
	else:
		START, HIGHEST = int(PAGE), int(PAGE)+1
	for ii in range(START, HIGHEST, 1):
		SLINK = f"{TARGET}&filter[primaryChannel.id]={DISCO_CHANNEL}&page[number]={str(ii)}&page[size]=50"
		debug_MS(f"(navigator.listSeries[1]) SERIES-PAGES XXX POS = {str(ii)} || URL = {SLINK} XXX")
		COMBI_PAGES.append([int(ii), SLINK])
	if COMBI_PAGES:
		CHALLENGE = AURORA_SEARCH.format(FILTER) if MARKER == 'overview_Themes' else AURORA_DEFAULT
		COMBI_SERIES = Transmission().retrieveMultiData(COMBI_PAGES+[[int(11), CHALLENGE]])
		if COMBI_SERIES:
			DATA_ONE = json.loads(COMBI_SERIES)
			#log("++++++++++++++++++++++++")
			#log(f"(navigator.listSeries[2]) XXXXX DATA_ONE-02 : {DATA_ONE} XXXXX")
			#log("++++++++++++++++++++++++")
			for item in DATA_ONE:
				if item is not None and (('data' in item and len(item['data']) > 0) or ('blocks' in item and len(item['blocks']) > 0)):
					if DISCO_HOST in item.get('Demand', '') and item.get('data', []) and len(item['data']) > 0:
						GENRES = list(filter(lambda xe: xe['type'] == 'genre', item.get('included', [])))
						IMAGES = list(filter(lambda xm: xm['type'] == 'image', item.get('included', [])))
						for each_uno in item.get('data', []):
							debug_MS("-----------------------------------------")
							debug_MS(f"(navigator.listSeries[2]) xxxxx EACH-02 : {each_uno} xxxxx")
							seriesID, species, picture, startTIMES = each_uno.get('id', None), "", icon, None
							if each_uno['relationships'].get('genres', '') and each_uno['relationships']['genres'].get('data', ''):
								genius = [og.get('id', []) for og in each_uno['relationships']['genres']['data']]
								species = ' / '.join(sorted([tg.get('attributes', {}).get('name', []) for tg in GENRES if tg.get('id') in genius]))
							if each_uno['relationships'].get('images', '') and each_uno['relationships']['images'].get('data', ''):
								picture = [pce.get('attributes', {}).get('src', []) for pce in IMAGES if pce.get('id') == each_uno['relationships']['images']['data'][0]['id']][0]
							each_uno = each_uno['attributes'] if each_uno.get('attributes', '') else each_uno
							discoID = each_uno.get('alternateId', None)
							name = cleaning(each_uno.get('name', None))
							if seriesID is None or name is None or seriesID in UNIKAT:
								continue
							UNIKAT.add(seriesID)
							SORTNAME = clear_umlaut(name).lower()
							epis_num = each_uno['episodeCount'] if str(each_uno.get('episodeCount')).isdecimal() and int(each_uno['episodeCount']) > 1 else None # All Episodes without STANDALONE = Specials
							video_num = each_uno['videoCount'] if epis_num is None and str(each_uno.get('videoCount')).isdecimal() and 1 <= int(each_uno['videoCount']) <= 5 else epis_num # All Videos include CLIP
							if str(each_uno.get('newestEpisodePublishStart'))[:4].isdecimal() and str(each_uno.get('newestEpisodePublishStart'))[:4] not in ['0', '1970']:
								LOCALstart = get_CentralTime(each_uno['newestEpisodePublishStart']) # 2024-05-05T19:10:00
								if LOCALstart > (datetime.utcnow() - timedelta(days=7, hours=2)): # Minus 7 Tage und 2 Stunden (GMT-Zeit)
									startTIMES = LOCALstart.strftime('%Y-%m-%dT%H:%M')
							NEWEST = True if (each_uno.get('hasNewEpisodes', '') is True or startTIMES) else False
							if MARKER == 'newest_Series' and NEWEST is False: continue
							descript = cleaning(each_uno['description']).replace('\n', '[CR]') if each_uno.get('description', '') else ""
							COMBI_FIRST.append([name, discoID, seriesID, picture, SORTNAME, descript, species, video_num, startTIMES, NEWEST])
					if PUBLIC_HOST in item.get('Demand', ''):
						blocking = item.get('data', []) if MARKER == 'overview_Themes' else item['blocks'][0].get('items', []) if item.get('blocks', []) and len(item['blocks']) > 0 else []
						for each_due in blocking:
							debug_MS("+++++++++++++++++++++++++++++++++++++++++")
							debug_MS(f"(navigator.listSeries[3]) xxxxx ITEM-03 : {each_due} xxxxx")
							FOUND, special, photo, poster, teaser = False, "", icon, None, ""
							if MARKER == 'overview_Favorites':
								showID = each_due['attributes']['showId'] if each_due.get('attributes', '') and each_due['attributes'].get('showId', '') else None
								match = [ids.get('url', '') for ids in FILTER if ids.get('url') == showID]
								if match and each_due.get('title', ''):
									FOUND = True
							else: FOUND = True
							if FOUND is True and each_due.get('type') == 'showpage':
								title = cleaning(each_due['title'])
								auroraID = each_due.get('slug', None)
								showID = each_due['attributes']['showId'] if each_due.get('attributes', '') and each_due['attributes'].get('showId', '') else None
								if (auroraID is None and showID is None) or (MARKER == 'overview_Themes' and each_due.get('parentSlug') == 'mediathek'): continue # Teilweise sind in den Genre-Shows Titel von Tele5 enthalten ('parentSlug'='mediathek')
								special = ' / '.join(sorted([tax.get('title', '') for tax in each_due.get('taxonomies', [])]))
								if each_due.get('metaMedia', '') and len(each_due['metaMedia']) > 0:
									photo = [pot.get('media', {}).get('url', '') for pot in each_due.get('metaMedia') if pot.get('role') == 'default'][0]
									poster = [psr.get('media', {}).get('url', '') for psr in each_due.get('metaMedia') if psr.get('role') == 'preview'][0]
								if poster is None and each_due.get('image', '') and each_due['image'].get('url', ''):
									poster = each_due['image']['url']
								if each_due.get('articleContent', '') and len(each_due['articleContent']) > 20:
									teaser = cleaning(each_due['articleContent'])
								COMBI_SECOND.append([title, auroraID, showID, photo, poster, teaser, special])
	if COMBI_FIRST:
		matchDAT, matchSID = [dax[8] for dax in COMBI_FIRST[:] if dax[8] and len(dax[8]) > 5], [six[2] for six in COMBI_FIRST[:] if six[2] and len(six[2]) <= 8]
		RESULT = [av + bv for av in COMBI_FIRST for bv in COMBI_SECOND if av[2] == bv[2] or (av[1] is not None and bv[1] is not None and ((av[1] == bv[1]) or (av[1] == clear_invalid(bv[1]))))] # Zusammenführung von Liste1 und Liste2 - wenn die ID an dritter Stelle(2) oder der Slug an zweiter Stelle (1) überein stimmt !!!
		if MARKER in ['newest_Series', 'last_Chance', 'listing_Series', 'overview_Alphabet']:
			RESULT += [cv for cv in COMBI_FIRST if all(dv[0] != cv[0] for dv in COMBI_SECOND)] # Der übriggebliebene Rest von Liste1 - wenn der Name nicht in der Liste2 vorhanden ist !!!
		elif MARKER == 'overview_Favorites':
			RESULT += [cv for cv in COMBI_FIRST for dv in FILTER if cv[2] == dv.get('url', '') and not any(ev[2] in cv[2] for ev in RESULT)] # Der übriggebliebene Rest der Favoriten - wenn die ID nicht im RESULT vorkommt !!!
		RESULT = sorted(RESULT, key=lambda mvs: mvs[4]) if MARKER in ['listing_Series', 'overview_Themes', 'overview_Alphabet', 'overview_Favorites'] else \
			sorted(RESULT, key=lambda mvs: mvs[8], reverse=True) if MARKER == 'newest_Series' and len(matchDAT) == len(matchSID) else RESULT
		for xev in RESULT:
			debug_MS("*****************************************")
			debug_MS(f"(navigator.listSeries[4]) ### Anzahl : {len(xev)} || Eintrag : {xev} ###")
			if len(xev) >= 17: ### Liste1+Liste2 ist grösser als Nummer:17 ###
				Title1, ALTID1, SERID1, Thumb1, ORDERNAME, Desc1, Genre1, numbers, start, newest = xev[0], xev[1], xev[2], xev[3], xev[4], xev[5], xev[6], xev[7], xev[8], xev[9]
				Title2, ALTID2, SERID2, Thumb2, cover, Desc2, Genre2 = xev[10], xev[11], xev[12], xev[13], xev[14], xev[15], xev[16]
			elif len(xev) == 10:
				Title1, ALTID1, SERID1, Thumb1, ORDERNAME, Desc1, Genre1, numbers, start, newest = xev[0], xev[1], xev[2], xev[3], xev[4], xev[5], xev[6], xev[7], xev[8], xev[9]
				Title2, ALTID2, SERID2, Thumb2, cover, Desc2, Genre2 = None, None, None, icon, None, "", ""
			else: continue
			name, image = translation(30620).format(Title1, numbers) if numbers else Title1, Thumb2 if Thumb2 != icon else Thumb1 if Thumb1 != icon else f"{artpic}standard.png"
			plot, genre = Desc2 if len(Desc2) > len(Desc1) else Desc1, Genre2 if len(Genre2) > len(Genre1) else Genre1
			if SERID1 and len(SERID1) <= 8 and SERID1 not in ISOLATE:
				ISOLATE.add(SERID1)
				if 'filter[hasExpiringEpisodes]' in TARGET:
					name = translation(30621).format(name)
				elif not 'filter[hasExpiringEpisodes]' in TARGET and newest is True:
					name = translation(30622).format(name)
				if MARKER != 'overview_Favorites':
					operation = 'adding'
					if xbmcvfs.exists(FAVORIT_FILE) and os.stat(FAVORIT_FILE).st_size > 0:
						for present in preserve(FAVORIT_FILE).get('items', []):
							if present.get('url') == SERID1: operation = 'skipping'
				elif MARKER == 'overview_Favorites':
					operation = 'removing'
				debug_MS(f"(navigator.listSeries[4]) ##### NAME : {name} || SERIES_IDD : {SERID1} || THUMB : {image} || FAVORIT_HANDLE : {operation} #####")
				FETCH_UNO = create_entries({'Title': name, 'Plot': plot, 'Genre': genre, 'Image': image, 'Cover': cover})
				addDir({'mode': 'listEpisodes', 'url': SERID1, 'genre': genre, 'name': Title1, 'pict': image, 'plot': plot}, FETCH_UNO, handling=operation)
		for meta in DATA_ONE:
			if MARKER in ['listing_Series', 'overview_Alphabet'] and meta is not None and meta.get('meta') and str(meta['meta'].get('totalPages')).isdecimal() and int(PAGE) < int(meta['meta']['totalPages']):
				debug_MS(f"(navigator.listSeries[5]) PAGES ### currentPAGE : {PAGE} from totalPAGES : {meta['meta']['totalPages']} ###")
				FETCH_DUE = create_entries({'Title': translation(30623).format(int(PAGE)+1), 'Image': f"{artpic}nextpage.png"})
				addDir({'mode': 'listSeries', 'url': TARGET, 'page': int(PAGE)+1, 'marker': MARKER}, FETCH_DUE)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listEpisodes(TVID, origGENRE, origSERIE):
	debug_MS("(navigator.listEpisodes) ------------------------------------------------ START = listEpisodes -----------------------------------------------")
	debug_MS(f"(navigator.listEpisodes) ### URL = {TVID} ### GENRE = {origGENRE} ### origSERIE = {origSERIE} ###")
	UNIKAT, position, FAULTS, (COMBI_PAGES, COMBI_EPISODE, COMBI_SECOND) = set(), 0, False, ([] for _ in range(3))
	backTIMES = f"{(datetime.utcnow() - timedelta(days=7, hours=2)).isoformat(timespec='seconds')}Z" # Minus 7 Tage und 2 Stunden (GMT-Zeit) // 2024-05-05T19:10:00
	for ii in range(1, 6, 1):
		ELINK = f"{EUAPI_VIDEOS}&sort=-seasonNumber,-episodeNumber&filter[show.id]={TVID}&filter[videoType]=EPISODE,STANDALONE&page[number]={str(ii)}&page[size]=100"
		if TVID.startswith(DISCO_HOST): # filter[earliestPlayableStart.gt] = ab zurückliegendem Zeitpunkt // filter[earliestPlayableStart.lt] = bis vorausliegendem Zeitpunkt
			ELINK = f"{TVID}&filter[earliestPlayableStart.gt]={backTIMES}&filter[videoType]=EPISODE,STANDALONE&page[number]={str(ii)}&page[size]=30"
		debug_MS(f"(navigator.listEpisodes[1]) EPISODE-PAGES XXX POS = {str(ii)} || URL = {ELINK} XXX")
		COMBI_PAGES.append([int(ii), ELINK])
	if COMBI_PAGES:
		COMBI_EPISODE = Transmission().retrieveMultiData(COMBI_PAGES)
		if COMBI_EPISODE:
			DATA_ONE = json.loads(COMBI_EPISODE)
			#log("++++++++++++++++++++++++")
			#log(f"(navigator.listEpisodes[2]) XXXXX DATA_ONE-02 : {DATA_ONE} XXXXX")
			#log("++++++++++++++++++++++++")
			for item in sorted(DATA_ONE, key=lambda pn: int(pn.get('Position', 0))):
				if item is not None and 'ERROR_occurred' in item: FAULTS = True
				elif item is not None and 'data' in item and len(item['data']) > 0:
					GENRES = list(filter(lambda xe: xe['type'] == 'genre', item.get('included', [])))
					IMAGES = list(filter(lambda xm: xm['type'] == 'image', item.get('included', [])))
					SHOWS = list(filter(lambda xw: xw['type'] == 'show', item.get('included', [])))
					for each in item.get('data', []):
						debug_MS("-----------------------------------------")
						debug_MS(f"(navigator.llistEpisodes[2]) xxxxx EACH-02 : {each} xxxxx")
						image, (plus_SUFFIX, Note_1, Note_2) = icon, ("" for _ in range(3))
						species, newSERIE, Title2, startTIMES, endTIMES, aired, begins, year, mpaa = (None for _ in range(9))
						episID = each.get('id', None)
						if each['relationships'].get('genres', '') and each['relationships']['genres'].get('data', ''):
							genius = [og.get('id', []) for og in each['relationships']['genres']['data']]
							species = ' / '.join(sorted([tg.get('attributes', {}).get('name', []) for tg in GENRES if tg.get('id') in genius]))
						genre = species if len(origGENRE) < 3 else origGENRE
						if each['relationships'].get('images', '') and each['relationships']['images'].get('data', ''):
							image = [img.get('attributes', {}).get('src', []) for img in IMAGES if img.get('id') == each['relationships']['images']['data'][0]['id']][0]
						if TVID.startswith(DISCO_HOST) and each['relationships'].get('show', '') and each['relationships']['show'].get('data', ''):
							newSERIE = [tvs.get('attributes', {}).get('name', []) for tvs in SHOWS if tvs.get('id') == each['relationships']['show']['data']['id']][0]
						seriesname = origSERIE if newSERIE is None else newSERIE
						each = each['attributes'] if each.get('attributes', '') else each
						title = cleaning(each.get('name', None))
						if episID is None or title is None or episID in UNIKAT:
							continue
						UNIKAT.add(episID)
						if each.get('isExpiring', '') is True or each.get('isNew', '') is True:
							plus_SUFFIX = translation(30624) if each.get('isNew', '') is True else translation(30625)
						season = f"{int(each['seasonNumber']):02}" if str(each.get('seasonNumber')).isdecimal() else 00
						episode = f"{int(each['episodeNumber']):02}" if str(each.get('episodeNumber')).isdecimal() else 00
						videoTYPE = each.get('videoType', 'UNKNOWN')
						if videoTYPE.upper() == 'STANDALONE' and episode == 00:
							position += 1
						if season != 00 and episode != 00:
							Title1 = translation(30626).format(season, episode) if videoTYPE.upper() == 'STANDALONE' else translation(30627).format(season, episode)
							Title2 = f"{title} - {newSERIE+plus_SUFFIX}" if newSERIE else title+plus_SUFFIX
						else:
							if videoTYPE.upper() == 'STANDALONE':
								season, episode = f"{int(0):02}", f"{int(position):02}"
								Title1 = translation(30626).format(season, episode)
								Title2 = f"{title}  [Special]{plus_SUFFIX}" if not 'Special' in title else title+plus_SUFFIX
								if newSERIE:
									Title2 = f"{title}  [Special] - {newSERIE+plus_SUFFIX}" if not 'Special' in title else f"{title} - {newSERIE+plus_SUFFIX}"
							else: Title1 = f"{title} - {newSERIE+plus_SUFFIX}" if newSERIE else title+plus_SUFFIX
						if str(each.get('publishStart'))[:4].isdecimal() and str(each.get('publishStart'))[:4] not in ['0', '1970']:
							LOCALstart = get_CentralTime(each['publishStart'])
							startTIMES = LOCALstart.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
							aired = LOCALstart.strftime('%d.%m.%Y') # FirstAired
							begins = LOCALstart.strftime('%Y-%m-%dT%H:%M') if KODI_ov20 else LOCALstart.strftime('%d.%m.%Y') # 2023-03-09T12:30:00 = NEWFORMAT // 09.03.2023 = OLDFORMAT
						if str(each.get('publishEnd'))[:4].isdecimal() and str(each.get('publishEnd'))[:4] not in ['0', '1970']:
							LOCALend = get_CentralTime(each['publishEnd'])
							endTIMES = LOCALend.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
						if str(each.get('airDate'))[:4].isdecimal() and str(each.get('airDate'))[:4] not in ['0', '1970']:
							year = str(each['airDate'])[:4]
						if startTIMES and endTIMES: Note_1 = translation(30628).format(startTIMES, endTIMES)
						elif startTIMES and endTIMES is None: Note_1 = translation(30629).format(startTIMES)
						elif startTIMES is None and endTIMES is None: Note_1 = '[CR]'
						if str(each.get('rating')).isdecimal():
							mpaa = translation(30630).format(each['rating']) if str(each.get('rating')) != '0' else translation(30631)
						if mpaa is None and each.get('contentRatings', '') and str(each.get('contentRatings', {})[0].get('code', '')).isdecimal():
							mpaa = translation(30630).format(each['contentRatings'][0]['code']) if str(each['contentRatings'][0]['code']) != '0' else translation(30631)
						Note_2 = cleaning(each['description']).replace('\n', '[CR]') if each.get('description', '') else ""
						plot = f"{seriesname}[CR]{Note_1}{Note_2}"
						protect = each.get('drmEnabled', False)
						duration = get_RunTime(each['videoDuration']) if str(each.get('videoDuration')).isdecimal() else None
						COMBI_SECOND.append([Title1, Title2, episID, image, season, episode, seriesname, plot, duration, begins, aired, year, genre, mpaa, protect])
	if COMBI_SECOND:
		COMBI_SECOND = sorted(COMBI_SECOND, key=lambda evs: (int(evs[4]), int(evs[5])), reverse=True) if SORTING == 0 and not TVID.startswith(DISCO_HOST) else COMBI_SECOND
		for Title1, Title2, episID, image, season, episode, seriesname, plot, duration, begins, aired, year, genre, mpaa, protect in COMBI_SECOND:
			if SORTING == 1 and not TVID.startswith(DISCO_HOST):
				for method in get_sorting(): xbmcplugin.addSortMethod(ADDON_HANDLE, method)
			name = Title1.strip() if Title2 is None else f"{Title1.strip()} {Title2.strip()}"
			cineType = 'episode' if episode != 00 else 'movie'
			debug_MS("*****************************************")
			debug_MS(f"(navigator.listEpisodes[3]) ##### NAME : {name} || IDD : {episID} || DURATION : {duration} #####")
			debug_MS(f"(navigator.listEpisodes[3]) ##### START : {startTIMES} || SEASON : {season} || EPISODE : {episode} || MPAA : {mpaa} #####")
			debug_MS(f"(navigator.listEpisodes[3]) ##### SERIE : {seriesname} || IMAGE : {image} #####")
			FETCH_UNO = create_entries({'Title': name, 'TvShowTitle': seriesname, 'Plot': plot, 'Season': season,'Episode': episode, 'Duration': duration,\
				'Date': begins, 'Aired': aired, 'Year': year, 'Genre': genre, 'Mpaa': mpaa, 'Mediatype': cineType, 'Image': image, 'Reference': 'Single'})
			addDir({'mode': 'playVideo', 'url': episID, 'cineType': cineType}, FETCH_UNO, folder=False)
	elif not COMBI_SECOND and not FAULTS:
		failing(f'(navigator.listEpisodes) ##### NO EPISODES-LIST - NO ENTRY FOR: "{origSERIE}" FOUND #####')
		return dialog.notification(translation(30525), translation(30526).format(origSERIE), icon, 10000)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def playVideo(PLID):
	debug_MS("(navigator.playVideo) ------------------------------------------------ START = playVideo -----------------------------------------------")
	debug_MS(f"(navigator.playVideo) ### URL = {DISCO_HOST}/playback/v3/videoPlaybackInfo ### IDD = {PLID} ###")
	STREAM, FINAL_URL, DRM_GUARD, DRM_SPECIES = (False for _ in range(4))
	payload = {'deviceInfo': {'adBlocker': False, 'drmSupported': True, 'hdrCapabilities': [], 'hwDecodingCapabilities': [], 'soundCapabilities': []}, 'wisteriaProperties': {}, 'videoId': str(PLID)}
	# NEW = https://public.aurora.enhanced.live/playback/v3/videoPlaybackInfo // OLD = https://eu1-prod.disco-api.com/playback/v3/videoPlaybackInfo
	DATA_ONE = Transmission().retrieveContent(f"{DISCO_HOST}/playback/v3/videoPlaybackInfo", 'POST', data=json.dumps(payload, indent=2))
	debug_MS("++++++++++++++++++++++++")
	debug_MS(f"(navigator.playVideo[1]) XXXXX CONTENT-01 : {DATA_ONE} XXXXX")
	debug_MS("++++++++++++++++++++++++")
	if DATA_ONE is not None and DATA_ONE.get('data', '') and DATA_ONE['data'].get('attributes', '') and len(DATA_ONE['data']['attributes']) > 0:
		for video in DATA_ONE['data']['attributes']['streaming']:
			if video.get('protection', '') and video['protection'].get('drmEnabled', False) is True and video.get('type', '') =='dash':
				STREAM, MIME, FINAL_URL = 'MPD', 'application/dash+xml', video['url']
				DRM_GUARD, DRM_TOKEN = video['protection']['schemes']['widevine']['licenseUrl'], video['protection']['drmToken']
				debug_MS("(navigator.playVideo[2]) ***** TAKE - Inputstream (mpd) - FILE *****")
			if FINAL_URL is False and video.get('type', '') == 'hls':
				STREAM, MIME, FINAL_URL = 'HLS', 'application/vnd.apple.mpegurl', video['url']
				debug_MS("(navigator.playVideo[2]) ***** TAKE - Inputstream (hls) - FILE *****")
	if FINAL_URL and STREAM and plugin_operate('inputstream.adaptive'):
		LPM = xbmcgui.ListItem(path=FINAL_URL, offscreen=True)
		IA_NAME, IA_SYSTEM = 'inputstream.adaptive', 'com.widevine.alpha'
		IA_VERSION = re.sub(r'(~[a-z]+(?:.[0-9]+)?|\+[a-z]+(?:.[0-9]+)?$|[.^]+)', '', xbmcaddon.Addon(IA_NAME).getAddonInfo('version'))[:4]
		DRM_HEADERS = {'PreAuthorization': DRM_TOKEN, 'Content-Type': 'application/octet-stream', 'User-Agent': agent_WEB} if DRM_GUARD else {}
		LPM.setMimeType(MIME), LPM.setContentLookup(False), LPM.setProperty('inputstream', IA_NAME)
		if KODI_un21:
			LPM.setProperty(f"{IA_NAME}.manifest_type", STREAM.lower()) # DEPRECATED ON Kodi v21, because the manifest type is now auto-detected.
		if KODI_ov20:
			LPM.setProperty(f"{IA_NAME}.manifest_headers", f"User-Agent={agent_WEB}") # On KODI v20 and above
		else: LPM.setProperty(f"{IA_NAME}.stream_headers", f"User-Agent={agent_WEB}") # On KODI v19 and below
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
		if DRM_SPECIES: log(f"(navigator.playVideo[3]) INPUTSTREAM_VERSION: {IA_VERSION} >>>>> LICENSE : {'|'.join(DRM_SPECIES.values())} <<<<<")
		log(f"(navigator.playVideo) {STREAM}_stream : {FINAL_URL}|User-Agent={agent_WEB}")
		from .player import discoMaster
		discoMaster().start_signal(LPM)
	else:
		failing(f"(navigator.playVideo) ##### Abspielen des Streams NICHT möglich ##### PLID : {PLID} #####\n ########## KEINEN Stream-Eintrag gefunden !!! ##########")
		xbmcplugin.setResolvedUrl(ADDON_HANDLE, False, xbmcgui.ListItem(offscreen=True))
		xbmc.PlayList(1).clear()
		return dialog.notification(translation(30521).format('ID - ', PLID), translation(30527), icon, 8000)

def listFavorites():
	debug_MS("(navigator.listFavorites) ------------------------------------------------ START = listFavorites -----------------------------------------------")
	WATCH = {}
	WATCH['items'] = []
	if xbmcvfs.exists(FAVORIT_FILE) and os.stat(FAVORIT_FILE).st_size > 0:
		for article in preserve(FAVORIT_FILE).get('items', []): # Liste alle Favoriten - gehe direkt zum 'listSeries' Ordner
			debug_MS(f"(navigator.listFavorites[1]) ##### NAME : {article.get('name')} || IDD : {article.get('url')} || IMAGE : {article.get('pict')} #####")
			WATCH['items'].append({'url': article.get('url'), 'name': article.get('name'), 'pict': article.get('pict'), 'plot': article.get('plot')})
		if WATCH['items']:
			return listSeries(f"{EUAPI_SHOWS}&sort=name", 1, 'overview_Favorites', WATCH['items'])
	return dialog.notification(translation(30528), translation(30529), icon, 8000)

def favorit_construct(**kwargs):
	TOPS = {}
	TOPS['items'] = []
	if xbmcvfs.exists(FAVORIT_FILE) and os.stat(FAVORIT_FILE).st_size > 0:
		TOPS = preserve(FAVORIT_FILE)
	if kwargs['action'] == 'ADD':
		del kwargs['mode']; del kwargs['action']
		TOPS['items'].append({key: value for key, value in kwargs.items() if value not in ['', 'None', None]})
		preserve(FAVORIT_FILE, TOPS)
		xbmc.sleep(500)
		dialog.notification(translation(30530), translation(30531).format(kwargs['name']), icon, 10000)
	elif kwargs['action'] == 'DEL':
		TOPS['items'] = [top for top in TOPS['items'] if top.get('url') != kwargs.get('url')]
		preserve(FAVORIT_FILE, TOPS)
		xbmc.executebuiltin('Container.Refresh')
		xbmc.sleep(1000)
		dialog.notification(translation(30530), translation(30532).format(kwargs['name']), icon, 10000)

def addDir(params, listitem, folder=True, handling='default'):
	uws, entries = build_mass(params), []
	listitem.setPath(uws)
	if handling == 'adding' and params:
		entries.append([translation(30651), f"RunPlugin({build_mass({**params, **{'mode': 'favorit_construct', 'action': 'ADD'}})})"])
	if handling == 'removing' and params:
		entries.append([translation(30652), f"RunPlugin({build_mass({**params, **{'mode': 'favorit_construct', 'action': 'DEL'}})})"])
	if len(entries) > 0: listitem.addContextMenuItems(entries)
	return xbmcplugin.addDirectoryItem(ADDON_HANDLE, uws, listitem, folder)

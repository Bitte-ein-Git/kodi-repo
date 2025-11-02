# -*- coding: utf-8 -*-

from .common import *
from .utilities import Transmission
# https://public.aurora.enhanced.live/content/videos/9229?include=primaryChannel,primaryChannel.images,alternateChannels,show,show.images,show.seasons,show.taxonomyNodes,show.taxonomyNodes.images,genres,images,contentPackages,season,taxonomyNodes,taxonomyNodes.images,parent,ratings,ratings.images,ratingDescriptors,ratingDescriptors.images&decorators=viewingHistory,isFavorite,playbackAllowed&sort=name&page[size]=100&page[number]=1


def mainMenu():
	for TITLE, PATH in [(30601, {'mode': 'listFavorites'}), (30602, {'mode': 'listSeries', 'url': f"{API_DISCO}/content/shows?include=images,genres&sort=-newestEpisodePublishStart&filter[hasNewEpisodes]=true", 'marker': 'newest_Series'}),
		(30603, {'mode': 'listEpisodes', 'url': f"{API_DISCO}/content/videos?include=show,images,genres&sort=-earliestPlayableStart&filter[primaryChannel.id]={PRIMARY_CHANNEL}"}),
		(30604, {'mode': 'listSeries', 'url': f"{API_DISCO}/content/shows?include=images,genres&sort=publishEnd&filter[hasExpiringEpisodes]=true", 'marker': 'last_Chance'}),
		(30605, {'mode': 'listThemes', 'url': API_LOMA.format('/page/sendungen/')}), 
		(30606, {'mode': 'listAlphabet'}), (30607, {'mode': 'listSeries', 'url': f"{API_DISCO}/content/shows?include=images,genres&sort=name", 'marker': 'listing_Series'})]:
		FETCH_UNO = create_entries({'Title': translation(TITLE), 'Image': f"{artpic}favourites.png" if TITLE == 30601 else icon})
		addDir(PATH, FETCH_UNO)
	if enableADJUSTMENT:
		addDir({'mode': 'aConfigs'}, create_entries({'Title': translation(30608), 'Image': f"{artpic}settings.png"}), folder=False)
		if plugin_operate('inputstream.adaptive'):
			addDir({'mode': 'iConfigs'}, create_entries({'Title': translation(30609), 'Image': f"{artpic}settings.png"}), folder=False)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listThemes(TARGET):
	debug_MS("(navigator.listThemes) ------------------------------------------------ START = listThemes -----------------------------------------------")
	xbmcplugin.addSortMethod(ADDON_HANDLE, xbmcplugin.SORT_METHOD_LABEL)
	DATA_ONE, UNIKAT = Transmission().retrieveContent(TARGET, forcing=False), set()
	debug_MS("++++++++++++++++++++++++")
	debug_MS(f"(navigator.listThemes[1]) XXXXX DATA_ONE-01 : {DATA_ONE} XXXXX")
	debug_MS("++++++++++++++++++++++++")
	if DATA_ONE.get('blocks', []) and len(DATA_ONE['blocks']) > 0:
		for item in DATA_ONE['blocks'][0].get('items', []):
			for each in item.get('taxonomies', []):
				name = cleaning(each['title'])
				if name in UNIKAT:
					continue
				UNIKAT.add(name)
				NEW_URL = f"{API_DISCO}/content/shows?include=images,genres&sort=name"
				FETCH_UNO = create_entries({'Title': name, 'Image': f"{artpic}standard.png"})
				addDir({'mode': 'listSeries', 'url': NEW_URL, 'marker': 'overview_Themes', 'transmit': name}, FETCH_UNO)
				debug_MS(f"(navigator.listThemes[2]) ##### NAME : {name} #####")
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listAlphabet():
	debug_MS("(navigator.listAlphabet) ------------------------------------------------ START = listAlphabet -----------------------------------------------")
	for letter in ['0-9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']:
		NEW_URL = f"{API_DISCO}/content/shows?include=images,genres&sort=name&filter[name.startsWith]={letter.replace('0-9', '1')}"
		FETCH_UNO = create_entries({'Title': letter, 'Image': f"{alppic}{letter}.jpg"})
		addDir({'mode': 'listSeries', 'url': NEW_URL, 'marker': 'overview_Alphabet'}, FETCH_UNO)
	xbmcplugin.endOfDirectory(ADDON_HANDLE)

def listSeries(TARGET, PAGE, MARKER, FILTER):
	debug_MS("(navigator.listSeries) ------------------------------------------------ START = listSeries -----------------------------------------------")
	debug_MS(f"(navigator.listSeries) ### URL = {TARGET} ### PAGE = {PAGE} ### MARKER = {MARKER} ### CATEGORY/FILTER = {FILTER} ###")
	UNIKAT, (DATA_ONE, COMBI_PAGES, COMBI_SERIES, COMBI_FIRST, COMBI_SECOND) = set(), ([] for _ in range(5))
	if MARKER in ['newest_Series', 'last_Chance', 'overview_Themes', 'overview_Favorites']:
		START, HIGHEST = 1, 11
	else:
		START, HIGHEST = int(PAGE), int(PAGE)+1
	for ii in range(START, HIGHEST, 1):
		SLINK = f"{TARGET}&filter[primaryChannel.id]={PRIMARY_CHANNEL}&page[number]={str(ii)}&page[size]=50"
		debug_MS(f"(navigator.listSeries[1]) SERIES-PAGES XXX POS = {str(ii)} || URL = {SLINK} XXX")
		COMBI_PAGES.append([int(ii), SLINK])
	if COMBI_PAGES:
		COMBI_SERIES = Transmission().retrieveMultiData(COMBI_PAGES+[[int(11), API_LOMA.format('/page/sendungen/')]])
		if COMBI_SERIES:
			DATA_ONE = json.loads(COMBI_SERIES)
			#log("++++++++++++++++++++++++")
			#log(f"(navigator.listSeries[2]) XXXXX DATA_ONE-02 : {DATA_ONE} XXXXX")
			#log("++++++++++++++++++++++++")
			for item in DATA_ONE:
				if item is not None and (('data' in item and len(item['data']) > 0) or ('blocks' in item and len(item['blocks']) > 0)):
					if item.get('blocks', []) and len(item['blocks']) > 0:
						for each_uno in item['blocks'][0].get('items', []):
							debug_MS("-----------------------------------------")
							debug_MS(f"(navigator.listSeries[2]) xxxxx EACH-02 : {each_uno} xxxxx")
							FOUND, special, photo, poster, teaser = False, "", icon, None, ""
							if MARKER == 'overview_Themes':
								match = [tax.get('title', '') for tax in each_uno.get('taxonomies', [])]
								if any(xy in FILTER for xy in match) and each_uno.get('title', ''):
									special = ' / '.join(sorted(match))
									FOUND = True
							elif MARKER == 'overview_Favorites':
								showID = each_uno['attributes']['showId'] if each_uno.get('attributes', '') and each_uno['attributes'].get('showId', '') else None
								match = [ids.get('url', '') for ids in FILTER if ids.get('url') == showID]
								if match and each_uno.get('title', ''):
									FOUND = True
							else: FOUND = True
							if FOUND is True:
								title = cleaning(each_uno['title'])
								showID = each_uno['attributes']['showId'] if each_uno.get('attributes', '') and each_uno['attributes'].get('showId', '') else None
								if MARKER != 'overview_Themes':
									special = ' / '.join(sorted([tax.get('title', '') for tax in each_uno.get('taxonomies', [])]))
								if each_uno.get('metaMedia', '') and len(each_uno['metaMedia']) > 0:
									photo = [pot.get('media', {}).get('url', []) for pot in each_uno.get('metaMedia') if pot.get('role') == 'default'][0]
									poster = [psr.get('media', {}).get('url', []) for psr in each_uno.get('metaMedia') if psr.get('role') == 'preview'][0]
								if each_uno.get('articleContent', ''):
									teaser = cleaning(each_uno['articleContent']).replace('\n', '[CR]')
									teaser += '' if teaser.endswith(('.', '!', '?')) else '...'
								COMBI_FIRST.append([title, showID, photo, poster, teaser, special])
					if item.get('data', []) and len(item['data']) > 0:
						GENRES = list(filter(lambda x: x['type'] == 'genre', item.get('included', [])))
						IMAGES = list(filter(lambda x: x['type'] == 'image', item.get('included', [])))
						for each_due in item.get('data', []):
							debug_MS("+++++++++++++++++++++++++++++++++++++++++")
							debug_MS(f"(navigator.listSeries[3]) xxxxx EACH-03 : {each_due} xxxxx")
							seriesID, species, picture, startTIMES = each_due.get('id', None), "", icon, None
							if each_due['relationships'].get('genres', '') and each_due['relationships']['genres'].get('data', ''):
								genius = [og.get('id', []) for og in each_due['relationships']['genres']['data']]
								species = ' / '.join(sorted([tg.get('attributes', {}).get('name', []) for tg in GENRES if tg.get('id') in genius]))
							if each_due['relationships'].get('images', '') and each_due['relationships']['images'].get('data', ''):
								picture = [pce.get('attributes', {}).get('src', []) for pce in IMAGES if pce.get('id') == each_due['relationships']['images']['data'][0]['id']][0]
							each_due = each_due['attributes'] if each_due.get('attributes', '') else each_due
							name = cleaning(each_due.get('name', None))
							if seriesID is None or name is None or seriesID in UNIKAT:
								continue
							UNIKAT.add(seriesID)
							SORTNAME = cleanUmlaut(name).lower()
							epis_num = each_due['episodeCount'] if str(each_due.get('episodeCount')).isdecimal() and int(each_due['episodeCount']) > 1 else None # All Episodes without STANDALONE = Specials
							video_num = each_due['videoCount'] if epis_num is None and str(each_due.get('videoCount')).isdecimal() and 1 <= int(each_due['videoCount']) <= 5 else epis_num # All Videos include CLIP
							if str(each_due.get('newestEpisodePublishStart'))[:4].isdecimal() and str(each_due.get('newestEpisodePublishStart'))[:4] not in ['0', '1970']:
								LOCALstart = get_CentralTime(each_due['newestEpisodePublishStart']) # 2024-05-05T19:10:00
								if LOCALstart > (datetime.utcnow() - timedelta(days=7, hours=1)): # Minus 7 Tage und 1 Stunde (GMT-Zeit)
									startTIMES = LOCALstart.strftime('%Y-%m-%dT%H:%M')
							NEWEST = True if (each_due.get('hasNewEpisodes', '') is True or startTIMES) else False
							if MARKER == 'newest_Series' and NEWEST is False: continue
							descript = cleaning(each_due['description']).replace('\n', '[CR]') if each_due.get('description', '') else ""
							COMBI_SECOND.append([name, seriesID, picture, SORTNAME, descript, species, video_num, startTIMES, NEWEST])
	if COMBI_SECOND:
		matchDAT, matchSID = [dax[7] for dax in COMBI_SECOND[:] if dax[7] and len(dax[7]) > 5], [six[1] for six in COMBI_SECOND[:] if six[1] and len(six[1]) <= 8]
		RESULT = [av + bv for av in COMBI_SECOND for bv in COMBI_FIRST if av[1] == bv[1]] # Zusammenführung von Liste1 und Liste2 - wenn die ID an zweiter Stelle(1) überein stimmt !!!
		if MARKER in ['newest_Series', 'last_Chance', 'listing_Series', 'overview_Alphabet']:
			RESULT += [cv for cv in COMBI_SECOND if all(dv[1] != cv[1] for dv in COMBI_FIRST)] # Der übriggebliebene Rest von Liste2 - wenn die ID nicht in der Liste1 vorkommt !!!
		elif MARKER == 'overview_Favorites':
			RESULT += [cv for cv in COMBI_SECOND for dv in FILTER if cv[1] == dv.get('url', '') and not any(ev[1] in cv[1] for ev in RESULT)] # Der übriggebliebene Rest der Favoriten - wenn die ID nicht in der Liste1 vorkommt !!!
		RESULT = sorted(RESULT, key=lambda mvs: mvs[3]) if MARKER in ['listing_Series', 'overview_Themes', 'overview_Alphabet', 'overview_Favorites'] else \
			sorted(RESULT, key=lambda mvs: mvs[7], reverse=True) if MARKER == 'newest_Series' and len(matchDAT) == len(matchSID) else RESULT
		for xev in RESULT:
			debug_MS("*****************************************")
			debug_MS(f"(navigator.listSeries[4]) ### Anzahl : {len(xev)} || Eintrag : {xev} ###")
			if len(xev) >= 15: ### Liste1+Liste2 ist grösser als Nummer:15 ###
				Title1, IDNT1, Thumb1, ORDERNAME, Desc1, Genre1, numbers, start, newest, Title2, IDNT2, Thumb2, cover, Desc2, Genre2 = xev[0], xev[1], xev[2], xev[3], xev[4], xev[5], xev[6], xev[7], xev[8], xev[9], xev[10], xev[11], xev[12], xev[13], xev[14]
			elif len(xev) == 9:
				Title1, IDNT1, Thumb1, ORDERNAME, Desc1, Genre1, numbers, start, newest = xev[0], xev[1], xev[2], xev[3], xev[4], xev[5], xev[6], xev[7], xev[8]
				Title2, IDNT2, Thumb2, cover, Desc2, Genre2 = None, None, icon, None, "", ""
			else: continue
			name, image = translation(30620).format(Title1, numbers) if numbers else Title1, Thumb2 if Thumb2 != icon else Thumb1 if Thumb1 != icon else f"{artpic}standard.png"
			plot, genre = Desc2 if len(Desc2) > len(Desc1) else Desc1, Genre2 if len(Genre2) > len(Genre1) else Genre1
			if IDNT1 and len(IDNT1) <= 8:
				if 'filter[hasExpiringEpisodes]' in TARGET:
					name = translation(30621).format(name)
				elif not 'filter[hasExpiringEpisodes]' in TARGET and newest is True:
					name = translation(30622).format(name)
				if MARKER != 'overview_Favorites':
					operation = 'adding'
					if xbmcvfs.exists(FAVORIT_FILE) and os.stat(FAVORIT_FILE).st_size > 0:
						for present in preserve(FAVORIT_FILE).get('items', []):
							if present.get('url') == IDNT1: operation = 'skipping'
				elif MARKER == 'overview_Favorites':
					operation = 'removing'
				debug_MS(f"(navigator.listSeries[4]) ##### NAME : {name} || SERIES_IDD : {IDNT1} || THUMB : {image} || FAVORIT_HANDLE : {operation} #####")
				FETCH_UNO = create_entries({'Title': name, 'Plot': plot, 'Genre': genre, 'Image': image, 'Cover': cover})
				addDir({'mode': 'listEpisodes', 'url': IDNT1, 'genre': genre, 'name': Title1, 'pict': image, 'plot': plot}, FETCH_UNO, handling=operation)
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
	backTIMES = f"{(datetime.utcnow() - timedelta(days=7, hours=1)).isoformat(timespec='seconds')}Z" # Minus 7 Tage und 1 Stunde (GMT-Zeit) // 2024-05-05T19:10:00
	for ii in range(1, 6, 1):
		ELINK = f"{API_DISCO}/content/videos?include=images,genres&sort=-seasonNumber,-episodeNumber&filter[show.id]={TVID}&filter[videoType]=EPISODE,STANDALONE&page[number]={str(ii)}&page[size]=100"
		if TVID.startswith(API_DISCO): # filter[earliestPlayableStart.gt] = ab zurückliegendem Zeitpunkt // filter[earliestPlayableStart.lt] = bis vorausliegendem Zeitpunkt
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
					GENRES = list(filter(lambda x: x['type'] == 'genre', item.get('included', [])))
					IMAGES = list(filter(lambda x: x['type'] == 'image', item.get('included', [])))
					SHOWS = list(filter(lambda x: x['type'] == 'show', item.get('included', [])))
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
						if TVID.startswith(API_DISCO) and each['relationships'].get('show', '') and each['relationships']['show'].get('data', ''):
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
		COMBI_SECOND = sorted(COMBI_SECOND, key=lambda evs: (int(evs[4]), int(evs[5])), reverse=True) if SORTING == 0 and not TVID.startswith(API_DISCO) else COMBI_SECOND
		for Title1, Title2, episID, image, season, episode, seriesname, plot, duration, begins, aired, year, genre, mpaa, protect in COMBI_SECOND:
			if SORTING == 1 and not TVID.startswith(API_DISCO):
				for method in getSorting(): xbmcplugin.addSortMethod(ADDON_HANDLE, method)
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
	debug_MS(f"(navigator.playVideo) ### URL = {API_DISCO}/playback/v3/videoPlaybackInfo ### IDD = {PLID} ###")
	STREAM, FINAL_URL, DRM_GUARD, DRM_SPECIES = (False for _ in range(4))
	payload = {'deviceInfo': {'adBlocker': False, 'drmSupported': True, 'hdrCapabilities': [], 'hwDecodingCapabilities': [], 'soundCapabilities': []}, 'wisteriaProperties': {}, 'videoId': str(PLID)}
	# NEW = https://public.aurora.enhanced.live/playback/v3/videoPlaybackInfo // OLD = https://eu1-prod.disco-api.com/playback/v3/videoPlaybackInfo
	DATA_ONE = Transmission().retrieveContent(f"{API_DISCO}/playback/v3/videoPlaybackInfo", 'POST', data=json.dumps(payload, indent=2))
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
			return listSeries(f"{API_DISCO}/content/shows?include=images,genres&sort=name", 1, 'overview_Favorites', WATCH['items'])
	return dialog.notification(translation(30528), translation(30529), icon, 8000)

def favorit_construct(**kwargs):
	TOPS = {}
	TOPS['items'] = []
	if xbmcvfs.exists(FAVORIT_FILE) and os.stat(FAVORIT_FILE).st_size > 0:
		TOPS = preserve(FAVORIT_FILE)
	if kwargs['action'] == 'ADD':
		del kwargs['mode']; del kwargs['action']
		TOPS['items'].append({key: value if value != 'None' else None for key, value in kwargs.items()})
		preserve(FAVORIT_FILE, TOPS)
		xbmc.sleep(500)
		dialog.notification(translation(30530), translation(30531).format(kwargs['name']), icon, 8000)
	elif kwargs['action'] == 'DEL':
		TOPS['items'] = [top for top in TOPS['items'] if top.get('url') != kwargs.get('url')]
		preserve(FAVORIT_FILE, TOPS)
		xbmc.executebuiltin('Container.Refresh')
		xbmc.sleep(1000)
		dialog.notification(translation(30530), translation(30532).format(kwargs['name']), icon, 8000)

def addDir(params, listitem, folder=True, handling='default'):
	uws, entries = build_mass(params), []
	listitem.setPath(uws)
	if handling == 'adding' and params:
		entries.append([translation(30651), f"RunPlugin({build_mass({**params, **{'mode': 'favorit_construct', 'action': 'ADD'}})})"])
	if handling == 'removing' and params:
		entries.append([translation(30652), f"RunPlugin({build_mass({**params, **{'mode': 'favorit_construct', 'action': 'DEL'}})})"])
	if len(entries) > 0: listitem.addContextMenuItems(entries)
	return xbmcplugin.addDirectoryItem(ADDON_HANDLE, uws, listitem, folder)

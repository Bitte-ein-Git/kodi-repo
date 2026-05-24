# -*- coding: utf-8 -*-

import sys
import os
import re
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
import json
import xbmcvfs
import shutil
import time
from datetime import datetime, timedelta
from calendar import timegm as TGM
import requests
from requests.adapters import HTTPAdapter
from urllib.parse import parse_qsl, urlencode, quote_plus, unquote_plus
from concurrent.futures import *
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


HOST_AND_PATH				= sys.argv[0]
ADDON_HANDLE				= int(sys.argv[1])
dialog									= xbmcgui.Dialog()
addon									= xbmcaddon.Addon()
addon_id							= addon.getAddonInfo('id')
addon_name						= addon.getAddonInfo('name')
addon_version					= addon.getAddonInfo('version')
addon_desc						= addon.getAddonInfo('description')
addon_folder						= xbmcvfs.translatePath(addon.getAddonInfo('path'))
addon_profile					= xbmcvfs.translatePath(addon.getAddonInfo('profile'))
FAVORIT_FILE						= xbmcvfs.translatePath(os.path.join(addon_profile, 'favorites_TLC.json'))
tempSTORE						= xbmcvfs.translatePath(os.path.join(addon_profile, 'tempSTORE', ''))
publicSECRET						= xbmcvfs.translatePath(os.path.join(tempSTORE, 'PUBLIC_SECRET'))
defaultFanart						= os.path.join(addon_folder, 'resources', 'media', 'fanart.jpg')
icon										= os.path.join(addon_folder, 'resources', 'media', 'icon.png')
artpic									= os.path.join(addon_folder, 'resources', 'media', '')
alppic									= os.path.join(addon_folder, 'resources', 'media', 'alphabet', '')
clamps_player					= (True if addon.getSetting('force_stopping') == 'true' else False)
courses								= int(addon.getSetting('sorting_technique'))
useThumbAsFanart			= addon.getSetting('use_fanart') == 'true'
enable_tune						= addon.getSetting('show_settings') == 'true'
DEB_LEVEL							= (xbmc.LOGINFO if addon.getSetting('enable_debug') == 'true' else xbmc.LOGDEBUG)
KODI_BUILD						= int(xbmc.getInfoLabel('System.BuildVersion')[0:2])
BASE_URL							= 'https://dmax.de/' # 'https://dmax.de/' = DMAX // 'https://de.hgtv.com/' = HGTV // 'https://tlc.de/' = TLC // 'https://tele5.de/' = TELE5
HEAD_WEB							= 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:150.0) Gecko/20100101 Firefox/150.0'
DEFAULT_HEADERS			= {'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json; charset=utf-8', 'DNT': '1', 'Accept-Encoding': 'gzip', \
	'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8', 'sec-ch-ua-platform': 'Windows', 'Origin': BASE_URL[:-1], 'Referer': BASE_URL}
STONE_HEADERS				= {**DEFAULT_HEADERS, **{'X-Device-Info': 'STONEJS/1 (Unknown/Unknown; Windows/NT 10.0; Unknown)', \
	'X-disco-client': 'WEB:UNKNOWN:wbdatv:2.1.9', 'X-disco-params': 'realm=de'}}
PUBIS_START						= 'https://public.aurora.enhanced.live'
PUBIS_ENDES						= f"include=default,advancedSearch&filter[environment]=dmaxde&v=2" # 'dmaxde' = DMAX // 'hgtvde' = HGTV // 'tlcde' = TLC // 'tele5' = TELE5
AURA_NORM						= f"{PUBIS_START}/site/page/sendungen/?{PUBIS_ENDES}"
AURA_HOME						= f"{PUBIS_START}/site/page/homepage/?{PUBIS_ENDES}"
AURA_SHOWS					= f"{PUBIS_START}/site/page/{{}}/?{PUBIS_ENDES}&parent_slug={{}}"
AURA_VIDEOS					= f"{PUBIS_START}/site/shows/{{}}/?{PUBIS_ENDES}"
AURA_SEARCH					= f"{PUBIS_START}/site/search/taxonomy/?{PUBIS_ENDES}&filter[slug]={{}}&page[size]=200"
AURA_PLAYER					= f"{PUBIS_START}/playback/v3/videoPlaybackInfo"
AURA_ACCESS					= f"{PUBIS_START}/token?realm=de" # https://public.aurora.enhanced.live/token?realm=de

xbmcplugin.setContent(ADDON_HANDLE, 'tvshows')

def translation(id):
	return addon.getLocalizedString(id)

def failing(content):
	log(content, xbmc.LOGERROR)

def debug_MS(content):
	log(content, DEB_LEVEL)

def log(msg, level=xbmc.LOGINFO):
	return xbmc.log(f"[{addon_id} v.{addon_version}]{str(msg)}", level)

def build_mass(body):
	return f"{HOST_AND_PATH}?{urlencode(body)}"

def plugin_operate(MARKING):
	check_uno = xbmc.executeJSONRPC(f'{{"jsonrpc":"2.0","id":1,"method":"Addons.GetAddonDetails","params":{{"addonid":"{MARKING}","properties":["enabled"]}}}}')
	answer_uno, answer_due = json.loads(check_uno), json.loads(f'{{"error": "{MARKING} NOT FOUND"}}')
	if not "error" in answer_uno.keys() and answer_uno.get('result', '') and answer_uno['result'].get('addon', {}).get('enabled', False) is False:
		try:
			xbmc.executeJSONRPC(f'{{"jsonrpc":"2.0","id":1,"method":"Addons.SetAddonEnabled","params":{{"addonid":"{MARKING}","enabled":true}}}}')
			failing(f"(common.plugin_operate) ERROR - ACTIVATED - ERROR :\n##### Das benötigte Addon : *{MARKING}* ist NICHT aktiviert !!! #####\n##### Es wird jetzt versucht die Aktivierung durchzuführen !!! #####")
		except: pass
		del answer_due
		check_due = xbmc.executeJSONRPC(f'{{"jsonrpc":"2.0","id":1,"method":"Addons.GetAddonDetails","params":{{"addonid":"{MARKING}","properties":["enabled"]}}}}')
		answer_due = json.loads(check_due)
	if (answer_uno.get('result', '') and answer_uno['result'].get('addon', {}).get('enabled', False) is True) or (answer_due.get('result', '') and answer_due['result'].get('addon', {}).get('enabled', False) is True):
		return True
	if answer_due.get('result', '') and answer_due['result'].get('addon', {}).get('enabled', False) is False:
		dialog.ok(addon_id, translation(30501).format(MARKING))
		failing(f"(common.plugin_operate) ERROR - ACTIVATED - ERROR :\n##### Das benötigte Addon : *{MARKING}* ist NICHT aktiviert !!! #####\n##### Eine automatische Aktivierung ist leider NICHT möglich !!! #####")
	if "error" in answer_uno.keys() or "error" in answer_due.keys():
		dialog.ok(addon_id, translation(30502).format(MARKING))
		failing(f"(common.plugin_operate) ERROR - INSTALLED - ERROR :\n##### Das benötigte Addon : *{MARKING}* ist NICHT installiert !!! #####")
	return False

def get_sorting():
	return [xbmcplugin.SORT_METHOD_UNSORTED, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE, xbmcplugin.SORT_METHOD_DURATION, xbmcplugin.SORT_METHOD_EPISODE, xbmcplugin.SORT_METHOD_DATE]

def convert_times(TIMING=None, ROUNDED=True, PLACES=3):
	DEMAND = float(int(round(TIMING*1000))) if ROUNDED is True else float(int(TIMING*1000))
	if ROUNDED is True and PLACES == 3:
		return str(timedelta(milliseconds=DEMAND))[: - PLACES]
	return str(timedelta(milliseconds=DEMAND))

def convert_region(info): # 2026-05-16T19:10:00+00:00
	CONVERTED = datetime(*(time.strptime(info[:19], '%Y-%m-%dT%H:%M:%S')[0:6]))
	try:
		LOCAL_DATE = datetime.fromtimestamp(TGM(CONVERTED.timetuple()))
		assert CONVERTED.resolution >= timedelta(microseconds=1)
		LOCAL_DATE = LOCAL_DATE.replace(microsecond=CONVERTED.microsecond)
	except (ValueError, OverflowError): # ERROR on Android 32bit Systems = cannot convert unix timestamp over year 2038
		LOCAL_DATE = datetime.fromtimestamp(0) + timedelta(seconds=TGM(CONVERTED.timetuple()))
		LOCAL_DATE = LOCAL_DATE - timedelta(hours=datetime.timetuple(LOCAL_DATE).tm_isdst)
	return LOCAL_DATE

def preserve(store, facts=None, arrive=None):
	if facts is not None:
		with open(store, 'w') as topics:
			json.dump(facts, topics, indent=2, sort_keys=True)
	else:
		if xbmcvfs.exists(store) and os.path.exists(store) and os.stat(store).st_size > 0:
			with open(store, 'r') as topics:
				arrive = json.load(topics)
		return arrive

def clear_umlaut(changes):
	if changes is not None:
		for cm in (('Ä', 'Ae'), ('ä', 'ae'), ('Ö', 'Oe'), ('ö', 'oe'), ('Ü', 'Ue'), ('ü', 'ue'), ('ß', 'ss')):
			changes = changes.replace(*cm)
		changes = changes.strip()
	return changes

def clear_invalid(changes):
	if changes is not None: # Ersetze den Umlaut und bestimmte Zeichen, um einen Slug für die entsprechende TV-Show für den Weiterleitungs-Link zu generieren
		for cn in (('Ä', 'Ae'), ('ä', 'ae'), ('Ö', 'Oe'), ('ö', 'oe'), ('Ü', 'Ue'), ('ü', 'ue'), ('ß', 'ss'), ('&', 'und'), (',', ''), ('.', ''), (':', ''), ('!', ''), ('?', ''), ('(', ''), (')', ''),  (' - ', '-'), (' ', '-'), ('--', '-')):
			changes = changes.replace(*cn)
		changes = changes.strip()
	return changes

def cleaning(text):
	if text is not None:
		for tx in (('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&'), ('&Amp;', '&'), ('&apos;', "'"), ("&quot;", "\""), ("&Quot;", "\""), ('&szlig;', 'ß'), ('&mdash;', '-'), ('&ndash;', '-'), ('&nbsp;', ' '), ('&hellip;', '...'), ('\xc2\xb7', '-'),
			("&#x27;", "'"), ('&#34;', '"'), ('&#39;', '\''), ('&#039;', '\''), ('&#x00c4', 'Ä'), ('&#x00e4', 'ä'), ('&#x00d6', 'Ö'), ('&#x00f6', 'ö'), ('&#x00dc', 'Ü'), ('&#x00fc', 'ü'), ('&#x00df', 'ß'), ('&#xD;', ''),
			('&#xC4;', 'Ä'), ('&#xE4;', 'ä'), ('&#xD6;', 'Ö'), ('&#xF6;', 'ö'), ('&#xDC;', 'Ü'), ('&#xFC;', 'ü'), ('&#xDF;', 'ß'), ('&#x201E;', '„'), ('&#xB4;', '´'), ('&#x2013;', '-'), ('&#xA0;', ' '),
			('&Auml;', 'Ä'), ('&Euml;', 'Ë'), ('&Iuml;', 'Ï'), ('&Ouml;', 'Ö'), ('&Uuml;', 'Ü'), ('&auml;', 'ä'), ('&euml;', 'ë'), ('&iuml;', 'ï'), ('&ouml;', 'ö'), ('&uuml;', 'ü'), ('&#376;', 'Ÿ'), ('&yuml;', 'ÿ'),
			("&rsquo;", "’"), ("&lsquo;", "‘"), ("&sbquo;", "’"), ('&rdquo;', '”'), ('&ldquo;', '“'), ('&bdquo;', '”'), ('&rsaquo;', '›'), ('lsaquo;', '‹'), ('&raquo;', '»'), ('&laquo;', '«'), ('\n', ' '), ('<br>', '[CR]'), ('</p><p>', '[CR]'),
			('\\xC4', 'Ä'), ('\\xE4', 'ä'), ('\\xD6', 'Ö'), ('\\xF6', 'ö'), ('\\xDC', 'Ü'), ('\\xFC', 'ü'), ('\\xDF', 'ß'), ('\\x201E', '„'), ('\\x28', '('), ('\\x29', ')'), ('\\x2F', '/'), ('\\x2D', '-'), ('\\x20', ' '), ('\\x3A', ':'), ("\\'", "'")):
			text = text.replace(*tx)
		text = re.sub(r'\<.*?\>', '', text).strip()
	return text

def create_entries(metadata, entries='DEFAULT', persist=1):
	if entries == 'COLLATE':
		#log(f"(common.create_entries[1]) xxxxx METAS-01 : {metadata} xxxxx")
		shorten = metadata['Contents'] if metadata.get('Contents', {}) else metadata
		series, showSlug, local_start, start_times, starting, airing, local_ends, ends_times, mpaa = (None for _ in range(9))
		collate, (note_1, note_2) = '2026-01-01T00:01', ("" for _ in range(2))
		title, episSlug = cleaning(shorten['title']), (shorten.get('alternateId', None) or shorten.get('url', None))
		show_title = (shorten.get('show', {}).get('title', '') or metadata.get('SeriesTitle', ''))
		series, showSlug = cleaning(show_title), clear_invalid(show_title).lower()
		episID, showID = shorten.get('id', None), (shorten.get('show', {}).get('id', '') or shorten.get('showId', '') or None)
		model = shorten.get('videoType', 'UNKNOWN')
		duration = int(shorten['videoDuration']) // 1000 if str(shorten.get('videoDuration')).isdecimal() else None
		season = f"{int(shorten['seasonNumber']):02}" if str(shorten.get('seasonNumber')).isdecimal() and int(shorten['seasonNumber']) != 0 else None
		episode = f"{int(shorten['episodeNumber']):02}" if str(shorten.get('episodeNumber')).isdecimal() and int(shorten['episodeNumber']) != 0 else None
		if shorten.get('contentRating', '') and str(shorten['contentRating'].get('code')).isdecimal():
			mpaa = translation(30623).format(shorten['contentRating']['code']) if str(shorten['contentRating']['code']) != '0' else translation(30624)
		if str(shorten.get('publishStart'))[:4].isdecimal():
			local_start = convert_region(shorten['publishStart'])
			start_times = local_start.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
			collate = local_start.strftime('%Y-%m-%dT%H:%M')
			starting = local_start.strftime('%Y-%m-%dT%H:%M') if KODI_BUILD >= 20 else LOCALstart.strftime('%d.%m.%Y') # 2026-05-16T19:10:00 = NEWFORMAT // 16.05.2026 = OLDFORMAT
			airing = local_start.strftime('%d.%m.%Y') # FirstAired
		if str(shorten.get('publishEnd'))[:4].isdecimal():
			local_ends = convert_region(shorten['publishEnd'])
			ends_times = local_ends.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
		if start_times and ends_times: note_1 = translation(30625).format(start_times, ends_times)
		elif start_times and ends_times is None: note_1 = translation(30626).format(start_times)
		elif start_times is None and ends_times is None: note_1 = '[CR]'
		thumb = shorten['poster']['src'] if shorten.get('poster', '') and shorten['poster'].get('src', '') else \
			shorten['meta']['thumbnailUrl'] if shorten.get('meta', '') and shorten['meta'].get('thumbnailUrl', '') else f"{artpic}standard.png"
		note_2 = shorten['description'] if shorten.get('description', '') and len(shorten['description']) > 20 else shorten['meta']['description'] if \
			shorten.get('meta', '') and shorten['meta'].get('description', '') and len(shorten['meta']['description']) > 20 else ""
		species = ' / '.join(sorted([tax.get('title', '') for tax in shorten.get('taxonomies', {}) if tax.get('category') == 'genre'][:2]))
		pioneer, medias = translation(30627).format(season, episode) if season and episode else None, 'episode' if season and episode else 'movie'
		suffix = translation(30629) if local_start and local_start > (datetime.now() - timedelta(days=7, hours=2)) else \
			translation(30630) if local_ends and local_ends < (datetime.now() + timedelta(days=7, hours=2)) else ""
		full_name= f"{pioneer} {title}{suffix}" if pioneer else f"{title}{suffix}"
		teaser, short_name = f"{series}[CR]{note_1}{note_2}" if series else note_1+note_2, re.sub(r'\[.*?\]', '', full_name)
		debug_MS("* * * * * * * * * * * * * * * * * * * * * * *")
		debug_MS(f"(navigator.list_episodes[3]) ##### POSITION : {persist} || NAME : {short_name} || IDD : {episID} || DURATION : {duration} #####")
		debug_MS(f"(navigator.list_episodes[3]) ##### START : {collate} || SEASON : {season} || EPISODE : {episode} || MPAA : {mpaa} #####")
		debug_MS(f"(navigator.list_episodes[3]) ##### SERIE : {series} || IMAGE : {thumb} #####")
		metadata = {'Title': full_name, 'TvShowTitle': series, 'Plot': teaser, 'Season': season,'Episode': episode, 'Duration': duration, \
			'Date': starting, 'Aired': airing, 'Genre': species, 'Mpaa': mpaa, 'Mediatype': medias, 'Image': thumb, 'Reference': 'Single'}
	listitem = xbmcgui.ListItem(metadata['Title'])
	vinfo = listitem.getVideoInfoTag() if KODI_BUILD >= 20 else {}
	if KODI_BUILD >= 20: vinfo.setTitle(metadata['Title'])
	else: vinfo['Title'] = metadata['Title']
	if metadata.get('TvShowTitle', ''):
		if KODI_BUILD >= 20: vinfo.setTvShowTitle(metadata['TvShowTitle'])
		else: vinfo['Tvshowtitle'] = metadata['TvShowTitle']
	description = metadata['Plot'] if metadata.get('Plot') not in ['', 'None', None] else ' '
	if KODI_BUILD >= 20: vinfo.setPlot(description)
	else: vinfo['Plot'] = description
	if str(metadata.get('Duration')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setDuration(int(metadata['Duration']))
		else: vinfo['Duration'] = metadata['Duration']
	if str(metadata.get('Season')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setSeason(int(metadata['Season']))
		else: vinfo['Season'] = metadata['Season']
	if str(metadata.get('Episode')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setEpisode(int(metadata['Episode']))
		else: vinfo['Episode'] = metadata['Episode']
	if metadata.get('Date', ''):
		if KODI_BUILD >= 20: listitem.setDateTime(metadata['Date'])
		else: vinfo['Date'] = metadata['Date']
	if metadata.get('Aired', ''):
		if KODI_BUILD >= 20: vinfo.setFirstAired(metadata['Aired'])
		else: vinfo['Aired'] = metadata['Aired']
	if str(metadata.get('Aired'))[6:10].isdecimal():
		if KODI_BUILD >= 20: vinfo.setYear(int(metadata['Aired'][6:10]))
		else: vinfo['Year'] = metadata['Aired'][6:10]
	if metadata.get('Genre', ''):
		if KODI_BUILD >= 20: vinfo.setGenres([metadata['Genre']])
		else: vinfo['Genre'] = metadata['Genre']
	if metadata.get('Mpaa', ''):
		if KODI_BUILD >= 20: vinfo.setMpaa(metadata['Mpaa'])
		else: vinfo['Mpaa'] = metadata['Mpaa']
	if metadata.get('Mediatype', ''):
		if KODI_BUILD >= 20: vinfo.setMediaType(metadata['Mediatype'])
		else: vinfo['Mediatype'] = metadata['Mediatype']
	picture = metadata['Image'] if metadata.get('Image') else f"{artpic}standard.png"
	listitem.setArt({'icon': icon, 'thumb': picture, 'poster': picture, 'fanart': defaultFanart})
	if metadata.get('Cover'): listitem.setArt({'poster': metadata['Cover']})
	if useThumbAsFanart and not artpic in picture:
		listitem.setArt({'fanart': picture})
	if metadata.get('Reference') == 'Single':
		listitem.setProperty('IsPlayable', 'true')
	if KODI_BUILD < 20: listitem.setInfo('Video', vinfo)
	return listitem

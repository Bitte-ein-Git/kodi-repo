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
import base64
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
FAVORIT_FILE						= xbmcvfs.translatePath(os.path.join(addon_profile, 'favorites_DMAX.json'))
tempSTORE						= xbmcvfs.translatePath(os.path.join(addon_profile, 'tempSTORE', ''))
publicSECRET						= xbmcvfs.translatePath(os.path.join(tempSTORE, 'PUBLIC_SECRET'))
defaultFanart						= os.path.join(addon_folder, 'resources', 'media', 'fanart.jpg')
icon										= os.path.join(addon_folder, 'resources', 'media', 'icon.png')
artpic									= os.path.join(addon_folder, 'resources', 'media', '')
alppic									= os.path.join(addon_folder, 'resources', 'media', 'alphabet', '')
clamps_player					= (True if addon.getSetting('force_stopping') == 'true' else False)
complete_titles					= addon.getSetting('complete_titles') == 'true'
titles_layout						= int(addon.getSetting('titles_layout'))
courses								= int(addon.getSetting('sorting_technique'))
using_fanart						= addon.getSetting('use_fanart') == 'true'
enable_tune						= addon.getSetting('show_settings') == 'true'
DEB_LEVEL							= (xbmc.LOGINFO if addon.getSetting('enable_debug') == 'true' else xbmc.LOGDEBUG)
KODI_BUILD						= int(xbmc.getInfoLabel('System.BuildVersion')[0:2])
BASE_URL							= 'https://dmax.de/' # 'https://dmax.de/' = DMAX // 'https://de.hgtv.com/' = HGTV // 'https://tlc.de/' = TLC // 'https://tele5.de/' = TELE5
WEB_AGENT						= 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:153.0) Gecko/20100101 Firefox/153.0'
DEFAULT_HEADERS			= {'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json; charset=utf-8', 'DNT': '1', 'Accept-Encoding': 'gzip, deflate', \
	'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8', 'sec-ch-ua-platform': 'Windows', 'Origin': BASE_URL[:-1], 'Referer': BASE_URL}
STONE_HEADERS				= {**DEFAULT_HEADERS, **{'X-Device-Info': 'STONEJS/1 (Unknown/Unknown; Windows/NT 10.0; Unknown)', \
	'X-disco-client': 'WEB:UNKNOWN:wbdatv:2.1.9', 'X-disco-params': 'realm=de'}}
CLOUD_ARTS						= 'https://d2v9mhsiek5lbq.cloudfront.net/'
CLOUD_TVIS						= f'{{"bucket":"loma-media-de","key":"{{code}}","edits":{{"resize":{{"fit":"cover","width":{{size}}}},"jpeg":{{"quality":85}}}}}}'
CLOUD_EPIS						= f'{{"bucket":"aurora-content-images","key":"{{code}}","edits":{{"resize":{{"fit":"cover","width":{{size}}}},"jpeg":{{"quality":80}}}}}}'
PUBIS_START						= 'https://public.aurora.enhanced.live'
PUBIS_ENDES						= f"include=default,advancedSearch&filter[environment]=dmaxde&v=2" # 'dmaxde' = DMAX // 'hgtvde' = HGTV // 'tlcde' = TLC // 'tele5' = TELE5
AURA_NORM						= f"{PUBIS_START}/site/page/sendungen/?{PUBIS_ENDES}"
AURA_HOME						= f"{PUBIS_START}/site/page/homepage/?{PUBIS_ENDES}"
AURA_ITEMS						= f"{PUBIS_START}/site/page/{{}}/?{PUBIS_ENDES}&parent_slug=sendungen"
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

def create_entries(metas, version='DEFAULT', persist=1):
	if version in ['COLLECT', 'NEWEST']:
		metas = {key: value for key, value in metas.items() if value is not None}
		#log(f"(common.create_entries[1]) xxxxx METAS-01 : {metas} xxxxx")
		show_name, showSlug, mpaa, local_start, start_times, starting, airing, local_ends, ends_times, species = (None for _ in range(10))
		collate, (note_1, note_2) = '2026-01-01T00:01', ("" for _ in range(2))
		titling, episSlug = cleaning(metas['title']), (metas.get('alternateId', None) or metas.get('url', None))
		show_title = (metas.get('show', {}).get('title', '') or metas.get('ShowTitle', ''))
		show_name, showSlug = cleaning(show_title), (metas.get('Slug_2', '') or clear_invalid(show_title).lower())
		episID, showID = metas.get('id', None), (metas.get('show', {}).get('id', '') or metas.get('showId', '') or None)
		model = metas.get('videoType', 'UNKNOWN')
		duration = int(metas['videoDuration']) // 1000 if str(metas.get('videoDuration')).isdecimal() else None
		season = f"{int(metas['seasonNumber']):02}" if str(metas.get('seasonNumber')).isdecimal() and int(metas['seasonNumber']) != 0 else None
		episode = f"{int(metas['episodeNumber']):02}" if str(metas.get('episodeNumber')).isdecimal() and int(metas['episodeNumber']) != 0 else None
		if str(metas.get('contentRating', {}).get('code')).isdecimal():
			mpaa = translation(30623).format(metas['contentRating']['code']) if str(metas['contentRating']['code']) != '0' else translation(30624)
		if str(metas.get('publishStart'))[:4].isdecimal():
			local_start = convert_region(metas['publishStart'])
			start_times = local_start.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
			collate = local_start.strftime('%Y-%m-%dT%H:%M')
			starting = local_start.strftime('%Y-%m-%dT%H:%M') if KODI_BUILD >= 20 else LOCALstart.strftime('%d.%m.%Y') # 2026-05-16T19:10:00 = NEWFORMAT // 16.05.2026 = OLDFORMAT
			airing = local_start.strftime('%d.%m.%Y') # FirstAired
		if str(metas.get('publishEnd'))[:4].isdecimal():
			local_ends = convert_region(metas['publishEnd'])
			ends_times = local_ends.strftime('%d{0}%m{0}%y {1} %H{2}%M').format('.', '•', ':')
		if start_times and ends_times: note_1 = translation(30625).format(start_times, ends_times)
		elif start_times and ends_times is None: note_1 = translation(30626).format(start_times)
		thumb = (metas.get('poster', {}).get('src', None) or metas.get('meta', {}).get('thumbnailUrl', None))
		if thumb: thumb = CLOUD_ARTS+base64.urlsafe_b64encode(CLOUD_EPIS.replace('{code}', thumb.split('nced.live/')[1]).replace('{size}', '1920').encode()).decode()
		story = metas['description'] if metas.get('description', None) else ""
		note_2 = cleaning(story) if len(story) > 20 else metas.get('ShowTeaser', '')
		if metas.get('show', {}).get('taxonomies', ''):
			species = ' / '.join(sorted([tax.get('title', '').title() for tax in metas['show']['taxonomies'] if tax.get('category') == 'genre'][:2]))
		pioneer, tables = translation(30627).format(season, episode, titling) if season and episode else titling, 'episode' if season and episode else 'movie'
		suffix = translation(30629) if local_start and local_start > (datetime.now() - timedelta(days=7, hours=2)) else \
			translation(30630) if local_ends and local_ends < (datetime.now() + timedelta(days=7, hours=2)) else ""
		full_name = f"{pioneer}{suffix}" if version != 'NEWEST' else pioneer
		if version == 'NEWEST' and complete_titles and show_name:
			prefix = f"{pioneer.split('[/COLOR]')[0]}[/COLOR]" if '[/COLOR]' in pioneer else pioneer
			full_name = f"{pioneer} - {show_name}" if titles_layout == 0 else f"{prefix}{show_name} - {titling}"
		teaser = f"{show_name}[CR]{note_1}{note_2}" if show_name and note_1 != "" else f"{show_name}[CR][CR]{note_2}" if show_name and note_1 == "" else note_1+note_2
		short_name = re.sub(r'\[.*?\]', '', full_name)
		debug_MS("* * * * * * * * * * * * * * * * * * * * * * *")
		debug_MS(f"(navigator.list_episodes[3]) ##### POSITION : {persist} || NAME : {short_name} || IDD : {episID} || DURATION : {duration} #####")
		debug_MS(f"(navigator.list_episodes[3]) ##### START : {collate} || SEASON : {season} || EPISODE : {episode} || MPAA : {mpaa} #####")
		debug_MS(f"(navigator.list_episodes[3]) ##### SERIE : {show_name} || IMAGE : {thumb} #####")
		metas = {'Title': full_name, 'TvShowTitle': show_name, 'Plot': teaser, 'Season': season,'Episode': episode, 'Duration': duration, \
			'Date': starting, 'Aired': airing, 'Genre': species, 'Mpaa': mpaa, 'Mediatype': tables, 'Image': thumb, 'Reference': 'Single'}
	listitem = xbmcgui.ListItem(metas['Title'])
	vinfo = listitem.getVideoInfoTag() if KODI_BUILD >= 20 else {}
	if KODI_BUILD >= 20: vinfo.setTitle(metas['Title'])
	else: vinfo['Title'] = metas['Title']
	if metas.get('TvShowTitle', ''):
		if KODI_BUILD >= 20: vinfo.setTvShowTitle(metas['TvShowTitle'])
		else: vinfo['Tvshowtitle'] = metas['TvShowTitle']
	description = metas['Plot'] if metas.get('Plot') not in ['', 'None', None] else ' '
	if KODI_BUILD >= 20: vinfo.setPlot(description)
	else: vinfo['Plot'] = description
	if str(metas.get('Duration')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setDuration(int(metas['Duration']))
		else: vinfo['Duration'] = metas['Duration']
	if str(metas.get('Season')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setSeason(int(metas['Season']))
		else: vinfo['Season'] = metas['Season']
	if str(metas.get('Episode')).isdecimal():
		if KODI_BUILD >= 20: vinfo.setEpisode(int(metas['Episode']))
		else: vinfo['Episode'] = metas['Episode']
	if metas.get('Date', ''):
		if KODI_BUILD >= 20: listitem.setDateTime(metas['Date'])
		else: vinfo['Date'] = metas['Date']
	if metas.get('Aired', ''):
		if KODI_BUILD >= 20: vinfo.setFirstAired(metas['Aired'])
		else: vinfo['Aired'] = metas['Aired']
	if str(metas.get('Aired'))[6:10].isdecimal():
		if KODI_BUILD >= 20: vinfo.setYear(int(metas['Aired'][6:10]))
		else: vinfo['Year'] = metas['Aired'][6:10]
	if metas.get('Genre', ''):
		if KODI_BUILD >= 20: vinfo.setGenres([metas['Genre']])
		else: vinfo['Genre'] = metas['Genre']
	if metas.get('Mpaa', ''):
		if KODI_BUILD >= 20: vinfo.setMpaa(str(metas['Mpaa']))
		else: vinfo['Mpaa'] = str(metas['Mpaa'])
	if metas.get('Mediatype', ''):
		if KODI_BUILD >= 20: vinfo.setMediaType(metas['Mediatype'])
		else: vinfo['Mediatype'] = metas['Mediatype']
	picture = metas['Image'] if metas.get('Image') else f"{artpic}standard.png"
	listitem.setArt({'icon': icon, 'thumb': picture, 'poster': picture, 'fanart': defaultFanart})
	if metas.get('Cover'): listitem.setArt({'poster': metas['Cover']})
	if using_fanart and picture and not artpic in picture:
		listitem.setArt({'fanart': picture})
	if metas.get('Reference') == 'Single':
		listitem.setProperty('IsPlayable', 'true')
	if KODI_BUILD < 20: listitem.setInfo('Video', vinfo)
	return listitem

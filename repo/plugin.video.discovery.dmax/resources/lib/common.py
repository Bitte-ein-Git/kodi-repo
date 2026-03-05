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
import ssl
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
addonPath							= xbmcvfs.translatePath(addon.getAddonInfo('path')).encode('utf-8').decode('utf-8')
dataPath								= xbmcvfs.translatePath(addon.getAddonInfo('profile')).encode('utf-8').decode('utf-8')
FAVORIT_FILE						= xbmcvfs.translatePath(os.path.join(dataPath, 'favorites_DMAX.json'))
tempSTORE						= xbmcvfs.translatePath(os.path.join(dataPath, 'tempSTORE', '')).encode('utf-8').decode('utf-8')
storeSECRET						= xbmcvfs.translatePath(os.path.join(tempSTORE, 'FREE_SECRET'))
defaultFanart						= os.path.join(addonPath, 'resources', 'media', 'fanart.jpg')
icon										= os.path.join(addonPath, 'resources', 'media', 'icon.png')
artpic									= os.path.join(addonPath, 'resources', 'media', '').encode('utf-8').decode('utf-8')
alppic									= os.path.join(addonPath, 'resources', 'media', 'alphabet', '').encode('utf-8').decode('utf-8')
FORCE_PLAYER					= (True if addon.getSetting('force_stopping') == 'true' else False)
SORTING							= int(addon.getSetting('sorting_technique'))
useThumbAsFanart			= addon.getSetting('use_fanart') == 'true'
enableADJUSTMENT			= addon.getSetting('show_settings') == 'true'
DEB_LEVEL							= (xbmc.LOGINFO if addon.getSetting('enable_debug') == 'true' else xbmc.LOGDEBUG)
KODI_ov20							= int(xbmc.getInfoLabel('System.BuildVersion')[0:2]) >= 20
KODI_un21							= int(xbmc.getInfoLabel('System.BuildVersion')[0:2]) <= 20
DISCO_CHANNEL				= '94' # '94' = DMAX // '148' = HGTV // '95' = TLC // '626' = TELE5
PUBLIC_CHANNEL				= 'dmaxde' # 'dmaxde' = DMAX // 'hgtvde' = HGTV // 'tlcde' = TLC // 'tele5' = TELE5
DISCO_REALM					= 'dmaxde' # 'dmaxde' = DMAX // 'hgtv' = HGTV // 'tlcde' = TLC // 'dmaxde' = TELE5
PUBLIC_REALM					= 'de' # https://public.aurora.enhanced.live/token?realm=de
PUBLIC_HOST					= 'https://public.aurora.enhanced.live'
AURORA_DEFAULT			= f"{PUBLIC_HOST}/site/page/sendungen/?include=default,advancedSearch&filter[environment]={PUBLIC_CHANNEL}&v=2"
AURORA_SEARCH				= f"{AURORA_DEFAULT.replace('/page/sendungen/', '/search/taxonomy/')}&filter[slug]={{}}&page[size]=200"
DISCO_HOST						= 'https://eu1-prod.disco-api.com'
EUAPI_SHOWS					= f"{DISCO_HOST}/content/shows?include=images,genres"
EUAPI_VIDEOS					= f"{DISCO_HOST}/content/videos?include=show,images,genres"
ACCESS_URL						= f"{DISCO_HOST}/token?realm={DISCO_REALM}"
BASE_URL							= 'https://dmax.de/'
agent_WEB							= 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:147.0) Gecko/20100101 Firefox/147.0'

xbmcplugin.setContent(ADDON_HANDLE, 'tvshows')

def py3_dec(d, nom='utf-8', ign='ignore'):
	if isinstance(d, bytes):
		d = d.decode(nom, ign)
	return d

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

def get_CentralTime(info): # 2024-05-05T19:10:00Z
	CONVERTED = datetime(*(time.strptime(info[:19], '%Y-%m-%dT%H:%M:%S')[0:6]))
	try:
		LOCAL_DATE = datetime.fromtimestamp(TGM(CONVERTED.timetuple()))
		assert CONVERTED.resolution >= timedelta(microseconds=1)
		LOCAL_DATE = LOCAL_DATE.replace(microsecond=CONVERTED.microsecond)
	except (ValueError, OverflowError): # ERROR on Android 32bit Systems = cannot convert unix timestamp over year 2038
		LOCAL_DATE = datetime.fromtimestamp(0) + timedelta(seconds=TGM(CONVERTED.timetuple()))
		LOCAL_DATE = LOCAL_DATE - timedelta(hours=datetime.timetuple(LOCAL_DATE).tm_isdst)
	return LOCAL_DATE

def get_RunTime(info, event='SECONDS'):
	if event == 'SECONDS':
		return "{0:.0f}".format(int(info) // 1000)
	return "{0:.0f}".format(round(timedelta(milliseconds=int(info)) / timedelta(minutes=1)))

def convert_times(TIMING=None, ROUNDED=True, PLACES=3):
	DEMAND = float(int(round(TIMING*1000))) if ROUNDED is True else float(int(TIMING*1000))
	if ROUNDED is True and PLACES == 3:
		return str(timedelta(milliseconds=DEMAND))[: - PLACES]
	return str(timedelta(milliseconds=DEMAND))

def preserve(storage, content=None):
	if content is not None:
		with open(storage, 'w') as topics:
			json.dump(content, topics, indent=2, sort_keys=True)
	else:
		with open(storage, 'r') as topics:
			arrive = json.load(topics)
		return arrive

def clear_umlaut(changes):
	if changes is not None:
		for cm in (('Ä', 'Ae'), ('ä', 'ae'), ('Ö', 'Oe'), ('ö', 'oe'), ('Ü', 'Ue'), ('ü', 'ue'), ('ß', 'ss')):
			changes = changes.replace(*cm)
		changes = changes.strip()
	return changes

def clear_invalid(changes):
	if changes is not None: # Replace Umlaut to Single Letter (AURORA=escape-vermaechtnis-der-wikinger -> DISCO=escape-vermachtnis-der-wikinger)
		for cn in (('Ae', 'A'), ('ae', 'a'), ('Oe', 'O'), ('oe', 'o'), ('Ue', 'U'), ('ue', 'u'), ('ss', '')):
			changes = changes.replace(*cn)
		changes = changes.strip()
	return changes

def cleaning(text):
	if text is not None:
		for tx in (('&lt;', '<'), ('&gt;', '>'), ('&amp;', '&'), ('&Amp;', '&'), ('&apos;', "'"), ("&quot;", "\""), ("&Quot;", "\""), ('&szlig;', 'ß'), ('&mdash;', '-'), ('&ndash;', '-'), ('&nbsp;', ' '), ('&hellip;', '...'), ('\xc2\xb7', '-'),
			("&#x27;", "'"), ('&#34;', '"'), ('&#39;', '\''), ('&#039;', '\''), ('&#x00c4', 'Ä'), ('&#x00e4', 'ä'), ('&#x00d6', 'Ö'), ('&#x00f6', 'ö'), ('&#x00dc', 'Ü'), ('&#x00fc', 'ü'), ('&#x00df', 'ß'), ('&#xD;', ''),
			('&#xC4;', 'Ä'), ('&#xE4;', 'ä'), ('&#xD6;', 'Ö'), ('&#xF6;', 'ö'), ('&#xDC;', 'Ü'), ('&#xFC;', 'ü'), ('&#xDF;', 'ß'), ('&#x201E;', '„'), ('&#xB4;', '´'), ('&#x2013;', '-'), ('&#xA0;', ' '),
			('&Auml;', 'Ä'), ('&Euml;', 'Ë'), ('&Iuml;', 'Ï'), ('&Ouml;', 'Ö'), ('&Uuml;', 'Ü'), ('&auml;', 'ä'), ('&euml;', 'ë'), ('&iuml;', 'ï'), ('&ouml;', 'ö'), ('&uuml;', 'ü'), ('&#376;', 'Ÿ'), ('&yuml;', 'ÿ'),
			('&agrave;', 'à'), ('&Agrave;', 'À'), ('&aacute;', 'á'), ('&Aacute;', 'Á'), ('&acirc;', 'â'), ('&Acirc;', 'Â'), ('&egrave;', 'è'), ('&Egrave;', 'È'), ('&eacute;', 'é'), ('&Eacute;', 'É'), ('&ecirc;', 'ê'), ('&Ecirc;', 'Ê'),
			('&igrave;', 'ì'), ('&Igrave;', 'Ì'), ('&iacute;', 'í'), ('&Iacute;', 'Í'), ('&icirc;', 'î'), ('&Icirc;', 'Î'), ('&ograve;', 'ò'), ('&Ograve;', 'Ò'), ('&oacute;', 'ó'), ('&Oacute;', 'Ó'), ('&ocirc;', 'ô'), ('&Ocirc;', 'Ô'),
			('&ugrave;', 'ù'), ('&Ugrave;', 'Ù'), ('&uacute;', 'ú'), ('&Uacute;', 'Ú'), ('&ucirc;', 'û'), ('&Ucirc;', 'Û'), ('&yacute;', 'ý'), ('&Yacute;', 'Ý'),
			('&atilde;', 'ã'), ('&Atilde;', 'Ã'), ('&ntilde;', 'ñ'), ('&Ntilde;', 'Ñ'), ('&otilde;', 'õ'), ('&Otilde;', 'Õ'), ('&Scaron;', 'Š'), ('&scaron;', 'š'), ('&ccedil;', 'ç'), ('&Ccedil;', 'Ç'),
			('&alpha;', 'a'), ('&Alpha;', 'A'), ('&aring;', 'å'), ('&Aring;', 'Å'), ('&aelig;', 'æ'), ('&AElig;', 'Æ'), ('&epsilon;', 'e'), ('&Epsilon;', 'Ε'), ('&eth;', 'ð'), ('&ETH;', 'Ð'), ('&gamma;', 'g'), ('&Gamma;', 'G'),
			('&oslash;', 'ø'), ('&Oslash;', 'Ø'), ('&theta;', 'θ'), ('&thorn;', 'þ'), ('&THORN;', 'Þ'), ('&bull;', '•'), ('&iexcl;', '¡'), ('&iquest;', '¿'), ('&copy;', '(c)'), ('\t', '    '), ('<br />', ' - '), ('</p>\n<p></p>', ''),
			("&rsquo;", "’"), ("&lsquo;", "‘"), ("&sbquo;", "’"), ('&rdquo;', '”'), ('&ldquo;', '“'), ('&bdquo;', '”'), ('&rsaquo;', '›'), ('lsaquo;', '‹'), ('&raquo;', '»'), ('&laquo;', '«'), ('<p></p><p>', '[CR][CR]'),
			('\\xC4', 'Ä'), ('\\xE4', 'ä'), ('\\xD6', 'Ö'), ('\\xF6', 'ö'), ('\\xDC', 'Ü'), ('\\xFC', 'ü'), ('\\xDF', 'ß'), ('\\x201E', '„'), ('\\x28', '('), ('\\x29', ')'), ('\\x2F', '/'), ('\\x2D', '-'), ('\\x20', ' '), ('\\x3A', ':'), ("\\'", "'")):
			text = text.replace(*tx)
		text = re.sub(r'\<.*?\>', '', text)
		text = text.strip()
	return text

def create_entries(metadata, SIGNS=None):
	listitem = xbmcgui.ListItem(metadata['Title'])
	vinfo = listitem.getVideoInfoTag() if KODI_ov20 else {}
	if KODI_ov20: vinfo.setTitle(metadata['Title'])
	else: vinfo['Title'] = metadata['Title']
	if metadata.get('TvShowTitle', ''):
		if KODI_ov20: vinfo.setTvShowTitle(metadata['TvShowTitle'])
		else: vinfo['Tvshowtitle'] = metadata['TvShowTitle']
	description = metadata['Plot'] if metadata.get('Plot') not in ['', 'None', None] else ' '
	if KODI_ov20: vinfo.setPlot(description)
	else: vinfo['Plot'] = description
	if str(metadata.get('Duration')).isdecimal():
		if KODI_ov20: vinfo.setDuration(int(metadata['Duration']))
		else: vinfo['Duration'] = metadata['Duration']
	if str(metadata.get('Season')).isdecimal():
		if KODI_ov20: vinfo.setSeason(int(metadata['Season']))
		else: vinfo['Season'] = metadata['Season']
	if str(metadata.get('Episode')).isdecimal():
		if KODI_ov20: vinfo.setEpisode(int(metadata['Episode']))
		else: vinfo['Episode'] = metadata['Episode']
	if metadata.get('Date', ''):
		if KODI_ov20: listitem.setDateTime(metadata['Date'])
		else: vinfo['Date'] = metadata['Date']
	if metadata.get('Aired', ''):
		if KODI_ov20: vinfo.setFirstAired(metadata['Aired'])
		else: vinfo['Aired'] = metadata['Aired']
	if str(metadata.get('Year')).isdecimal():
		if KODI_ov20: vinfo.setYear(int(metadata['Year']))
		else: vinfo['Year'] = metadata['Year']
	if metadata.get('Genre', ''):
		if KODI_ov20: vinfo.setGenres([metadata['Genre']])
		else: vinfo['Genre'] = metadata['Genre']
	if metadata.get('Mpaa', ''):
		if KODI_ov20: vinfo.setMpaa(metadata['Mpaa'])
		else: vinfo['Mpaa'] = metadata['Mpaa']
	if metadata.get('Mediatype', ''):
		if KODI_ov20: vinfo.setMediaType(metadata['Mediatype'])
		else: vinfo['Mediatype'] = metadata['Mediatype']
	picture = metadata['Image'] if metadata.get('Image') else f"{artpic}standard.png"
	listitem.setArt({'icon': icon, 'thumb': picture, 'poster': picture, 'fanart': defaultFanart})
	if metadata.get('Cover'): listitem.setArt({'poster': metadata['Cover']})
	if useThumbAsFanart and not artpic in picture:
		listitem.setArt({'fanart': picture})
	if metadata.get('Reference') == 'Single':
		listitem.setProperty('IsPlayable', 'true')
	if not KODI_ov20: listitem.setInfo('Video', vinfo)
	return listitem

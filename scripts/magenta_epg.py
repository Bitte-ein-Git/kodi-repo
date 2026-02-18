import requests
import uuid
import datetime
import os
import re
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- CONFIGURATION ---
DAYS_TO_GRAB = 3
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_XML = os.path.join(REPO_ROOT, "iptv", "magenta.xml")

# API CONSTANTS
BOOTSTRAP_TEMPLATE = "https://prod.dcm.telekom-dienste.de/v1/settings/{configGroupId}/bootstrap?"
CONFIG_GROUP_ID = "atv-androidtv"
APP_MODEL = "DT:ATV-AndroidTV"
APP_NAME = "MagentaTV"
APP_VERSION = "104180"
FIRMWARE = "API level 30"
RUNTIME = "1"
USER_AGENT = "Dalvik/2.1.0 (Linux; U; Android 11; SHIELD Android TV Build/RQ1A.210105.003) ((2.00T_ATV::3.134.4462::mdarcy::FTV_OTT_DT))"

class MagentaEPG:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': USER_AGENT,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.device_id = str(uuid.uuid4())
        self.session_id = str(uuid.uuid4())
        self.config = {}
        self.channels = []
        self.epg_data = {}
        self.account_pid = None

    def _get_headers(self, url):
        headers = {}
        if "prod.dcm.telekom-dienste.de" in url:
            headers['x-dt-session-id'] = self.session_id
            headers['x-dt-call-id'] = str(uuid.uuid4())
        return headers

    def _get_json(self, url, params=None):
        try:
            req_headers = self._get_headers(url)
            response = self.session.get(url, params=params, headers=req_headers)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def bootstrap(self):
        url = BOOTSTRAP_TEMPLATE.replace("{configGroupId}", CONFIG_GROUP_ID)
        url += f"deviceid={self.device_id}"
        print(f"Bootstrapping: {url}")
        
        data = self._get_json(url)
        if not data or 'baseSettings' not in data:
            raise Exception("Bootstrap failed: 'baseSettings' missing")

        base_settings = data['baseSettings']
        self.config['deviceTokensUrl'] = base_settings.get('deviceTokensUrl')
        if 'dcm' in data:
            self.config['manifestBaseUrl'] = data['dcm'].get('manifestBaseUrl')
            
        print("Bootstrap successful.")
        self.device_manifest()

    def device_manifest(self):
        if not self.config.get('deviceTokensUrl'):
            raise Exception("No deviceTokensUrl found")

        url = self.config['deviceTokensUrl']
        params = {
            'model': APP_MODEL,
            'deviceId': self.device_id,
            'appname': APP_NAME,
            'appVersion': APP_VERSION,
            'firmware': FIRMWARE,
            'runtimeVersion': RUNTIME,
            'duid': self.device_id
        }
        
        print(f"Fetching Device Manifest...")
        data = self._get_json(url, params)
        if not data:
            raise Exception("Device Manifest request failed")

        if 'settings' in data and 'parameters' in data['settings']:
            for param in data['settings']['parameters']:
                self.config[param.get('key')] = param.get('value')

        self.account_pid = self.config.get('mpxAccountPid')
        if not self.account_pid:
            if self.config.get('manifestBaseUrl'):
                self.manifest()
            else:
                raise Exception("Account PID not found")
        else:
             print(f"Account PID: {self.account_pid}")

    def manifest(self):
        base_url = self.config.get('manifestBaseUrl')
        if not base_url: return

        url = base_url.replace("{configGroupId}", CONFIG_GROUP_ID)
        url += f"?deviceid={self.device_id}"
        
        data = self._get_json(url)
        if data and 'mpx' in data:
            self.account_pid = data['mpx'].get('accountPid')
            if 'feeds' in data['mpx']:
                for k, v in data['mpx']['feeds'].items():
                    if k not in self.config:
                        self.config[k] = v

    def clean_channel_name(self, name):
        """Bereinigt den Kanalnamen für die ID (entfernt HD, SD, Suffixe)."""
        # Entferne "- Main", "(Sky)", " HD", " SD", " FHD" etc.
        # Reihenfolge ist wichtig (längere Strings zuerst)
        name = name.replace(" - Main", "")
        name = name.replace(" (Sky)", "")
        name = re.sub(r'\s(HD|SD|FHD|UHD)\b', '', name) # Entfernt HD/SD am Wortende
        return name.strip()

    def get_channels(self):
        feed_url = self.config.get('mpxDefaultUrlAllChannelStationsFeed') or \
                   self.config.get('mpxBasicUrlAllChannelStationsFeed') or \
                   self.config.get('allChannelStationsFeed')

        if not feed_url:
            print("No channel feed URL found.")
            return

        feed_url = feed_url.replace('{MpxAccountPid}', self.account_pid)
        feed_url += "?lang=short-de&range=1-500"

        print(f"Fetching Channels from {feed_url}")
        data = self._get_json(feed_url)
        
        if data and 'entries' in data:
            for entry in data['entries']:
                # Wir bereinigen den Titel sofort für die ID
                raw_title = entry.get('title', 'Unknown')
                clean_id = self.clean_channel_name(raw_title)

                chan_obj = {
                    'id': clean_id,  # Das ist jetzt der "channel" wert im XML (z.B. "Das Erste")
                    'channel_number': entry.get('channelNumber'),
                    'title': raw_title, # Der volle Name für display-name
                    'stations': []
                }
                
                stations_map = entry.get('stations', {})
                stations_iterable = stations_map if isinstance(stations_map, list) else stations_map.values()

                for station in stations_iterable:
                    station_data = {
                        'station_id': station.get('id'),
                        'is_hd': station.get('isHd', False)
                    }
                    if 'thumbnails' in station:
                        thumbs = station['thumbnails']
                        logo = thumbs.get('stationLogoColored.png', thumbs.get('stationLogo.png', {}))
                        if isinstance(logo, dict):
                            station_data['icon'] = logo.get('url', '')
                        else:
                            station_data['icon'] = ''
                    chan_obj['stations'].append(station_data)
                
                self.channels.append(chan_obj)
        print(f"Found {len(self.channels)} channels.")

    def fetch_epg(self, days=DAYS_TO_GRAB):
        schedule_base = self.config.get('mpxBasicUrlAllChannelSchedulesFeed') or self.config.get('allChannelSchedulesFeed')
        program_base = self.config.get('mpxAllProgramsFeedUrl') or self.config.get('allProgramsFeedUrl')
        location_id = self.config.get('mpxLocationIdUri') or self.config.get('locationIdUri')
        
        if not schedule_base or not program_base or not location_id:
            print("Missing EPG feed URLs or Location ID.")
            return

        schedule_base = schedule_base.replace('{{MpxAccountPid}}', self.account_pid).replace('{MpxAccountPid}', self.account_pid)
        program_base = program_base.replace('{{MpxAccountPid}}', self.account_pid).replace('{MpxAccountPid}', self.account_pid)

        now = datetime.datetime.now(datetime.timezone.utc)
        end = now + datetime.timedelta(days=days)
        time_range = f"{now.strftime('%Y-%m-%dT%H:%M:%SZ')}~{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        print(f"Fetching EPG for range: {time_range}")

        for channel in self.channels: 
            chan_num = channel.get('channel_number')
            if not chan_num: continue

            # Schedule abrufen
            url = (f"{schedule_base}?form=cjson&byLocationId={location_id}"
                   f"&byListingTime={time_range}&byChannelNumber={chan_num}"
                   f"&range=1-500&fields=listings.program.guid,listings.startTime,listings.endTime")
            
            data = self._get_json(url)
            guids = []
            schedule_map = {}

            if data and 'entries' in data:
                for entry in data['entries']:
                    for listing in entry.get('listings', []):
                        if 'program' in listing:
                            guid = listing['program'].get('guid')
                            if guid:
                                guids.append(guid)
                                if guid not in schedule_map: schedule_map[guid] = []
                                schedule_map[guid].append({
                                    'start': listing.get('startTime'),
                                    'end': listing.get('endTime')
                                })

            if not guids: continue

            # Programmdetails abrufen
            unique_guids = list(set(guids))
            chunk_size = 50
            for i in range(0, len(unique_guids), chunk_size):
                chunk = unique_guids[i:i + chunk_size]
                guid_str = "|".join(chunk)
                
                # secondaryTitle = Episodentitel
                # year = Produktionsjahr
                p_url = (f"{program_base}?form=cjson&byGuid={guid_str}"
                         f"&fields=guid,title,secondaryTitle,description,shortDescription,thumbnails,year,ratings,tvSeasonNumber,tvSeasonEpisodeNumber")
                
                p_data = self._get_json(p_url)
                
                if p_data and 'entries' in p_data:
                    for prog in p_data['entries']:
                        guid = prog.get('guid')
                        if guid in schedule_map:
                            for timing in schedule_map[guid]:
                                program_entry = {
                                    'start': timing['start'],
                                    'end': timing['end'],
                                    'title': prog.get('title'),
                                    'sub_title': prog.get('secondaryTitle'), # Episodentitel
                                    'desc': prog.get('description') or prog.get('shortDescription'),
                                    'year': prog.get('year'),
                                    'icon': self._extract_image(prog),
                                    'season': prog.get('tvSeasonNumber'),
                                    'episode': prog.get('tvSeasonEpisodeNumber')
                                }
                                
                                if channel['id'] not in self.epg_data:
                                    self.epg_data[channel['id']] = []
                                self.epg_data[channel['id']].append(program_entry)
            
            print(f"Processed EPG for: {channel['id']}")

    def _extract_image(self, prog):
        if 'thumbnails' in prog:
            for k, v in prog['thumbnails'].items():
                if v and 'url' in v: return v['url']
        return None

    def create_xmltv(self, filename):
        print(f"Generating XMLTV file: {filename}")
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        root = ET.Element("tv", {"generator-info-name": "PythonMagentaScraper v2"})

        # Channels schreiben
        for channel in self.channels:
            # Wir nehmen die bereinigte ID
            c_elem = ET.SubElement(root, "channel", {"id": channel['id']})
            
            display = ET.SubElement(c_elem, "display-name")
            display.text = channel['title'] # Voller Name für Anzeige
            
            # Icon vom ersten Stations-Eintrag nehmen
            if channel['stations'] and channel['stations'][0].get('icon'):
                ET.SubElement(c_elem, "icon", {"src": channel['stations'][0]['icon']})

        # Programme schreiben
        for cid, programs in self.epg_data.items():
            for p in programs:
                start_dt = datetime.datetime.fromtimestamp(p['start'] / 1000, datetime.timezone.utc)
                end_dt = datetime.datetime.fromtimestamp(p['end'] / 1000, datetime.timezone.utc)
                
                prog_elem = ET.SubElement(root, "programme", {
                    "start": start_dt.strftime('%Y%m%d%H%M%S +0000'), 
                    "stop": end_dt.strftime('%Y%m%d%H%M%S +0000'), 
                    "channel": cid
                })

                ET.SubElement(prog_elem, "title").text = p['title']
                
                if p.get('sub_title'):
                    ET.SubElement(prog_elem, "sub-title").text = p['sub_title']

                if p.get('desc'):
                    ET.SubElement(prog_elem, "desc").text = p['desc']
                
                if p.get('year'):
                    ET.SubElement(prog_elem, "date").text = str(p['year'])

                if p.get('icon'):
                    ET.SubElement(prog_elem, "icon", {"src": p['icon']})

                # Staffel/Episode
                season = p.get('season')
                episode = p.get('episode')
                if season or episode:
                    s_idx = int(season) - 1 if season and int(season) > 0 else 0
                    e_idx = int(episode) - 1 if episode and int(episode) > 0 else 0
                    if season is not None or episode is not None:
                        ET.SubElement(prog_elem, "episode-num", {"system": "xmltv_ns"}).text = f"{s_idx}.{e_idx}."

        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(xmlstr)
        print("Done.")

if __name__ == "__main__":
    scraper = MagentaEPG()
    try:
        scraper.bootstrap()
        scraper.get_channels()
        scraper.fetch_epg()
        scraper.create_xmltv(OUTPUT_XML)
    except Exception as e:
        print(f"Critical Error: {e}")
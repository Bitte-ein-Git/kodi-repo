import requests, uuid, json, os, sys
from datetime import datetime, timedelta
from lxml import etree

# configuration
DAYS_TO_GRAB = 3
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_XML = os.path.join(REPO_ROOT, "iptv", "magenta.xml")
os.makedirs(os.path.dirname(OUTPUT_XML), exist_ok=True)

# api endpoints
AUTH_URL = 'https://api.prod.sngtv.magentatv.de/EPG/JSON/Authenticate'
CHLIST_URL = 'https://api.prod.sngtv.magentatv.de/EPG/JSON/AllChannel'
EPG_URL = 'https://api.prod.sngtv.magentatv.de/EPG/JSON/PlayBillList?userContentFilter=241221015&sessionArea=1&SID=ottall&T=PC_firefox_75'

# request headers
HEADERS = {
    'Host': 'api.prod.sngtv.magentatv.de',
    'origin': 'https://web.magentatv.de',
    'referer': 'https://web.magentatv.de/',
    'User-Agent': 'Mozilla/5.0',
    'Accept': '*/*',
    'Accept-Language': 'de,en-US;q=0.7,en;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
}

# log status message
def log(msg):
    print(f"[{datetime.now().isoformat()}] {msg}", file=sys.stderr)

# handle authentication
def authenticate():
    log("Authentifiziere bei MagentaTV...")
    mac = str(uuid.uuid4())
    ter = str(uuid.uuid4())
    payload = {
        "areaid": "1", "cnonce": "c4b11948545fb3089720dd8b12c81f8e",
        "mac": mac, "preSharedKeyID": "NGTV000001", "subnetId": "4901",
        "templatename": "NGTV", "terminalid": ter, "terminaltype": "WEB-MTV",
        "terminalvendor": "WebTV", "timezone": "UTC", "usergroup": "-1",
        "userType": 3, "utcEnable": 1
    }
    session = requests.Session()
    for attempt in range(120):
        r = session.post(AUTH_URL, json=payload, headers=HEADERS, timeout=5)
        if r.json().get("retcode") != "-2":
            break
    session.headers.update({'X_CSRFToken': session.cookies.get("CSRFSESSION")})
    log("Authentifizierung abgeschlossen.")
    return session

# fetch channel list
def get_channels(session):
    log("Lade Kanalliste...")
    payload = {
        "properties": [{"name": "logicalChannel", "include": "/channellist/logicalChannel/contentId,/channellist/logicalChannel/name"}],
        "metaDataVer": "Channel/1.1", "channelNamespace": "2",
        "filterlist": [{"key": "IsHide", "value": "-1"}], "returnSatChannel": "0"
    }
    r = session.post(CHLIST_URL, json=payload, headers=HEADERS)
    channels = r.json().get("channellist", [])
    log(f"{len(channels)} Kanäle gefunden.")
    return channels

# fetch program data
def get_epg(session, content_id, start, end):
    payload = {
        "channelid": content_id, "type": "2", "offset": "0", "count": "-1", "isFillProgram": "1",
        "properties": '[{"name":"playbill","include":"name,subname,starttime,endtime,introduce,productionyear,seasonnum,episodenum"}]',
        "begintime": start, "endtime": end
    }
    r = session.post(EPG_URL, json=payload, headers=HEADERS)
    return r.json().get("playbilllist", [])

# generate xmltv file
def write_xmltv(channels, epg_data):
    log("Schreibe XMLTV-Datei...")
    tv = etree.Element("tv")
    for ch in channels:
        ch_elem = etree.SubElement(tv, "channel", id=ch["name"])
        etree.SubElement(ch_elem, "display-name").text = ch["name"]

    for ch in channels:
        for prog in epg_data.get(ch["contentId"], []):
            start = prog.get("starttime", "").replace(" ", "").replace("-", "").replace(":", "")
            end = prog.get("endtime", "").replace(" ", "").replace("-", "").replace(":", "")
            prog_elem = etree.SubElement(tv, "programme", start=start, stop=end, channel=ch["name"])
            
            # basic metadata
            etree.SubElement(prog_elem, "title", lang="de").text = prog.get("name", "")
            
            if prog.get("subname"):
                etree.SubElement(prog_elem, "sub-title", lang="de").text = prog.get("subname", "")
            
            # format description with SxxExx prefix
            desc_text = prog.get("introduce", "")
            s = prog.get("seasonnum")
            e = prog.get("episodenum")
            
            if s and e:
                desc_text = f"S{s}E{e} | {desc_text}"
            elif e:
                desc_text = f"Episode: {e} | {desc_text}"
            
            etree.SubElement(prog_elem, "desc", lang="de").text = desc_text
            
            # extra metadata
            if prog.get("productionyear"):
                etree.SubElement(prog_elem, "date").text = str(prog.get("productionyear"))
                
            if s or e:
                sn = s if s else "?"
                en = e if e else "?"
                ep_text = f"S{sn} E{en}"
                etree.SubElement(prog_elem, "episode-num", system="onscreen").text = ep_text

    tree = etree.ElementTree(tv)
    tree.write(OUTPUT_XML, encoding="utf-8", xml_declaration=True, pretty_print=True)
    log(f"✅ EPG gespeichert unter: {OUTPUT_XML}")

# main execution
def main():
    log("📺 Starte Magenta EPG Updater...")
    session = authenticate()
    channels = get_channels(session)
    start = datetime.now().replace(hour=0, minute=0, second=1)
    end = start + timedelta(days=DAYS_TO_GRAB)
    start_str = start.strftime("%Y%m%d%H%M%S")
    end_str = end.strftime("%Y%m%d%H%M%S")

    epg_data = {}
    for ch in channels:
        cid = ch["contentId"]
        log(f"Lade EPG für Kanal: {ch['name']} ({cid})")
        epg_data[cid] = get_epg(session, cid, start_str, end_str)

    write_xmltv(channels, epg_data)
    log("🏁 Magenta EPG Update abgeschlossen.")

if __name__ == "__main__":
    main()
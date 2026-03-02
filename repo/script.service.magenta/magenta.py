import bottle
from bottle import request, response, route, static_file, redirect
from wsgiref.simple_server import make_server
from bs4 import BeautifulSoup
from uuid import uuid4
import base64, json, requests, time, urllib, xbmc, xbmcaddon, xbmcgui, xbmcvfs, xmltodict, os, threading

release_pids = {}

login_url = "https://accounts.login.idm.telekom.com"
sso_url = "https://ssom.magentatv.de"
feed_url = "https://feed.entertainment.tv.theplatform.eu"
link_url = "https://link.theplatform.eu"
concurrency_url = "https://concurrency.delivery.theplatform.eu/concurrency/web/Concurrency/unlock"
wv_url = "https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense"
epg_source_url = "https://bitte-ein-git.github.io/kodi-repo/iptv/magenta.xml"

__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))

if not os.path.exists(__profile__):
    os.makedirs(__profile__)

CACHE_FILE_CHANNELS = os.path.join(__profile__, 'channels_cache.json')
CACHE_FILE_EPG = os.path.join(__profile__, 'guide.xml')
CACHE_TIME_CHANNELS = 86400
CACHE_TIME_EPG = 43200

httpd = None

def parse_input_values(content):
    f = dict()
    parser = BeautifulSoup(content, 'html.parser')
    ref = parser.findAll('input')
    for i in ref:
        if "xsrf" in i.get("name", "") or i.get("name", "") == "tid":
            f.update({i["name"]: i["value"]})
    return f

def init_config(t):
    global w
    w = t

class WebServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        init_config(self)
        self.p_token = login()

    def run(self):
        global httpd
        
        # fetch channels on startup to trigger ready notification
        if self.p_token:
            if self.get_ch_list():
                xbmcgui.Dialog().notification(__addonname__, "Senderliste bereit", xbmcgui.NOTIFICATION_INFO)

        app = bottle.default_app()
        httpd = make_server('0.0.0.0', 4700, app)
        httpd.serve_forever()

    def stop(self):
        global httpd
        if httpd:
            threading.Thread(target=httpd.shutdown).start()

    def get_ch_list(self):
        ch_list = channel_list(self.p_token)
        if not ch_list:
            self.p_token = login(force=True)
            if not self.p_token:
                return
            else:
                ch_list = channel_list(self.p_token, force_refresh=True)
        return ch_list

    def get_channel(self, channel):
        mpd = channel_mpd(self.p_token, channel)
        if not mpd:
            self.p_token = login(force=True)
            if not self.p_token:
                return
            else:
                mpd = channel_mpd(self.p_token, channel)
        return mpd

    def get_license(self, channel):
        return channel_license(self.p_token, channel)

@route("/api/file/channels.m3u", method="GET")
def m3u():
    response.set_header("Content-Type", "application/m3u8")
    return w.get_ch_list()

@route("/api/file/guide.xml", method="GET")
def epg():
    update_epg_cache()
    return static_file('guide.xml', root=__profile__, mimetype='application/xml')

@route("/api/fw/<channel>/manifest.mpd", method="GET")
def play_channel(channel):
    video_src = w.get_channel(channel)
    if video_src:
        redirect(video_src)
    return "Error"

@route("/api/fw/<channel>/license", method="POST")
def proxy_license(channel):
    url = w.get_license(channel)
    response.set_header("Content-Type", "application/octet-stream")
    drm = requests.post(url, data=request.body.read())
    return drm.content

def login(force=False):
    if not force:
        p_token = __addon__.getSetting("p_token")
        if p_token:
            return p_token

    __device_id = __addon__.getSetting("device_id")
    if not __device_id:
        __device_id = str(uuid4())
        __addon__.setSetting("device_id", __device_id)

    __login = __addon__.getSetting("username")
    __password = __addon__.getSetting("password")
    __customer_id = __addon__.getSetting("customer_id")

    if not __login or not __password:
        xbmcgui.Dialog().notification(__addonname__, "Konfiguration unvollständig/ungültig", xbmcgui.NOTIFICATION_ERROR)
        return None

    r = requests.Session()
    r.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })
    
    s = requests.Session()
    s.headers.update({
        "Device-Id": __device_id, "Session-Id": str(uuid4()), "Content-Type": "application/json", "Application-Id": "ngtv",
        "Referer": "https://web2.magentatv.de/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    sso_login_url = f"{sso_url}/login"
    sso_req = s.get(sso_login_url)
    
    try:
        login_red_url = sso_req.json()["loginRedirectUrl"].replace("redirect_uri=authn", f"redirect_uri={urllib.parse.quote('https://web2.magentatv.de/authn')}")
        req = r.get(login_red_url)
    except Exception as e:
        xbmc.log("MTV2: " + str(sso_req.content))
        xbmcgui.Dialog().notification(__addonname__, "Falsche Login Daten", xbmcgui.NOTIFICATION_ERROR)
        return None

    data = {"x-show-cancel": "false", "bdata": "", "pw_usr": __login, "pw_submit": "", "hidden_pwd": ""}
    data.update(parse_input_values(req.content))

    url_post = f"{login_url}/factorx"
    req = r.post(url_post, data=data)

    resp = BeautifulSoup(req.content, "html.parser")
    if resp.find("input", {"id": "customerNr"}):
        if not __customer_id:
            xbmcgui.Dialog().notification(__addonname__, "Konfiguration unvollständig/ungültig", xbmcgui.NOTIFICATION_ERROR)
            return None

        data = {"bdata": "", "customerNr": __customer_id, "next": ""}
        data.update(parse_input_values(req.content))
        req = r.post(url_post, data=data)
        data = {"bdata": "", "passid02": __password}
    else:
        data = {"hidden_usr": __login, "bdata": "", "pw_pwd": __password, "pw_submit": ""}
        
    data.update(parse_input_values(req.content))
    req = r.post(url_post, data=data)

    if "Passkey: Die neue Anmeldeoption" in str(req.content):
        data = {"pkc": "", "webauthnError": "", "dont_ask_again": ""}
        data.update(parse_input_values(req.content))
        req = r.post(url_post, data=data)

    try:    
        codes = {i.split("=")[0]: i.split("=")[1] for i in req.url.split("?")[1].split("&")}
    except:
        xbmcgui.Dialog().notification(__addonname__, "Falsche Login Daten", xbmcgui.NOTIFICATION_ERROR)
        return None
    
    r.get(req.url)

    try:
        sso_auth_url = f"{sso_url}/authenticate"
        sso_req = s.post(sso_auth_url, data=json.dumps({"checkRefreshToken": True, "returnCode": {"code": codes["code"], "state": codes["state"]}}))
        info = sso_req.json()
    except:
        xbmcgui.Dialog().notification(__addonname__, "Falsche Login Daten", xbmcgui.NOTIFICATION_ERROR)
        return None

    try:
        p_token = info["userInfo"]["personaToken"]  
        __addon__.setSetting("p_token", p_token)
        return p_token
    except:
        xbmcgui.Dialog().notification(__addonname__, "Falsche Login Daten", xbmcgui.NOTIFICATION_ERROR)
        return None

def update_epg_cache():
    needs_update = True
    if os.path.exists(CACHE_FILE_EPG):
        if (time.time() - os.path.getmtime(CACHE_FILE_EPG)) < CACHE_TIME_EPG:
            needs_update = False
    
    if needs_update:
        try:
            xbmc.log(f"MTV2: Updating EPG Cache from {epg_source_url}", xbmc.LOGINFO)
            r = requests.get(epg_source_url, stream=True)
            if r.status_code == 200:
                with open(CACHE_FILE_EPG, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                xbmc.log("MTV2: EPG Cache updated successfully.", xbmc.LOGINFO)
            else:
                xbmc.log(f"MTV2: Failed to update EPG. Status: {r.status_code}", xbmc.LOGERROR)
        except Exception as e:
            xbmc.log(f"MTV2: EPG Update Error: {str(e)}", xbmc.LOGERROR)

def get_cached_channels():
    if os.path.exists(CACHE_FILE_CHANNELS):
        if (time.time() - os.path.getmtime(CACHE_FILE_CHANNELS)) < CACHE_TIME_CHANNELS:
            try:
                with open(CACHE_FILE_CHANNELS, 'r') as f:
                    return json.load(f)
            except:
                pass
    return None

def save_channels_cache(data):
    try:
        with open(CACHE_FILE_CHANNELS, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        xbmc.log(f"MTV2: Cache Save Error: {str(e)}", xbmc.LOGERROR)

def channel_list(token, force_refresh=False):
    ch_list = None
    if not force_refresh:
        ch_list = get_cached_channels()

    if not ch_list:
        if not token:
            return None
            
        r = requests.Session()
        r.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        try:
            url = f"{feed_url}/f/mdeprod/mdeprod-channel-stations-main?lang=short-de&sort=dt%24displayChannelNumber&range=1-500"
            req = r.get(url)
            if req.status_code != 200:
                return False
            ch_list = req.json()
            save_channels_cache(ch_list)
        except:
            return
            
    custom_order = {}
    favorites = []
    hidden = []
    
    hide_sd = __addon__.getSettingBool("hide_sd")
    use_alt_logos = __addon__.getSettingBool("alt_logos")
    use_custom_order = __addon__.getSettingBool("custom_order")
    only_favorites = __addon__.getSettingBool("only_favorites")
    deactivate_hidden = __addon__.getSettingBool("deactivate_hidden")

    if use_custom_order or only_favorites or deactivate_hidden:
        try:
            r_prof = requests.get("https://pro.entertainment.tv.theplatform.eu/data/UserList?form=cjson&schema=1.3", headers={"Authorization": f"Basic {token}"}, timeout=5)
            if r_prof.status_code == 200:
                for entry in r_prof.json().get("entries", []):
                    title = entry.get("title", "")
                    for item in entry.get("items", []):
                        if title == "LiveTvPersonalChannelList":
                            custom_order[item.get("aboutId")] = item.get("index", 9999)
                        elif title == "LiveTvFavoriteChannelList":
                            favorites.append(item.get("aboutId"))
                        elif title == "LiveTvHiddenChannelList":
                            hidden.append(item.get("aboutId"))
        except Exception as e:
            xbmc.log(f"MTV2: fetch user list failed {str(e)}", xbmc.LOGERROR)

    processed_channels = []

    try:
        for idx, chan in enumerate(ch_list["entries"]):
            chan_url = [*chan["stations"]][0]
            station = chan["stations"][chan_url]
            station_id = station.get("id")
            
            if deactivate_hidden and station_id in hidden:
                continue
                
            if only_favorites and station_id not in favorites:
                continue
                
            if station.get("era$mediaPids", {}).get("urn:theplatform:tv:location:any"):
                is_hd = station.get("dt$quality") == "HD"
                base_title = station.get("title", "")

                if hide_sd:
                    if not is_hd:
                        continue 
                    chan_title = base_title 
                else:
                    chan_title = f'{base_title} HD' if is_hd else base_title

                logo_url = ""
                if use_alt_logos:
                    thumb_url = ""
                    thumbnails = station.get("thumbnails", {})
                    for k, v in thumbnails.items():
                        if v.get("title") == "stationLogoColored.png":
                            thumb_url = v.get("url", "")
                            break
                    if not thumb_url:
                        for k, v in thumbnails.items():
                            if v.get("title") == "stationLogo.png":
                                thumb_url = v.get("url", "")
                                break
                    if thumb_url:
                        logo_url = "https://ngiss.t-online.de/iss?client=ftp22&out=webp&x=512&y=512&ar=keep&src=" + urllib.parse.quote(thumb_url)
                
                if not logo_url:
                    logo_url = "https://ngiss.t-online.de/iss?client=ftp22&out=webp&x=512&y=512&ar=keep&src="+urllib.parse.quote(station["thumbnails"]["stationBackground"]["url"])

                orig_num = chan.get("channelNumber", 9999)
                
                if use_custom_order and station_id in custom_order:
                    sort_num = custom_order[station_id]
                elif use_custom_order:
                    sort_num = 10000 + idx
                else:
                    sort_num = idx
                    
                processed_channels.append({
                    "sort_num": sort_num,
                    "orig_num": orig_num,
                    "title": chan_title,
                    "logo": logo_url,
                    "pid": station["era$mediaPids"]["urn:theplatform:tv:location:any"]
                })
                
        processed_channels.sort(key=lambda x: x["sort_num"])

        output = '#EXTM3U x-tvg-url="http://localhost:4700/api/file/guide.xml"\n'
        for p in processed_channels:
            output += (
                f'#KODIPROP:inputstreamclass=inputstream.adaptive\n'
                f'#KODIPROP:inputstream.adaptive.manifest_type=mpd\n'
                f'#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha\n'
                f'#KODIPROP:inputstream.adaptive.license_key=http://localhost:4700/api/fw/{p["pid"]}/license||R{{SSM}}|\n'
                f'#EXTINF:0001 tvg-id="tkm_{p["orig_num"]}" tvg-logo="{p["logo"]}", {p["title"]}\n'
                f'http://localhost:4700/api/fw/{p["pid"]}/manifest.mpd\n'
            )
        return output
    except Exception as e:
        xbmc.log(str(e))
        return

def channel_mpd(token, channel):
    __device_id = __addon__.getSetting("device_id")
    
    r = requests.Session()
    r.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Authorization": f"Basic {token}"
    })

    try:
        manifest_url = f"{link_url}/s/mdeprod/media/{channel}?format=SMIL&formats=MPEG-DASH&tracking=true"
        req = r.get(manifest_url)
        if req.status_code != 200:
            return False

        ch_data = xmltodict.parse(req.content)
        unlock_url = f"https://concurrency.delivery.theplatform.eu/concurrency/web/Concurrency/unlock?_clientId={__device_id}&_encryptedLock={urllib.parse.quote(ch_data['smil']['head']['meta'][5]['@content'])}&_id={urllib.parse.quote(ch_data['smil']['head']['meta'][3]['@content'])}&_sequenceToken={urllib.parse.quote(ch_data['smil']['head']['meta'][4]['@content'])}&form=json&schema=1.0"
        
        threading.Thread(target=requests.get, args=(unlock_url,)).start()

        video_src = ch_data['smil']['body']['seq']['switch']['switch']['video'][0]['@src']
        video_args = {i.split("=")[0]: i.split("=")[1] for i in ch_data['smil']['body']['seq']['switch']['ref']['param']['@value'].split("|")}

        release_pids[channel] = video_args["pid"]

        return video_src
    except Exception as e:
        xbmc.log(str(e))
        return False

def channel_license(token, channel):
    x = 10
    while True:
        if release_pids.get(channel):
            try:
                decoded_session = base64.b64decode(token).decode().split(":")
                url = f"{wv_url}?account={urllib.parse.quote('http:'+decoded_session[1])}&releasePid={urllib.parse.quote(release_pids[channel])}&token={urllib.parse.quote(decoded_session[2])}&schema=1.0"
                return url
            except:
                break
        else:
            x = x - 1
        if x == 0:
            break
        time.sleep(0.3)
    return


class MagentaMonitor(xbmc.Monitor):
    def __init__(self):
        xbmc.Monitor.__init__(self)
        self.restart_flag = False

    def onSettingsChanged(self):
        xbmcgui.Dialog().notification(__addonname__, "Einstellungen geändert, Server Neustart...", xbmcgui.NOTIFICATION_INFO)
        __addon__.setSetting("p_token", "") # clear token to enforce new settings load
        self.restart_flag = True
        global httpd
        if httpd:
            threading.Thread(target=httpd.shutdown).start()


def start():
    monitor = MagentaMonitor()
    
    while not monitor.abortRequested():
        t = WebServer()
        t.start()
        
        while not monitor.abortRequested() and not monitor.restart_flag:
            monitor.waitForAbort(1)
            
        t.stop()
        t.join(timeout=3)
        
        if monitor.restart_flag:
            monitor.restart_flag = False
            continue
        else:
            break

if __name__ == "__main__":
    start()
from bottle import request, response, route, run, static_file
from bs4 import BeautifulSoup
from uuid import uuid4
import base64, json, requests, time, urllib, xbmc, xbmcaddon, xbmcgui, xbmcvfs, xmltodict, os

### Magenta TV DE OTT 2.0 PARAMS

release_pids = {}

login_url = "https://accounts.login.idm.telekom.com"
sso_url = "https://ssom.magentatv.de"
feed_url = "https://feed.entertainment.tv.theplatform.eu"
link_url = "https://link.theplatform.eu"
concurrency_url = "https://concurrency.delivery.theplatform.eu/concurrency/web/Concurrency/unlock"
wv_url = "https://widevine.entitlement.theplatform.eu/wv/web/ModularDrm/getRawWidevineLicense"
epg_source_url = "https://kodi.heyfordy.de/iptv/magenta.xml"


# KODI PARAMS
__addon__ = xbmcaddon.Addon()
__addonname__ = __addon__.getAddonInfo('name')

# FIX: Use xbmcvfs instead of xbmc for translatePath in Kodi 19+
__profile__ = xbmcvfs.translatePath(__addon__.getAddonInfo('profile'))

# Ensure profile directory exists
if not os.path.exists(__profile__):
    os.makedirs(__profile__)

# CACHE CONFIG
CACHE_FILE_CHANNELS = os.path.join(__profile__, 'channels_cache.json')
CACHE_FILE_EPG = os.path.join(__profile__, 'guide.xml')
CACHE_TIME_CHANNELS = 86400  # 24 Hours
CACHE_TIME_EPG = 43200       # 12 Hours


# Helper to parse hidden form values
def parse_input_values(content):
    f = dict()

    parser = BeautifulSoup(content, 'html.parser')
    ref = parser.findAll('input')

    for i in ref:
        if "xsrf" in i.get("name", "") or i.get("name", "") == "tid":
            f.update({i["name"]: i["value"]})

    return f

#
# WEB SERVER
#

def init_config(t):
    global w
    w = t


# Main web server class
class WebServer():

    def __init__(self):
        init_config(self)

        self.p_token = login()
        
        run(host='0.0.0.0', port=4700, debug=False, quiet=True)

    def get_ch_list(self):
        # Logic moved to channel_list function to handle caching internally
        ch_list = channel_list(self.p_token)

        if not ch_list:
            # If cache miss and token invalid, relogin
            self.p_token = login()

            if not self.p_token:
                return
            else:
                # Retry with new token
                ch_list = channel_list(self.p_token, force_refresh=True)
        
        return ch_list

    def get_channel(self, channel):
        mpd = channel_mpd(self.p_token, channel)
        
        if not mpd:
            self.p_token = login()

            if not self.p_token:
                return
            else:
                mpd = channel_mpd(self.p_token, channel)
        
        return mpd

    def get_license(self, channel):
        return channel_license(self.p_token, channel)
    
    def stop_kodi(self):
        requests.get("http://localhost:4700")


# API route for M3U playlist
@route("/api/file/channels.m3u", method="GET")
def m3u():
    response.set_header("Content-Type", "application/m3u8")
    return w.get_ch_list()

# API route for EPG XML
@route("/api/file/guide.xml", method="GET")
def epg():
    # Update EPG cache if needed
    update_epg_cache()
    # Serve static file from userdata folder
    return static_file('guide.xml', root=__profile__, mimetype='application/xml')

# API route for MPD manifest
@route("/api/fw/<channel>/manifest.mpd", method="GET")
def play_channel(channel):
    response.set_header("Content-Type", "application/dash+xml")
    return w.get_channel(channel)

# API route for license proxy
@route("/api/fw/<channel>/license", method="POST")
def proxy_license(channel):
    url = w.get_license(channel)
    response.set_header("Content-Type", "application/octet-stream")
    drm = requests.post(url, data=request.body.read())
    lic = drm.content
    return lic


#
# LOGIN
#

# Handles the multi-step login process
def login():

    __device_id = __addon__.getSetting("device_id")

    if not __device_id:
        __device_id = str(uuid4())
        __addon__.setSetting("device_id", __device_id)

    __login = __addon__.getSetting("username")
    __password = __addon__.getSetting("password")
    __customer_id = __addon__.getSetting("customer_id")

    if not __login or not __password:
        xbmcgui.Dialog().notification(__addonname__, "Bitte Anmeldedaten in den Addon-Einstellungen eintragen.", xbmcgui.NOTIFICATION_ERROR)
        return

    # RETRIEVE SESSION DATA
    r = requests.Session()  # LOGIN PAGE
    r.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    })
    
    s = requests.Session()  # SSOM
    s.headers.update({
        "Device-Id": __device_id, "Session-Id": str(uuid4()), "Content-Type": "application/json", "Application-Id": "ngtv",
        "Referer": "https://web2.magentatv.de/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })

    
    # STEP 1.1: GET LOGIN URL VIA SSO
    sso_login_url = f"{sso_url}/login"
    sso_req = s.get(sso_login_url)
    
    # STEP 1.2: GET INITIAL LOGIN PAGE
    try:
        login_red_url = sso_req.json()["loginRedirectUrl"].replace("redirect_uri=authn", f"redirect_uri={urllib.parse.quote('https://web2.magentatv.de/authn')}")
        req = r.get(login_red_url)
    except Exception as e:
        xbmc.log("MTV2: " + str(sso_req.content))
        xbmcgui.Dialog().notification(__addonname__, "Login-Fehler: Login-Redirect-URL konnte nicht abgerufen werden.", xbmcgui.NOTIFICATION_ERROR)
        return

    # STEP 2: SEND USERNAME/MAIL
    data = {"x-show-cancel": "false", "bdata": "", "pw_usr": __login, "pw_submit": "", "hidden_pwd": ""}
    data.update(parse_input_values(req.content))

    url_post = f"{login_url}/factorx"
    req = r.post(url_post, data=data)

    # STEP 3.1: SEND CUSTOMER ID
    resp = BeautifulSoup(req.content, "html.parser")
    if resp.find("input", {"id": "customerNr"}):
        if not __customer_id:
            xbmcgui.Dialog().notification(__addonname__, "Bitte Kundennummer in den Addon-Einstellungen eintragen.", xbmcgui.NOTIFICATION_ERROR)
            return

        data = {"bdata": "", "customerNr": __customer_id, "next": ""}
        data.update(parse_input_values(req.content))

        req = r.post(url_post, data=data)

        data = {"bdata": "", "passid02": __password}

    # STEP 3.2: SEND PASSWORD
    else:
        data = {"hidden_usr": __login, "bdata": "", "pw_pwd": __password, "pw_submit": ""}
        
    data.update(parse_input_values(req.content))
    req = r.post(url_post, data=data)

    # STEP 3.3: CHECK FOR ADDITIONAL PASSKEY STEP
    if "Passkey: Die neue Anmeldeoption" in str(req.content):
        data = {"pkc": "", "webauthnError": "", "dont_ask_again": ""}
  
        data.update(parse_input_values(req.content))
        req = r.post(url_post, data=data)

    try:    
        codes = {i.split("=")[0]: i.split("=")[1] for i in req.url.split("?")[1].split("&")}
    except:
        xbmcgui.Dialog().notification(__addonname__, "Login-Fehler: Bitte Anmeldedaten prüfen. (Code: 1)", xbmcgui.NOTIFICATION_ERROR)
        return
    
    r.get(req.url)

    # STEP 4: RETRIEVE ACCESS TOKEN FOR USER
    try:
        sso_auth_url = f"{sso_url}/authenticate"
        sso_req = s.post(sso_auth_url, data=json.dumps({"checkRefreshToken": True, "returnCode": {"code": codes["code"], "state": codes["state"]}}))
        info = sso_req.json()
    except:
        xbmcgui.Dialog().notification(__addonname__, "Login-Fehler: Bitte Anmeldedaten prüfen. (Code: 2)", xbmcgui.NOTIFICATION_ERROR)
        return

    # RETURN BASIC AUTH TOKEN + JWT
    try:
        p_token = info["userInfo"]["personaToken"]  
        xbmcgui.Dialog().notification(__addonname__, "Angemeldet", xbmcgui.NOTIFICATION_INFO) # Notify success
        return p_token
    except:
        xbmcgui.Dialog().notification(__addonname__, "Login-Fehler: Bitte Anmeldedaten prüfen. (Code: 3)", xbmcgui.NOTIFICATION_ERROR)
        return


#
# CACHE & EPG HELPERS
#

def update_epg_cache():
    """Downloads the EPG file if cache is expired or missing."""
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
    """Returns cached channel JSON if valid."""
    if os.path.exists(CACHE_FILE_CHANNELS):
        if (time.time() - os.path.getmtime(CACHE_FILE_CHANNELS)) < CACHE_TIME_CHANNELS:
            try:
                with open(CACHE_FILE_CHANNELS, 'r') as f:
                    return json.load(f)
            except:
                pass
    return None

def save_channels_cache(data):
    """Saves channel JSON to cache."""
    try:
        with open(CACHE_FILE_CHANNELS, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        xbmc.log(f"MTV2: Cache Save Error: {str(e)}", xbmc.LOGERROR)

#
# CHANNEL LIST
#

# Generates the M3U channel list
def channel_list(token, force_refresh=False):
    
    ch_list = None
    
    # Try Cache first
    if not force_refresh:
        ch_list = get_cached_channels()
        if ch_list:
            xbmc.log("MTV2: Loading channels from cache", xbmc.LOGINFO)

    # Fetch from API if no cache or forced
    if not ch_list:
        if not token:
            return None # Cannot fetch without token
            
        r = requests.Session()
        r.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        })

        try:
            xbmc.log("MTV2: Fetching channels from API", xbmc.LOGINFO)
            url = f"{feed_url}/f/mdeprod/mdeprod-channel-stations-main?lang=short-de&sort=dt%24displayChannelNumber&range=1-500"
            req = r.get(url)
            ch_list = req.json()
            # Save to cache
            save_channels_cache(ch_list)
        except:
            return

    # Build M3U
    output = '#EXTM3U x-tvg-url="http://localhost:4700/api/file/guide.xml"\n'
    
    # Load addon settings
    hide_sd = __addon__.getSettingBool("hide_sd")

    try:
        for chan in ch_list["entries"]:
            chan_url = [*chan["stations"]][0]
            if chan["stations"][chan_url]["era$mediaPids"].get("urn:theplatform:tv:location:any"):
                
                # Apply channel filter and naming logic
                is_hd = chan["stations"][chan_url]["dt$quality"] == "HD"
                base_title = chan["stations"][chan_url]["title"]

                if hide_sd:
                    if not is_hd:
                        continue  # Filter out SD channel
                    chan_title = base_title  # Use base title (no " HD" suffix)
                else:
                    # Default behavior: add " HD" if it's HD
                    chan_title = f'{base_title} HD' if is_hd else base_title

                # Construct Logo URL
                logo_url = "https://ngiss.t-online.de/iss?client=ftp22&out=webp&x=512&y=512&ar=keep&src="+urllib.parse.quote(chan["stations"][chan_url]["thumbnails"]["stationBackground"]["url"])

                output = \
                    f'{output}' \
                    f'#KODIPROP:inputstreamclass=inputstream.adaptive\n' \
                    f'#KODIPROP:inputstream.adaptive.manifest_type=mpd\n' \
                    f'#KODIPROP:inputstream.adaptive.license_type=com.widevine.alpha\n' \
                    f'#KODIPROP:inputstream.adaptive.license_key=http://localhost:4700/api/fw/{chan["stations"][chan_url]["era$mediaPids"]["urn:theplatform:tv:location:any"]}/license||R' + '{SSM}|\n' \
                    f'#EXTINF:0001 tvg-id="{"tkm_"+str(chan["channelNumber"])}" tvg-logo="{logo_url}", {chan_title}\n' \
                    f'http://localhost:4700/api/fw/{chan["stations"][chan_url]["era$mediaPids"]["urn:theplatform:tv:location:any"]}/manifest.mpd\n'
        return output
    except Exception as e:
        xbmc.log(str(e))
        return


#
# CHANNEL MPD
#

# Generates the MPD manifest for a channel
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
        
        ch_data = xmltodict.parse(req.content)
        r.get(f"https://concurrency.delivery.theplatform.eu/concurrency/web/Concurrency/unlock?_clientId={__device_id}&_encryptedLock={urllib.parse.quote(ch_data['smil']['head']['meta'][5]['@content'])}&_id={urllib.parse.quote(ch_data['smil']['head']['meta'][3]['@content'])}&_sequenceToken={urllib.parse.quote(ch_data['smil']['head']['meta'][4]['@content'])}&form=json&schema=1.0")

        video_src = ch_data['smil']['body']['seq']['switch']['switch']['video'][0]['@src']
        video_args = {i.split("=")[0]: i.split("=")[1] for i in ch_data['smil']['body']['seq']['switch']['ref']['param']['@value'].split("|")}

        release_pids[channel] = video_args["pid"]

        mpd = requests.get(video_src)
        xml = xmltodict.parse(mpd.content)
        xml["MPD"]["Period"]["BaseURL"] = f"{video_src.replace('/index.mpd', '')}/dash"

        return xmltodict.unparse(xml, pretty=True)
    except Exception as e:
        xbmc.log(str(e))
        return


#
# CHANNEL LICENSE
#

# Generates the Widevine license URL
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


#
# MAIN PROCESS
#

# Main service entry point
def start():
    
    t = WebServer()

    # START SERVER (+ STOP SERVER BEFORE CLOSING KODI)
    monitor = xbmc.Monitor()
    while not monitor.abortRequested():
        if monitor.waitForAbort(1):
            break
    t.stop_kodi()


if __name__ == "__main__":
    start()
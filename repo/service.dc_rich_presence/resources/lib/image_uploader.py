import os
import base64
import urllib.parse
import requests
import xbmc
import time

IMGBB_API_URL = "https://api.imgbb.com/1/upload"
CACHE = {}  # key: image_path, value: (timestamp, url)
CACHE_EXPIRY = 14400  # 4 Stunden

def decode_kodi_image_url(image_url):
    """
    Entfernt 'image://' Präfix, trailing '/', und dekodiert URL-Encoding.
    """
    if not image_url:
        return None
    try:
        if image_url.startswith("image://"):
            clean_url = image_url[len("image://"):]
            if clean_url.endswith("/"):
                clean_url = clean_url[:-1]
            return urllib.parse.unquote(clean_url)
        return image_url
    except Exception as e:
        xbmc.log(f"[DiscordRPC] Image decode failed: {e}", xbmc.LOGWARNING)
        return None

def upload_to_imgbb(image_path, api_key):
    """
    Lädt ein lokales Bild zu imgbb hoch, cached Ergebnis für 4h.
    """
    now = time.time()

    # Cache-Check
    if image_path in CACHE:
        ts, url = CACHE[image_path]
        if now - ts < CACHE_EXPIRY:
            xbmc.log(f"[DiscordRPC] Using cached imgbb URL: {url}", xbmc.LOGDEBUG)
            return url
        else:
            del CACHE[image_path]

    try:
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")

        response = requests.post(IMGBB_API_URL, data={
            "key": api_key,
            "image": encoded,
            "expiration": str(CACHE_EXPIRY)
        }, timeout=10)

        response.raise_for_status()
        data = response.json()
        url = data["data"]["url"]
        CACHE[image_path] = (now, url)

        xbmc.log(f"[DiscordRPC] Uploaded image to imgbb: {url}", xbmc.LOGINFO)
        return url

    except Exception as e:
        xbmc.log(f"[DiscordRPC] imgbb upload failed: {e}", xbmc.LOGERROR)
        return None

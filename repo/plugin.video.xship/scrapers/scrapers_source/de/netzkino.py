

# edit 2024-11-14

from resources.lib.utils import isBlockedHoster
import json
from resources.lib.requestHandler import cRequestHandler
from scrapers.modules import cleantitle, dom_parser
from resources.lib.control import getSetting
from resources.lib.utils import getExtIDS

SITE_IDENTIFIER = 'netzkino'
SITE_DOMAIN = 'www.netzkino.de'
SITE_NAME = SITE_IDENTIFIER.upper()

# 'https://api.netzkino.de.simplecache.net/capi-2.0a/search?q=%s&d=www&l=de-DE'
class source:
    def __init__(self):
        self.priority = 1
        self.language = ['de']
        self.domain = getSetting('provider.' + SITE_IDENTIFIER + '.domain', SITE_DOMAIN)
        self.base_link = 'https://' + self.domain

        #self.search_api = 'https://api.netzkino.de.simplecache.net/capi-2.0a/search?q=%s&d=www&l=de-DE'
        self.search_api = 'https://api.netzkino.de.simplecache.net/capi-2.0a/movies/%s.json?d=www'  # id 726633
        self.get_link = 'movie/load-stream/%s/%s?'
        self.sources = []


    def run(self, titles, year, season=0, episode=0, imdb='', hostDict=None):
        if season > 0: return self.sources
        try:
            aIDS = getExtIDS(imdb, 'movies')
            slug = aIDS['slug'].rsplit('-', 1)[0]
            oRequest = cRequestHandler(self.search_api % slug)
            item = json.loads(oRequest.request())
            if 'No such slug found' in str(item): return self.sources
            elif not int(item['custom_fields']['Jahr'][0]) == year: return self.sources
            elif 'Streaming' in item['custom_fields'] and item['custom_fields']['Streaming'][0]:
                stream = 'https://pmd.netzkino-seite.netzkino.de/%s.mp4' % item['custom_fields']['Streaming'][0]
                quality = item['custom_fields']['Adaptives_Streaming'][0] if item['custom_fields']['Adaptives_Streaming'][0] else '1080p'
                self.sources.append(
                    {'source': 'Netzkino', 'quality': quality, 'language': 'de', 'url': stream, 'direct': True})
            # if 'Youtube_Delivery_Id' in item['custom_fields'] and item['custom_fields']['Youtube_Delivery_Id'][0]:
            #     stream = 'plugin://plugin.video.youtube/play/?video_id=%s' % item['custom_fields']['Youtube_Delivery_Id'][0]
            #     self.sources.append(
            #         {'source': 'Youtube', 'quality': item['custom_fields']['Adaptives_Streaming'][0], 'language': 'de', 'url': stream, 'direct': True})

            return self.sources
        except:
            return self.sources

    def resolve(self, url):
        try:
            return url
        except:
            return



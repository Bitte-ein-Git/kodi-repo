# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, unicode_literals

# Standard library imports
import re
import os
import unicodedata
import traceback # Added for better error logging in export

# Kodi imports
from xbmcvfs import translatePath, mkdirs, exists, File
from resources.lib.kodi.utils import get_addon_profile_path, get_form_data_from_string # Assuming this is from a local helper
from resources.lib.kodi.utils import get_form_data_from_params, get_page, get_url, get_addon_id, get_addon_version # Assuming these too
from resources.lib.kodi.utils import json, unquote, unquote_plus, urlencode, parse_qsl, quote # Assuming these too

# Local imports
from resources.lib.external.singleton import Singleton
from resources.lib.compat import compat

from resources.lib.xbmc_helper import xbmc_helper
from resources.lib.lib_joyn import lib_joyn # Direct import needed if used outside plugin_instance
from resources.lib.submodules.plugin_lastseen import plugin_lastseen
from resources.lib.submodules.libjoyn_video import libjoyn_video
from resources.lib.submodules.libjoyn_auth import libjoyn_auth

pluginurl = compat.sys.argv[0]
addon_id = get_addon_id()
addon_version = get_addon_version()
profile_path = get_addon_profile_path()
default_icon = translatePath(os.path.join(profile_path, '..', 'icon.png'))
default_fanart = translatePath(os.path.join(profile_path, '..', 'fanart.jpg'))
language = xbmc_helper().get_language()
search_history_file = os.path.join(profile_path, 'search_history.json')


@Singleton
class plugin(object):

    def __init__(self):
        self.lib_joyn = lib_joyn()
        self.libjoyn_video = libjoyn_video()
        self.libjoyn_auth = libjoyn_auth()
        self.plugin_last = plugin_lastseen()

    def run(self, params):
        xbmc_helper().log(msg='Call plugin with params: {}'.format(params), level=xbmc_helper().log_debug)
        param_keys = params.keys()
        mode = params.get('mode')
        if mode:
            xbmc_helper().log(msg='Mode: {}'.format(mode), level=xbmc_helper().log_debug)
        if 'page' in param_keys:
            page = int(params['page'])
        else:
            page = 1
        if 'title' in param_keys:
            title = params['title']
        else:
            title = ''
        if 'search_term' in param_keys:
            search_term = params['search_term']
        else:
            search_term = ''
        if 'path' in param_keys:
            path = params['path']
        else:
            path = ''
        if 'block_id' in param_keys:
            block_id = params['block_id']
        else:
            block_id = ''
        if 'parent_block_id' in param_keys:
            parent_block_id = params['parent_block_id']
        else:
            parent_block_id = ''
        if 'compilation_id' in param_keys:
            compilation_id = params['compilation_id']
        else:
            compilation_id = ''
        if 'channel_id' in param_keys:
            channel_id = params['channel_id']
        else:
            channel_id = ''
        if 'movie_id' in param_keys:
            movie_id = params['movie_id']
        else:
            movie_id = ''
        if 'tv_show_id' in param_keys:
            tv_show_id = params['tv_show_id']
        else:
            tv_show_id = ''
        if 'season_id' in param_keys:
            season_id = params['season_id']
        else:
            season_id = ''
        if 'teaser_id' in param_keys:
            teaser_id = params['teaser_id']
        else:
            teaser_id = ''
        if 'video_id' in param_keys:
            video_id = params['video_id']
        else:
            video_id = ''
        if 'client_data' in param_keys:
            client_data = params['client_data']
        else:
            client_data = ''
        if 'stream_type' in param_keys:
            stream_type = params['stream_type']
        else:
            stream_type = 'VOD'
        if 'viewtype' in param_keys:
            viewtype = params['viewtype']
        else:
            viewtype = ''

        if mode == 'login':
            self.libjoyn_auth.login()
        elif mode == 'logout':
            self.libjoyn_auth.logout()
        elif mode == 'play_video' and video_id:
            play_video(path, video_id, client_data, stream_type, season_id, movie_id)
        elif mode == 'play_movie' and path:
            play_movie(path, movie_id)
        elif mode == 'play_live' and channel_id:
            play_live(channel_id, title)
        elif mode == 'play_hbbtv' and path:
            play_hbbtv(path)
        elif mode == 'show_page' and path:
            show_page(path, title, page)
        elif mode == 'show_block' and path and (block_id or parent_block_id):
            show_block(path, block_id, parent_block_id, title)
        elif mode == 'show_compilation' and path and compilation_id:
            show_compilation(path, compilation_id, title)
        elif mode == 'show_movie_details' and path and movie_id:
            show_movie_details(path, movie_id)
        elif mode == 'show_tv_show_details' and path and (tv_show_id or movie_id):
            show_tv_show_details(path, (tv_show_id or movie_id))
        elif mode == 'season_episodes' and season_id:
            season_episodes(season_id)
        elif mode == 'trailer' and teaser_id:
            trailer(teaser_id)
        elif mode == 'search':
            search(search_term)
        elif mode == 'clear_search_history':
            clear_search_history()
        elif mode == 'live_tv':
            live_tv(page)
        elif mode == 'on_demand':
            on_demand()
        elif mode == 'originals':
            originals()
        elif mode == 'categories':
            categories()
        elif mode == 'sports':
            sports()
        elif mode == 'hbbtv':
            hbbtv(page)
        elif mode == 'last_seen':
            self.plugin_last.get_last_seen_items()
        elif mode == 'clear_cache':
            clear_cache()
        elif mode == 'export_to_library':
            export_to_library(params)
        elif mode == 'play_from_strm':
            play_from_strm(params)
        else:
            index(params)

    def get_search_history(self):
        # get search history from file
        if not exists(search_history_file):
            with compat.io_open(search_history_file, 'w', encoding='utf-8') as f:
                f.write(compat._unicode(json.dumps([])))
        with compat.io_open(search_history_file, 'r', encoding='utf-8') as f:
            search_history = json.load(f)
        return search_history

    def add_to_search_history(self, search_term):
        # add search term to history
        if not xbmc_helper().get_bool_setting('save_search_history'):
            return
        search_history = self.get_search_history()
        if search_term in search_history:
            search_history.remove(search_term)
        search_history.insert(0, search_term)
        with compat.io_open(search_history_file, 'w', encoding='utf-8') as f:
            f.write(compat._unicode(json.dumps(search_history)))

    def remove_from_search_history(self, search_term):
        # remove search term from history
        search_history = self.get_search_history()
        search_history.remove(search_term)
        with compat.io_open(search_history_file, 'w', encoding='utf-8') as f:
            f.write(compat._unicode(json.dumps(search_history)))

    def get_dir_entry(self, params, metadata, is_folder=False, is_playable=False):
        # create directory entry
        mode = params.get('mode')
        list_item = xbmc_helper().get_list_item(metadata['infoLabels'].get('title', ''))
        list_item.setArt(metadata.get('artwork', {}))
        if metadata.get('infoLabels'):
            list_item.setInfo('video', metadata['infoLabels'])
        if metadata.get('properties'):
            for key, value in metadata['properties'].items():
                list_item.setProperty(key, value)
        if metadata.get('cast'):
            list_item.setCast(metadata['cast'])
        if metadata.get('ratings'):
            list_item.setRating(metadata['ratings'].get('rating', 0), metadata['ratings'].get('votes', 0),
                                metadata['ratings'].get('provider', ''))
        if metadata.get('stream_info'):
            for stream_type, stream_value in metadata['stream_info'].items():
                list_item.addStreamInfo(stream_type, stream_value)
        if metadata.get('subtitles'):
            list_item.setSubtitles(metadata['subtitles'])
        if is_playable:
            list_item.setProperty('IsPlayable', 'true')
        if mode == 'search' and 'search_term' in params.keys():
            # context menu for search history
            list_item.addContextMenuItems([
                (
                    xbmc_helper().get_string(30040),
                    compat._format(
                        'RunPlugin({}?{})',
                        pluginurl,
                        urlencode({
                            'mode': 'remove_from_search_history',
                            'search_term': params['search_term']
                        })
                    )
                )
            ])

        context_items = []

        # add library export context item
        info_labels = metadata.get('infoLabels', {})
        media_type = info_labels.get('mediatype')

        # Check if item is suitable for export (needs specific IDs)
        can_export = False
        if media_type == 'movie' and (params.get('movie_id') or params.get('path')):
            can_export = True
        elif media_type == 'episode' and params.get('video_id'):
             can_export = True
        # Allow export also from details pages where playability implies exportability
        elif is_playable and (mode == 'play_movie' or mode == 'play_video' or mode == 'show_movie_details'):
             can_export = True # Assume necessary IDs are present or derivable

        if can_export:
            export_params = params.copy() # Use the params dict built for the list item URL
            export_params['mode'] = 'export_to_library'

            # Ensure minimal required IDs are present or use placeholders
            export_params['mediatype'] = media_type if media_type else ('movie' if params.get('movie_id') else ('episode' if params.get('video_id') else 'unknown'))
            export_params['title'] = info_labels.get('title', 'Unknown Title')
            export_params['year'] = info_labels.get('year', '')
            export_params['plot'] = info_labels.get('plot', '')
            export_params['thumb'] = metadata.get('artwork', {}).get('thumb', '') or metadata.get('artwork', {}).get('icon', '')
            export_params['fanart'] = metadata.get('artwork', {}).get('fanart', default_fanart)

            if export_params['mediatype'] == 'movie':
                export_params['uniqueid'] = params.get('movie_id', params.get('path', '')) # Fallback to path if no movie_id
            elif export_params['mediatype'] == 'episode':
                export_params['tvshow_title'] = info_labels.get('tvshowtitle', 'Unknown Show')
                export_params['season'] = info_labels.get('season', '0') # Default to 0 if missing
                export_params['episode_num'] = info_labels.get('episode', '0') # Default to 0 if missing
                export_params['uniqueid'] = params.get('video_id', params.get('path', '')) # Fallback to path if no video_id

            # Pass necessary playback IDs
            export_params['path'] = params.get('path', '')
            export_params['movie_id'] = params.get('movie_id', '')
            export_params['video_id'] = params.get('video_id', '')
            export_params['season_id'] = params.get('season_id', '')


            context_items.append((
                xbmc_helper().get_string(30103), # Export to library
                compat._format('RunPlugin({}?{})', pluginurl, urlencode(export_params))
            ))

        if context_items:
            list_item.addContextMenuItems(context_items)

        return (compat._format('{}?{}', pluginurl, urlencode(params)), list_item, is_folder)

    def show_listing(self, listing, viewtype='', page=1, total_pages=1, sort_methods=None):
        # show listing
        if not sort_methods:
            sort_methods = []
        if viewtype == 'thumbnail':
            xbmc_helper().set_view(xbmc_helper().get_int_setting('thumbnail_view'))
        elif viewtype == 'season':
            xbmc_helper().set_view(xbmc_helper().get_int_setting('season_view'))
        elif viewtype == 'episode':
            xbmc_helper().set_view(xbmc_helper().get_int_setting('episode_view'))
        elif viewtype == 'movie':
            xbmc_helper().set_view(xbmc_helper().get_int_setting('movie_view'))
        else:
            xbmc_helper().set_view(xbmc_helper().get_int_setting('default_view'))

        if listing:
            if page > 1:
                # previous page item
                params = compat.sys.argv[2]
                params = get_form_data_from_string(params)
                params['page'] = page - 1
                metadata = {
                    'infoLabels': {
                        'title': compat._format('{} {}', xbmc_helper().get_string(30083), page - 1) # Previous
                    },
                    'artwork': {
                        'icon': 'DefaultFolderBack.png'
                    },
                    'properties': {
                        'SpecialSort': 'top'
                    }
                }
                xbmc_helper().add_dir_item(self.get_dir_entry(params, metadata, is_folder=True))

            xbmc_helper().add_dir_items(listing) # Add actual items

            if page < total_pages:
                # next page item
                params = compat.sys.argv[2]
                params = get_form_data_from_string(params)
                params['page'] = page + 1
                metadata = {
                    'infoLabels': {
                        'title': compat._format('{} {}', xbmc_helper().get_string(30084), page + 1) # Next
                    },
                    'artwork': {
                        'icon': 'DefaultFolder.png'
                    },
                    'properties': {
                        'SpecialSort': 'bottom'
                    }
                }
                xbmc_helper().add_dir_item(self.get_dir_entry(params, metadata, is_folder=True))

            xbmc_helper().end_of_directory(sort_methods=sort_methods)
        else:
            xbmc_helper().end_of_directory()


plugin_instance = plugin() # Create singleton instance


def index(params):
    # main menu
    show_search = xbmc_helper().get_bool_setting('show_search_in_main_menu')
    show_search_history = xbmc_helper().get_bool_setting('show_search_history_in_main_menu')
    show_last_seen = xbmc_helper().get_bool_setting('show_last_seen_in_main_menu')
    show_live_tv = xbmc_helper().get_bool_setting('show_live_tv_in_main_menu')
    show_on_demand = xbmc_helper().get_bool_setting('show_ondemand_in_main_menu')
    show_originals = xbmc_helper().get_bool_setting('show_originals_in_main_menu')
    show_categories = xbmc_helper().get_bool_setting('show_categories_in_main_menu')
    show_sports = xbmc_helper().get_bool_setting('show_sports_in_main_menu')
    show_hbbtv = xbmc_helper().get_bool_setting('show_hbbtv_in_main_menu')
    show_settings = xbmc_helper().get_bool_setting('show_settings_in_main_menu')

    listing = []
    if show_live_tv:
        params = {'mode': 'live_tv'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30087)}} # Live TV
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_on_demand:
        params = {'mode': 'on_demand'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30088)}} # On Demand
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_originals:
        params = {'mode': 'originals'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30089)}} # Originals
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_categories:
        params = {'mode': 'categories'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30090)}} # Categories
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_sports:
        params = {'mode': 'sports'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30091)}} # Sports
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_search:
        params = {'mode': 'search'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30092)}} # Search
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_last_seen:
        params = {'mode': 'last_seen'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30094)}} # Last Seen
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_search_history and xbmc_helper().get_bool_setting('save_search_history'):
        params = {'mode': 'search', 'search_term': 'show_search_history'}
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30095)}} # Search history
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_hbbtv:
        params = {'mode': 'hbbtv'}
        metadata = {'infoLabels': {'title': 'HbbTV'}} # HbbTV (Add translation if needed)
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=True))
    if show_settings:
        params = {'mode': 'settings'}
        # Assuming settings is an action, not a folder
        metadata = {'infoLabels': {'title': xbmc_helper().get_string(30093)}} # Settings
        listing.append(plugin_instance.get_dir_entry(params, metadata, is_folder=False)) # is_folder=False

    plugin_instance.show_listing(listing)


def live_tv(page):
    # list live tv channels
    listing = []
    live_tv_data = plugin_instance.lib_joyn.get_live_tv(page)
    show_live_tv_previews = xbmc_helper().get_bool_setting('show_live_tv_previews')
    if live_tv_data:
        for item in live_tv_data['items']:
            params = {
                'mode': 'play_live',
                'channel_id': item['channel_id'],
                'title': item['infoLabels']['title']
            }
            if show_live_tv_previews:
                item['infoLabels']['plot'] = plugin_instance.lib_joyn.get_live_tv_preview(item['channel_id'])
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=False, is_playable=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail', page=live_tv_data['page'],
                                     total_pages=live_tv_data['total_pages'])


def on_demand():
    # list on demand categories
    listing = []
    on_demand_data = plugin_instance.lib_joyn.get_on_demand()
    if on_demand_data:
        for item in on_demand_data['items']:
            params = {
                'mode': 'show_page',
                'path': item['path'],
                 'title': item['infoLabels']['title'] # Pass title for breadcrumbs/header
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail')


def originals():
    # list originals categories
    listing = []
    originals_data = plugin_instance.lib_joyn.get_originals()
    if originals_data:
        for item in originals_data['items']:
            params = {
                'mode': 'show_page',
                'path': item['path'],
                'title': item['infoLabels']['title'] # Pass title
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail')


def categories():
    # list categories
    listing = []
    categories_data = plugin_instance.lib_joyn.get_categories()
    if categories_data:
        for item in categories_data['items']:
            params = {
                'mode': 'show_page',
                'path': item['path'],
                'title': item['infoLabels']['title'] # Pass title
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail')


def sports():
    # list sports categories
    listing = []
    sports_data = plugin_instance.lib_joyn.get_sports()
    if sports_data:
        for item in sports_data['items']:
            params = {
                'mode': 'show_page',
                'path': item['path'],
                'title': item['infoLabels']['title'] # Pass title
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail')


def hbbtv(page):
    # list hbbtv links
    listing = []
    hbbtv_data = plugin_instance.lib_joyn.get_hbbtv_links(page)
    if hbbtv_data:
        for item in hbbtv_data['items']:
            params = {
                'mode': 'play_hbbtv',
                'path': item['path']
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=False, is_playable=True))
        plugin_instance.show_listing(listing, viewtype='thumbnail', page=hbbtv_data['page'],
                                     total_pages=hbbtv_data['total_pages'])


def search(search_term):
    # perform search or show history
    listing = []
    if not search_term:
        search_term = xbmc_helper().get_keyboard_input(heading=xbmc_helper().get_string(30092)) # Search
    if search_term:
        if search_term == 'show_search_history':
            # show search history
            search_history = plugin_instance.get_search_history()
            max_items = xbmc_helper().get_int_setting('search_items_count')
            if max_items > 0:
                 search_history = search_history[:max_items]
            for item in search_history:
                params = {
                    'mode': 'search',
                    'search_term': item
                }
                metadata = {
                    'infoLabels': {
                        'title': item
                    }
                }
                # Add context menu to remove item from history
                entry = plugin_instance.get_dir_entry(params, metadata, is_folder=True)
                entry[1].addContextMenuItems([(
                     xbmc_helper().get_string(30040), # Clear search history (actually, remove item)
                     compat._format('RunPlugin({}?mode=remove_from_search_history&search_term={})', pluginurl, quote(item))
                )])
                listing.append(entry)
            plugin_instance.show_listing(listing)
        else:
            # perform search
            plugin_instance.add_to_search_history(search_term)
            search_data = plugin_instance.lib_joyn.search(search_term)
            if search_data:
                for item in search_data['items']:
                    params = {
                        'mode': item['mode'],
                        'path': item.get('path', ''),
                        'compilation_id': item.get('compilation_id'),
                        'movie_id': item.get('movie_id'),
                        'tv_show_id': item.get('tv_show_id'),
                        'season_id': item.get('season_id'),
                        'title': item['infoLabels']['title'] # Pass title
                    }
                    # Determine folder/playable status based on mode
                    is_folder = True
                    is_playable = False
                    if item.get('mode') == 'show_movie_details':
                        is_playable = True # Movie details page is folder, but item implies playability
                    elif item.get('mode') == 'season_episodes':
                        is_folder = True
                    elif item.get('mode') == 'show_tv_show_details':
                        is_folder = True
                    elif item.get('mode') == 'show_compilation':
                         is_folder = True
                    # Add other modes if necessary

                    listing.append(plugin_instance.get_dir_entry(params, item, is_folder=is_folder, is_playable=is_playable))
                plugin_instance.show_listing(listing, viewtype='thumbnail')


def clear_search_history():
    # clear search history file
    if xbmc_helper().get_dialog_yes_no(text=xbmc_helper().get_string(30041)): # Really clear?
        with compat.io_open(search_history_file, 'w', encoding='utf-8') as f:
            f.write(compat._unicode(json.dumps([])))
        xbmc_helper().refresh() # Refresh current view


def show_page(path, title, page):
    # show items from a generic page
    listing = []
    page_data = plugin_instance.lib_joyn.get_page(path, page)
    if page_data:
        for item in page_data['items']:
            params = {
                'mode': item['mode'],
                'path': item.get('path', ''),
                'block_id': item.get('block_id'),
                'parent_block_id': item.get('parent_block_id'),
                'compilation_id': item.get('compilation_id'),
                'movie_id': item.get('movie_id'),
                'tv_show_id': item.get('tv_show_id'),
                'title': item['infoLabels']['title'] # Pass title
            }
            # Determine folder/playable status based on mode
            is_folder = True
            is_playable = False
            if item.get('mode') == 'show_movie_details':
                is_playable = True
            # Add other modes if necessary

            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=is_folder, is_playable=is_playable))
        xbmc_helper().set_title(title)
        plugin_instance.show_listing(listing, viewtype='thumbnail', page=page_data['page'],
                                     total_pages=page_data['total_pages'])


def show_block(path, block_id, parent_block_id, title):
    # show items from a specific block
    listing = []
    block_data = plugin_instance.lib_joyn.get_block(path, block_id, parent_block_id)
    if block_data:
        for item in block_data['items']:
            params = {
                'mode': item['mode'],
                'path': item.get('path', ''),
                'block_id': item.get('block_id'),
                'parent_block_id': item.get('parent_block_id'),
                'compilation_id': item.get('compilation_id'),
                'movie_id': item.get('movie_id'),
                'tv_show_id': item.get('tv_show_id'),
                'title': item['infoLabels']['title'] # Pass title
            }
             # Determine folder/playable status based on mode
            is_folder = True
            is_playable = False
            if item.get('mode') == 'show_movie_details':
                is_playable = True
            # Add other modes if necessary

            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=is_folder, is_playable=is_playable))
        xbmc_helper().set_title(title)
        plugin_instance.show_listing(listing, viewtype='thumbnail', page=block_data['page'],
                                     total_pages=block_data['total_pages'])


def show_compilation(path, compilation_id, title):
    # show items from a compilation
    listing = []
    compilation_data = plugin_instance.lib_joyn.get_compilation(path, compilation_id)
    if compilation_data:
        for item in compilation_data['items']:
            params = {
                'mode': item['mode'],
                'path': item.get('path', ''),
                'movie_id': item.get('movie_id'),
                'tv_show_id': item.get('tv_show_id'),
                'title': item['infoLabels']['title'] # Pass title
            }
             # Determine folder/playable status based on mode
            is_folder = True
            is_playable = False
            if item.get('mode') == 'show_movie_details':
                is_playable = True
            # Add other modes if necessary

            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=is_folder, is_playable=is_playable))
        xbmc_helper().set_title(title)
        plugin_instance.show_listing(listing, viewtype='thumbnail')


def show_movie_details(path, movie_id):
    # show movie details, trailer, similar movies
    listing = []
    movie_details = plugin_instance.lib_joyn.get_movie_details(path, movie_id)
    if movie_details:
        # Playable item for the movie itself
        params_play = {
            'mode': 'play_movie',
            'path': path,
            'movie_id': movie_id,
            # Pass metadata needed for export context item
            'title': movie_details['play']['infoLabels'].get('title', ''),
            'year': movie_details['play']['infoLabels'].get('year', ''),
            'plot': movie_details['play']['infoLabels'].get('plot', ''),
            'thumb': movie_details['play']['artwork'].get('thumb', ''),
            'fanart': movie_details['play']['artwork'].get('fanart', '')
        }
        listing.append(plugin_instance.get_dir_entry(params_play, movie_details['play'], is_folder=False, is_playable=True))

        # Trailer item
        if movie_details.get('trailer'):
            params_trailer = {
                'mode': 'trailer',
                'teaser_id': movie_details['trailer']['teaser_id']
            }
            listing.append(
                plugin_instance.get_dir_entry(params_trailer, movie_details['trailer'], is_folder=False, is_playable=True))

        # Similar items
        if movie_details.get('similar'):
            for item in movie_details['similar']['items']:
                params_similar = {
                    'mode': 'show_movie_details',
                    'path': item.get('path', ''),
                    'movie_id': item.get('movie_id'),
                    'title': item['infoLabels']['title'] # Pass title
                }
                listing.append(plugin_instance.get_dir_entry(params_similar, item, is_folder=True, is_playable=True))

        xbmc_helper().set_title(movie_details['play']['infoLabels']['title'])
        plugin_instance.show_listing(listing, viewtype='movie')


def show_tv_show_details(path, tv_show_id):
    # show tv show details, trailer, seasons, similar shows
    listing = []
    tv_show_details = plugin_instance.lib_joyn.get_tv_show_details(path, tv_show_id)
    show_title = "TV Show" # Default title
    if tv_show_details:
        # Trailer item
        if tv_show_details.get('trailer'):
            params_trailer = {
                'mode': 'trailer',
                'teaser_id': tv_show_details['trailer']['teaser_id']
            }
            listing.append(
                plugin_instance.get_dir_entry(params_trailer, tv_show_details['trailer'], is_folder=False, is_playable=True))

        # Season items
        if tv_show_details.get('seasons'):
            # Try to get show title from the first season item
            if tv_show_details['seasons']['items']:
                 show_title = tv_show_details['seasons']['items'][0]['infoLabels'].get('tvshowtitle', show_title)
            for item in tv_show_details['seasons']['items']:
                params_season = {
                    'mode': 'season_episodes',
                    'season_id': item['season_id'],
                    'title': item['infoLabels']['title'] # Pass season title
                }
                listing.append(plugin_instance.get_dir_entry(params_season, item, is_folder=True))

        # Similar items
        if tv_show_details.get('similar'):
            for item in tv_show_details['similar']['items']:
                params_similar = {
                    'mode': 'show_tv_show_details',
                    'path': item.get('path', ''),
                    'tv_show_id': item.get('tv_show_id'),
                    'title': item['infoLabels']['title'] # Pass title
                }
                listing.append(plugin_instance.get_dir_entry(params_similar, item, is_folder=True))

        xbmc_helper().set_title(show_title)
        plugin_instance.show_listing(listing, viewtype='season')


def season_episodes(season_id):
    # list episodes for a season
    listing = []
    season_episodes_data = plugin_instance.lib_joyn.get_season_episodes(season_id)
    show_title = "Season" # Default title
    if season_episodes_data and season_episodes_data.get('items'):
         show_title = season_episodes_data['items'][0]['infoLabels'].get('tvshowtitle', show_title)
         for item in season_episodes_data['items']:
            params = {
                'mode': 'play_video',
                'path': item.get('path', ''), # Ensure path is included if available/needed
                'video_id': item['video_id'],
                'client_data': item.get('client_data', ''), # Ensure client_data exists
                'stream_type': item.get('stream_type', 'VOD'), # Ensure stream_type exists
                'season_id': season_id,
                'movie_id': item.get('movie_id', ''), # Include movie_id if relevant
                 # Pass metadata needed for export context item
                 'title': item['infoLabels'].get('title', ''),
                 'year': item['infoLabels'].get('year', ''),
                 'plot': item['infoLabels'].get('plot', ''),
                 'thumb': item['artwork'].get('thumb', ''),
                 'fanart': item['artwork'].get('fanart', ''),
                 'tvshow_title': item['infoLabels'].get('tvshowtitle', ''),
                 'season': item['infoLabels'].get('season', ''),
                 'episode_num': item['infoLabels'].get('episode', '')
            }
            listing.append(plugin_instance.get_dir_entry(params, item, is_folder=False, is_playable=True))

         xbmc_helper().set_title(show_title)
         plugin_instance.show_listing(listing, viewtype='episode',
                                     sort_methods=[xbmc_helper().sort_method_episode, xbmc_helper().sort_method_label])
    else:
         plugin_instance.show_listing(listing) # Show empty list if no items


def trailer(teaser_id):
    # play trailer
    video_details = plugin_instance.lib_joyn.get_video_details(teaser_id, '', 'TEASER')
    if video_details:
        play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
        if play_item:
            xbmc_helper().play(play_item)


def play_video(path, video_id, client_data, stream_type='VOD', season_id='', movie_id=''):
    # play VOD video (usually episode)
    video_details = plugin_instance.lib_joyn.get_video_details(video_id, path, stream_type, client_data)
    if video_details:
        play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
        if play_item:
            plugin_instance.plugin_last.add_last_seen_item(video_id, video_details, {
                'mode': 'play_video',
                'path': path,
                'video_id': video_id,
                'client_data': client_data, # Use the potentially updated client_data
                'stream_type': stream_type,
                'season_id': season_id,
                'movie_id': movie_id
            })
            xbmc_helper().play(play_item)


def play_movie(path, movie_id):
    # play movie (needs details fetched first)
    video_details = plugin_instance.lib_joyn.get_video_details_from_movie(path, movie_id)
    if video_details:
        play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
        if play_item:
            plugin_instance.plugin_last.add_last_seen_item(movie_id, video_details, {
                'mode': 'play_movie', # Keep original mode for identification?
                'path': path,
                'movie_id': movie_id
                # Add video_id etc. if available from video_details for consistency?
            })
            xbmc_helper().play(play_item)


def play_live(channel_id, title):
    # play live tv channel
    video_details = plugin_instance.lib_joyn.get_video_details(channel_id, '', 'LIVE', '', title)
    if video_details:
        play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
        if play_item:
            xbmc_helper().play(play_item)


def play_hbbtv(path):
    # play hbbtv link
    video_details = plugin_instance.lib_joyn.get_video_details_from_hbbtv(path)
    if video_details:
        play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
        if play_item:
            xbmc_helper().play(play_item)


def clear_cache():
    # clear addon cache
    plugin_instance.lib_joyn.clear_cache()
    xbmc_helper().notification('Cache', 'Cache cleared', default_icon) # Add translation

# --- Library Export Functions ---

def vfs_path_join(*args):
    # normalize slashes for vfs
    return '/'.join(s.strip('/') for s in args if s).replace('\\', '/')

def slugify(value):
    # create safe filename
    value = compat._unicode(value)
    try:
        # try normalizing unicode
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    except TypeError:
        pass # Handle case where value might not be unicode correctly
    value = re.sub(r'[^\w\s-]', '', value).strip().lower() # remove invalid chars
    value = re.sub(r'[-\s]+', '-', value) # replace spaces/hyphens with single hyphen
    return value if value else 'untitled' # ensure not empty

# play function called by strm file
def play_from_strm(params):
    # play item from strm file, fetch fresh data
    media_type = params.get('mediatype')
    path = params.get('path') # Path might be important context for API calls
    unique_id = params.get('uniqueid') # Original ID used for export

    xbmc_helper().log(msg='Playing from STRM: {}'.format(params), level=xbmc_helper().log_info)

    try:
        if media_type == 'movie':
            movie_id = params.get('movie_id') or unique_id # Use unique_id as fallback
            if not movie_id and path: # If only path was stored
                 xbmc_helper().log(msg='Movie STRM has no movie_id, using path: {}'.format(path), level=xbmc_helper().log_warning)
                 # Might need to resolve movie_id from path if API allows, otherwise play_movie might fail
            elif not movie_id and not path:
                 raise Exception('Movie STRM missing movie_id and path')

            play_movie(path, movie_id) # play_movie handles fetching details

        elif media_type == 'episode':
            video_id = params.get('video_id') or unique_id # Use unique_id as fallback
            if not video_id:
                 raise Exception('Episode STRM missing video_id')

            # Fetch fresh video details (client_data etc.) using video_id and potentially path
            # Use the main lib_joyn instance from the plugin singleton
            video_details = plugin_instance.lib_joyn.get_video_details(video_id, path, 'VOD') # Assume VOD, client_data fetched internally

            if video_details and video_details.get('client_data'):
                # Call play_video with fresh data
                play_video(
                    path,
                    video_id,
                    video_details['client_data'],
                    video_details.get('stream_type', 'VOD'),
                    params.get('season_id', ''), # Pass season_id if available in STRM params
                    params.get('movie_id', '') # Pass movie_id if available in STRM params (unlikely for episodes)
                )
            elif video_details:
                 # If client_data is not needed or handled differently
                 xbmc_helper().log(msg='Playing episode without explicit client_data fetch (might be included in get_video_details)', level=xbmc_helper().log_debug)
                 play_item = plugin_instance.libjoyn_video.get_play_item(video_details)
                 if play_item:
                      xbmc_helper().play(play_item)
                 else:
                      raise Exception('Could not generate play item from details')
            else:
                raise Exception('Could not retrieve video details for episode')
        else:
            raise Exception(compat._format('Unknown mediatype in STRM: {}', media_type))

    except Exception as e:
        xbmc_helper().log_error('Failed to play from STRM: {} \n {}', e, traceback.format_exc())
        xbmc_helper().notification(xbmc_helper().get_string(30106), compat._str(e), default_icon) # Export failed

# export function called from context menu
def export_to_library(params):
    # export item to kodi library via strm/nfo files
    try:
        media_type = params.get('mediatype')
        title = params.get('title', 'Unknown')
        year = params.get('year', '')
        unique_id = params.get('uniqueid') # Should be movie_id or video_id

        if not unique_id:
             xbmc_helper().notification(xbmc_helper().get_string(30104), 'Missing unique ID for export', default_icon)
             return

        xbmc_helper().log(msg='Exporting to library: {}'.format(params), level=xbmc_helper().log_info)

        if media_type == 'movie':
            base_path_setting = xbmc_helper().get_text_setting('export_path_movies')
            if not base_path_setting:
                xbmc_helper().notification(xbmc_helper().get_string(30104), xbmc_helper().get_string(30105), default_icon) # Path not set
                return
            base_path = translatePath(base_path_setting)

            safe_title = slugify(title)
            safe_folder_name = compat._format('{} ({})', safe_title, year) if year else safe_title
            item_folder = vfs_path_join(base_path, safe_folder_name)
            strm_file = vfs_path_join(item_folder, compat._format('{}.strm', safe_folder_name))
            nfo_file = vfs_path_join(item_folder, compat._format('{}.nfo', safe_folder_name))

        elif media_type == 'episode':
            base_path_setting = xbmc_helper().get_text_setting('export_path_tvshows')
            if not base_path_setting:
                xbmc_helper().notification(xbmc_helper().get_string(30104), xbmc_helper().get_string(30105), default_icon) # Path not set
                return
            base_path = translatePath(base_path_setting)

            tvshow_title = params.get('tvshow_title', 'Unknown Show')
            season_num_str = params.get('season', '0')
            episode_num_str = params.get('episode_num', '0')

            # Ensure season/episode are integers for formatting
            try:
                 season_num = int(season_num_str)
            except ValueError:
                 season_num = 0
            try:
                 episode_num = int(episode_num_str)
            except ValueError:
                 episode_num = 0


            safe_show_title = slugify(tvshow_title)
            # Use year in show folder name if available? Kodi usually doesn't.
            show_folder = vfs_path_join(base_path, safe_show_title)
            season_folder = vfs_path_join(show_folder, compat._format('Season {}', season_num))

            safe_episode_title = slugify(title)
            # Kodi standard filename: SxxExx - Title.strm
            safe_filename = compat._format('S{}E{} - {}', str(season_num).zfill(2), str(episode_num).zfill(2), safe_episode_title)
            strm_file = vfs_path_join(season_folder, compat._format('{}.strm', safe_filename))
            nfo_file = vfs_path_join(season_folder, compat._format('{}.nfo', safe_filename))

            # Create tvshow.nfo if it doesn't exist
            tvshow_nfo_file = vfs_path_join(show_folder, 'tvshow.nfo')
            if not exists(tvshow_nfo_file):
                try:
                    mkdirs(show_folder) # Ensure show folder exists before writing NFO
                    # Basic tvshow.nfo, could fetch more details if needed
                    tvshow_nfo_content = compat._format(
                        '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
                        '<tvshow>\n'
                        '    <title>{}</title>\n'
                        # Use a stable ID if possible, maybe tv_show_id if available? Fallback to slug.
                        '    <uniqueid type="joyn" default="true">{}</uniqueid>\n'
                        '</tvshow>',
                        tvshow_title, params.get('tv_show_id', slugify(tvshow_title))
                    )
                    f = File(tvshow_nfo_file, 'w')
                    f.write(compat._bytes(tvshow_nfo_content, 'utf-8'))
                    f.close()
                except Exception as e:
                    xbmc_helper().log_error('Failed to write tvshow.nfo: {}', e) # Log error but continue
        else:
            xbmc_helper().notification(xbmc_helper().get_string(30104), compat._format('Cannot export type: {}', media_type), default_icon)
            return

        # Ensure target directory exists
        item_folder_for_strm = vfs_path_join(strm_file, '..')
        if not exists(item_folder_for_strm):
            mkdirs(item_folder_for_strm)

        # Check if STRM file already exists
        if exists(strm_file):
            # Optional: Ask user to overwrite? For now, just notify and stop.
            if xbmc_helper().get_dialog_yes_no(heading=xbmc_helper().get_string(30104), text=compat._format('{} {}', xbmc_helper().get_string(30108), '\nOverwrite?')): # File exists
                 pass # Continue to overwrite
            else:
                 return # User chose not to overwrite

        # Create .strm file content
        strm_params = {
            'mode': 'play_from_strm',
            'mediatype': media_type,
            'uniqueid': unique_id, # Store the original ID
            'title': title # Store title for reference/logging
            # Add IDs needed by play_from_strm to find the item again
        }
        if media_type == 'movie':
            strm_params['movie_id'] = params.get('movie_id')
            strm_params['path'] = params.get('path') # Path might be needed
        elif media_type == 'episode':
            strm_params['video_id'] = params.get('video_id')
            strm_params['path'] = params.get('path') # Path might be needed
            strm_params['season_id'] = params.get('season_id') # Include season_id if available

        # Remove empty params before encoding url
        strm_params = {k: v for k, v in strm_params.items() if v}
        strm_url = compat._format('{}?{}', pluginurl, urlencode(strm_params))

        # Write the .strm file
        f_strm = File(strm_file, 'w')
        f_strm.write(compat._bytes(strm_url, 'utf-8'))
        f_strm.close()
        xbmc_helper().log(msg='STRM file created: {}'.format(strm_file), level=xbmc_helper().log_debug)


        # Create .nfo file if enabled
        if xbmc_helper().get_bool_setting('export_nfo', True):
            nfo_content = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>\n'
            # Basic NFO structure
            if media_type == 'movie':
                nfo_content += '<movie>\n'
                nfo_content += compat._format('    <title>{}</title>\n', params.get('title', ''))
                nfo_content += compat._format('    <originaltitle>{}</originaltitle>\n', params.get('title', '')) # Assume same
                nfo_content += compat._format('    <year>{}</year>\n', params.get('year', ''))
                nfo_content += compat._format('    <plot>{}</plot>\n', params.get('plot', ''))
                nfo_content += compat._format('    <thumb aspect="poster">{}</thumb>\n', params.get('thumb', ''))
                nfo_content += compat._format('    <fanart><thumb>{}</thumb></fanart>\n', params.get('fanart', ''))
                # Use Joyn specific uniqueid if possible
                nfo_content += compat._format('    <uniqueid type="joyn" default="true">{}</uniqueid>\n', params.get('movie_id') or unique_id)
                nfo_content += '</movie>\n'

            elif media_type == 'episode':
                nfo_content += '<episodedetails>\n'
                nfo_content += compat._format('    <title>{}</title>\n', params.get('title', ''))
                nfo_content += compat._format('    <showtitle>{}</showtitle>\n', params.get('tvshow_title', ''))
                nfo_content += compat._format('    <season>{}</season>\n', params.get('season', ''))
                nfo_content += compat._format('    <episode>{}</episode>\n', params.get('episode_num', ''))
                nfo_content += compat._format('    <plot>{}</plot>\n', params.get('plot', ''))
                nfo_content += compat._format('    <thumb>{}</thumb>\n', params.get('thumb', ''))
                 # Use Joyn specific uniqueid if possible
                nfo_content += compat._format('    <uniqueid type="joyn" default="true">{}</uniqueid>\n', params.get('video_id') or unique_id)
                nfo_content += '</episodedetails>\n'

            # Write the .nfo file
            f_nfo = File(nfo_file, 'w')
            f_nfo.write(compat._bytes(nfo_content, 'utf-8'))
            f_nfo.close()
            xbmc_helper().log(msg='NFO file created: {}'.format(nfo_file), level=xbmc_helper().log_debug)


        xbmc_helper().notification(xbmc_helper().get_string(30104), xbmc_helper().get_string(30107), default_icon) # Export successful

    except Exception as e:
        xbmc_helper().log_error('Failed to export to library: {} \n {}', e, traceback.format_exc())
        xbmc_helper().notification(xbmc_helper().get_string(30106), compat._str(e), default_icon) # Export failed


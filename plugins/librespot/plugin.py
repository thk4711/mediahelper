import os
import sys
import time
import json
import spotipy
import webbrowser
import spotipy.util as util
from json.decoder import JSONDecodeError
import pprint
import urllib
import socket

os.environ["SPOTIPY_CLIENT_ID"]     = ""
os.environ["SPOTIPY_CLIENT_SECRET"] = ""
os.environ["SPOTIPY_REDIRECT_URI"]  = "https://google.com/"

username      = ''
cache_file    = '.cache-' + username
scope         = 'user-modify-playback-state user-read-currently-playing user-read-playback-state'
token         = None
spotifyObject = None
module_path   = None
hostname      = socket.gethostname()
d_id          = None
username      = ''

#------------------------------------------------------------------------------#
#                         do something on startup                              #
#------------------------------------------------------------------------------#
def init(path):
    global token
    global module_path
    module_path = path
    global username
    conf = read_config(path + '/plugin.conf')
    for key in conf:
        if key == 'spotify_username':
            username = conf[key]
        else:
            os.environ[key] = conf[key]
    #get_token()
    d_id = get_device_id()

#------------------------------------------------------------------------------#
#                         get a token from spotify                             #
#------------------------------------------------------------------------------#
def get_token():
    global spotifyObject
    try:
        token = util.prompt_for_user_token(username, scope)
        print(token)
    except:
        if os.path.isfile(myfile):
            os.remove(myfile)
            token = util.prompt_for_user_token(username, scope)
        else:
            print("Error: %s file not found" % cache_file)
    spotifyObject = spotipy.Spotify(auth=token)



#------------------------------------------------------------------------------#
#           read config file                                                   #
#------------------------------------------------------------------------------#
def read_config(config_file):
    if not os.path.isfile(config_file):
        print('ERROR config file', config_file, 'does not exist')
        exit(1)
    conf = {}
    with open(config_file) as f:
        content = f.readlines()
    for line in content:
        if line.startswith("#"):
            continue
        line = line.strip()
        key,value = line.split('=',2)
        key   = key.strip()
        value = value.strip()
        if value.lower() == 'no':
            value = False
        elif value.lower() == 'yes':
            value = True
        conf[key] = value
    return(conf)

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    props['type']       = 'service'
    props['name']       = 'spotify'
    props['short_name'] = 'SPO'
    props['controls']   = True
    props['button']     = "<div style='font-family: mediaicons;'>&#x0051;</div>"
    return(props)

#------------------------------------------------------------------------------#
#                  get metadata from spotify                                   #
#------------------------------------------------------------------------------#
def get_metadata():
    meta_data = {}
    try:
        current_track, success = talk_to_spotify('current_track')
        album = current_track['item']['album']
        meta_data['track']  = current_track['item']['name']
        meta_data['album']  = album['name']
        meta_data['artist'] = album['artists'][0]['name']
        meta_data['cover']  = album['images'][0]['url']
        return(meta_data)
    except:
        meta_data['track']  = ''
        meta_data['album']  = ''
        meta_data['artist'] = ''
        meta_data['cover']  = ''
        return(meta_data)

#------------------------------------------------------------------------------#
#                  get play status                                             #
#------------------------------------------------------------------------------#
def get_play_status():
    playing = False
    ret_val = False
    try:
        current_track, success = talk_to_spotify('current_track')
        playing = current_track['is_playing']
    except:
        playing = False
    if playing:
        ret_val = get_active()
    return(ret_val)

#------------------------------------------------------------------------------#
#                  get active status                                           #
#------------------------------------------------------------------------------#
def get_active():
    active = False
    try:
        devices, success = talk_to_spotify('devices')
        for device in devices['devices']:
            if hostname.upper() in device['name'].upper():
                if device['is_active']:
                    active = True
    except:
        active = False
    return(active)

#------------------------------------------------------------------------------#
#                  get device_id                                               #
#------------------------------------------------------------------------------#
def get_device_id():
    id = ''
    devices, success = talk_to_spotify('devices')
    try:
        for device in devices['devices']:
            print(device['name'])
            if hostname in device['name']:
                id = device['is_active']
                print('MY ID:', id)
                return(id)
    except:
        print("unable to get device ID")
        exit(1)
    if success == False:
        print("domething went wrong getting device ID")
        exit(1)

#------------------------------------------------------------------------------#
#                  make a call to spotify with retry                           #
#------------------------------------------------------------------------------#
def talk_to_spotify(item):
    success = False
    result = None
    try:
        if item == 'devices':
            result = spotifyObject.devices()
        elif item == 'current_track':
            result = spotifyObject.current_user_playing_track()
        elif item == 'next':
            result = spotifyObject.next_track(device_id=d_id)
        elif item == 'prev':
            result = spotifyObject.previous_track(device_id=d_id)
        elif item == 'play':
            result = spotifyObject.start_playback(device_id=d_id)
        elif item == 'pause':
            result = spotifyObject.pause_playback(device_id=d_id)
        success = True
    except:
        get_token()
        try:
            if item == 'devices':
                result = spotifyObject.devices()
            elif item == 'current_track':
                result = spotifyObject.current_user_playing_track()
            elif item == 'next':
                result = spotifyObject.next_track(device_id=d_id)
            elif item == 'prev':
                result = spotifyObject.previous_track(device_id=d_id)
            elif item == 'play':
                result = spotifyObject.start_playback(device_id=d_id)
            elif item == 'pause':
                result = spotifyObject.pause_playback(device_id=d_id)
            success = True
        except:
            print('unable to talk to spotify')
    return(result, success)

#------------------------------------------------------------------------------#
#          read cover image fom spotify connect web                            #
#------------------------------------------------------------------------------#
def read_cover_image(cover_uri):
    cover = 'http://localhost:4000/api/info/image_url/' + cover_uri
    webURL = urllib.request.urlopen(cover)
    data = webURL.read()
    return(data)

#------------------------------------------------------------------------------#
#         play next song                                                       #
#------------------------------------------------------------------------------#
def next():
    talk_to_spotify('next')

#------------------------------------------------------------------------------#
#         play previuous song                                                  #
#------------------------------------------------------------------------------#
def prev():
    talk_to_spotify('prev')

#------------------------------------------------------------------------------#
#         start playing                                                        #
#------------------------------------------------------------------------------#
def play():
    talk_to_spotify('play')

#------------------------------------------------------------------------------#
#         stop playing                                                         #
#------------------------------------------------------------------------------#
def stop():
    talk_to_spotify('pause')

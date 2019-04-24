#!/usr/bin/python

import re
import time
from mpd import MPDClient, MPDError, CommandError
import _thread
import pprint
stations = None
pos = 0
max = 0
current = 0
module_path = None
meta_data = {}
command_queue = []
play_status = False

#------------------------------------------------------------------------------#
#        init mpd                                                              #
#------------------------------------------------------------------------------#
def init(path, host="localhost", port=6600, playlist="radio", columns=200):
    global mpd_client
    global mpd_host
    global mpd_port
    global diplay_columns
    global stations
    global max
    global module_path
    global meta_data
    module_path = path
    mpd_host = host
    mpd_port = port
    diplay_columns = columns
    mpd_client = MPDClient()
    mpd_client.timeout = 20
    mpd_client.idletimeout = None
    mpd_client.connect(mpd_host, mpd_port)
    stations = mpd_client.playlistinfo()
    mpd_client.disconnect()
    max = len(stations)
    meta_data['track']  = ""
    meta_data['album']  = ""
    meta_data['artist'] = ""
    meta_data['cover']  = "/images/pause.png"
    queue_monitor()

#------------------------------------------------------------------------------#
#        connect to mpd                                                        #
#------------------------------------------------------------------------------#
def connect():
    try:
        mpd_client.disconnect()
    except:
        a=1
    try:
        mpd_client.connect(mpd_host, mpd_port)
    except:
        return(False)
    return(True)

#------------------------------------------------------------------------------#
#        disconnect to mpd                                                        #
#------------------------------------------------------------------------------#
def disconnect():
    try:
        mpd_client.disconnect()
    except:
        print('retrying to disconnect to mpd')
        time.sleep(0.5)
        try:
            mpd_client.disconnect()
        except:
            return(False)
    return(True)

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    props['type']       = 'service'
    props['name']       = 'radio'
    props['short_name'] = 'RAD'
    props['controls']   = True
    props['button']     = "&#xF2C2;"
    return(props)

#------------------------------------------------------------------------------#
#       get metadata from mpd                                                  #
#------------------------------------------------------------------------------#
def get_metadata():
    return(meta_data)

#------------------------------------------------------------------------------#
#      tune to a station                                                       #
#------------------------------------------------------------------------------#
def play():
    global command_queue
    command_queue.append('play')

#------------------------------------------------------------------------------#
#      stop mpd                                                                #
#------------------------------------------------------------------------------#
def stop():
    global command_queue
    command_queue.append('stop')

#------------------------------------------------------------------------------#
#                  get play status                                             #
#------------------------------------------------------------------------------#
def get_play_status():
    return(play_status)

#------------------------------------------------------------------------------#
#      next station                                                            #
#------------------------------------------------------------------------------#
def next():
    global command_queue
    command_queue.append('next')

#------------------------------------------------------------------------------#
#      previous station                                                        #
#------------------------------------------------------------------------------#
def prev():
    global command_queue
    command_queue.append('prev')

#------------------------------------------------------------------------------#
#           monitor changes and update display                                           #
#------------------------------------------------------------------------------#
def run_queue():
    print('starting mpd queue')
    name   = ''
    title  = ''
    artist = ''
    global pos
    global command_queue
    global meta_data
    global play_status
    global current
    time.sleep(1)
    loop_count = 0
    while True:
        loop_count = loop_count + 1
        time.sleep(0.1)
        while len(command_queue) > 0:
            for item in command_queue:
                if connect():
                    command_queue.pop()
                    if item == 'next':
                        if current == max:
                            mpd_client.play(0)
                        else:
                            mpd_client.next()
                    if item == 'prev':
                        if current > 0:
                            mpd_client.previous()
                    if item == 'stop':
                        mpd_client.stop()
                    if item == 'play':
                        mpd_client.play()
                    disconnect()
                    time.sleep(0.4)
        if loop_count == 10:
            loop_count = 0
            meta_data['track']  = ""
            meta_data['album']  = ""
            meta_data['artist'] = ""
            meta_data['cover']  = "/images/pause.png"
            if connect():
                status = mpd_client.status()
                #pprint.pprint(status)
                if 'songid' in status:
                    current = int(status['songid'])
                if status['state'] == 'play':
                    play_status = True
                else:
                    play_status = False
                info = mpd_client.currentsong()
                if 'name' in info.keys():
                    name = info["name"]
                    name = name[:diplay_columns]
                    name = name.strip()
                if 'title'in info.keys():
                    parts  = re.split("( \- )", info["title"], 2)
                    if len(parts) > 1:
                        artist=parts[0]
                        title=parts[2]
                    else:
                        artist = info["title"]
                if 'pos' in info.keys():
                    pos = int(info["pos"])
                artist=artist.replace(name, "")
                artist= artist[:diplay_columns]
                artist=artist.strip()
                title=title.replace(name, "")
                title=title[:diplay_columns]
                title=title.strip()
                cover = '/images/logos/' + str(pos) + '.png'
                meta_data['track']  = name
                meta_data['album']  = title
                meta_data['artist'] = artist
                meta_data['cover']  = '/images/logos/' + str(pos) + '.png'
                disconnect()

#------------------------------------------------------------------------------#
#           start thread for change monitor                                    #
#------------------------------------------------------------------------------#
def queue_monitor():
    try:
        _thread.start_new_thread( run_queue, () )
    except:
        print("Error: unable to start thread run_queue")

#init('./')
#queue_monitor()
#while True:
#    print('klong')
#    time.sleep(3)

#!/usr/bin/python3

import dbus
import pprint
import time
import pprint
import subprocess

SERVICE_NAME = "org.bluez"
ADAPTER_NAME = SERVICE_NAME + ".MediaPlayer1"
MANAGER_NAME = "org.freedesktop.DBus.ObjectManager"
adapter = None
player  = None

module_path = None
meta_data   = {}
play_status = False
connected   = False

#------------------------------------------------------------------------------#
#        init plugin                                                           #
#------------------------------------------------------------------------------#
def init(path, host="localhost"):
    global module_path
    global meta_data
    module_path = path
    meta_data['track']  = ""
    meta_data['album']  = ""
    meta_data['artist'] = ""
    meta_data['cover']  = "/images/black.png"

#------------------------------------------------------------------------------#
#        start plugin                                                          #
#------------------------------------------------------------------------------#
def module_start():
    print('STARTING')
    #return
    return_code = subprocess.call("/bin/systemctl restart bluetooth.service > /dev/null 2>&1", shell=True)
    return_code = subprocess.call("echo 'power on\nquit' | /usr/bin/bluetoothctl", shell=True)
    #return_code = subprocess.call("/bin/systemctl start bluetooth.service > /dev/null 2>&1", shell=True)

#------------------------------------------------------------------------------#
#        stop plugin                                                           #
#------------------------------------------------------------------------------#
def module_stop():
    print('STOPPING')
    #return_code = subprocess.call("/bin/systemctl stop bluetooth.service > /dev/null 2>&1", shell=True)
    return_code = subprocess.call("echo 'power off\nquit' | /usr/bin/bluetoothctl", shell=True)

#------------------------------------------------------------------------------#
#       init dbus interface                                                    #
#------------------------------------------------------------------------------#
def init_dbus_interface():
    global adapter
    global player
    global connected
    connected = True
    try:
        bus = dbus.SystemBus()
        service = bus.get_object(SERVICE_NAME, "/")
        manager = dbus.Interface(service, MANAGER_NAME)
        objects = manager.GetManagedObjects()
        for path, ifaces in objects.items():
            adapter = ifaces.get(ADAPTER_NAME)
            if adapter:
                #print(path)
                media = bus.get_object(SERVICE_NAME, path)
                break
        else:
            connected = False
            return
            raise Exception('no bluetooth adapter found')
        player = dbus.Interface(media, dbus_interface=ADAPTER_NAME)
    except:
        connected = False

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    props['type']       = 'service'
    props['name']       = 'bluetooth'
    props['short_name'] = 'BT '
    props['controls']   = True
    props['button']     = "&#xF282;"
    return(props)

#------------------------------------------------------------------------------#
#       get metadata from dbus                                                 #
#------------------------------------------------------------------------------#
def get_metadata():
    global meta_data
    init_dbus_interface()
    if connected:
        data = adapter.get('Track')
        if data.get('Title') != None:
            meta_data['track'] = data.get('Title')
        if data.get('Album') != None:
            meta_data['album'] = data.get('Album')
        if data.get('Artist') != None:
            meta_data['artist'] = data.get('Artist')

    else:
        print('no metadata')
        meta_data['track']  = ' '
        meta_data['album']  = ' '
        meta_data['artist'] = ' '
    return(meta_data)

#------------------------------------------------------------------------------#
#      start playback                                                          #
#------------------------------------------------------------------------------#
def play():
    init_dbus_interface()
    if connected:
        player.Play()

#------------------------------------------------------------------------------#
#      stop playback                                                           #
#------------------------------------------------------------------------------#
def stop():
    print('!!!!!!!!!!!!!! GOT STOP')
    init_dbus_interface()
    if connected:
        player.Stop()

#------------------------------------------------------------------------------#
#      next track                                                              #
#------------------------------------------------------------------------------#
def next():
    init_dbus_interface()
    if connected:
        player.Next()

#------------------------------------------------------------------------------#
#      previous track                                                          #
#------------------------------------------------------------------------------#
def prev():
    init_dbus_interface()
    if connected:
        player.Previous()
        player.Previous()

#------------------------------------------------------------------------------#
#                  get play status                                             #
#------------------------------------------------------------------------------#
def get_play_status():
    global play_status
    init_dbus_interface()
    if connected:
        status = adapter.get('Status')
        if status == 'playing':
            play_status = True
        else:
            play_status = False
    else:
        play_status = False
    return(play_status)

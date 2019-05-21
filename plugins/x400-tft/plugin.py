#!/usr/bin/python3.5

import pprint
import urllib
import requests
import time
import _thread
import os
import RPi.GPIO as GPIO
import alsaaudio
import re
from evdev import InputDevice, categorize, ecodes, list_devices
import subprocess
import smbus

bus             = smbus.SMBus(1)
i2c_address     = 0x05

ENCODER_1_LAST  = (0,1,1)

lirc_device     = None
mixer           = None
port            = None
module_path     = None
out_device      = None
flag            = False
remote_change   = False
display_enabled = True
speaker_enabled = True
hw_test         = False
active_output   = 'speaker'

volume          = 0
host            = ''
current_mode    = ''
services_string = ''
services        = []
command_queue   = []
modes           = []
conf            = {}

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def init(path, p = '8081', se='', test=False):
    global modes
    global conf
    global mixer
    global lirc_device
    global host
    global module_path
    global port
    global services_string
    global services
    global hw_test
    hw_test = test
    conf = read_config(path + '/plugin.conf')
    host = conf['MISC']['HOST']
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        if device.name == 'lircd-uinput':
            lirc_device = InputDevice(device.path)
    mixer = alsaaudio.Mixer(device=conf['MISC']['MIXER_DEVICE'], control=conf['MISC']['MIXER_CONTROL'])
    modes = se.split(',')
    module_path = path
    services_string = se
    services = services_string.split(',')
    port = p
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for item in conf['IN_PINS']:
        GPIO.setup(conf['IN_PINS'][item], GPIO.IN, pull_up_down=GPIO.PUD_UP)
    for item in conf['OUT_PINS']:
        GPIO.setup(conf['OUT_PINS'][item], GPIO.OUT)
        GPIO.output(conf['OUT_PINS'][item], 0)
    GPIO.add_event_detect(conf['IN_PINS']['ENCODER_1_BTN'], GPIO.FALLING, callback=handle_button, bouncetime=300)
    GPIO.add_event_detect(conf['IN_PINS']['ENCODER_1_PIN_A'], GPIO.RISING, callback=read_encoder)
    GPIO.add_event_detect(conf['IN_PINS']['ENCODER_1_PIN_B'], GPIO.RISING, callback=read_encoder)
    GPIO.add_event_detect(conf['IN_PINS']['I2C_INTERRUPT'], GPIO.RISING, callback=get_i2c_data)
    GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], display_enabled)
    GPIO.output(conf['OUT_PINS']['SPEAKER_ENABLE'], speaker_enabled)
    switch_output(active_output)
    ir_monitor()
    if not hw_test:
        time.sleep(2)
        change_monitor()
        x_windows()

#------------------------------------------------------------------------------#
#           read config file                                                   #
#------------------------------------------------------------------------------#
def read_config(config_file):
    section = ''
    if not os.path.isfile(config_file):
        print('ERROR config file', config_file, 'does not exist')
        exit(1)
    conf = {}
    with open(config_file) as f:
        content = f.readlines()
    for line in content:
        line = line.strip()
        if line.startswith("#"):
            continue
        if line.startswith("["):
            section = re.findall(r"^\[(.+)\]$", line)[0]
            conf[section] = {}
            continue
        if '=' in line:
            key,value = line.split('=',2)
            key   = key.strip()
            value = value.strip()
            if section == 'SWITCHES':
                switches = value.split(',')
                conf[section][key] = {}
                for item in switches:
                    parts = item.split(':')
                    conf[section][key][parts[0]] = int(parts[1])
            else:
                if re.match(r'^([\d]+)$', value) :
                    value = int(value)
                if re.match(r'^([\d]+)$', key) :
                    key = int(key)
                conf[section][key] = value
    return(conf)

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    con_trols = []
    tmp_control= {}
    tmp_control['name'] = 'volume'
    tmp_control['type'] = 'slider'
    con_trols.append(tmp_control)
    props['type']       = 'interface'
    props['name']       = 'x400-tft'
    props['controls']   = ['volume']
    props['con_trols']  = con_trols
    return(props)

#------------------------------------------------------------------------------#
#           change mode                                                        #
#------------------------------------------------------------------------------#
def change_mode(name, short_name):
    global current_mode
    current_mode = short_name
    set_switches(current_mode)

#------------------------------------------------------------------------------#
#           handle control input                                               #
#------------------------------------------------------------------------------#
def handle_control(control,value):
    global volume
    global active_output
    if control == 'volume':
        remote_change = True
        volume = value
    elif control == 'output':
        remote_change = True
        switch_output(value)
        active_output = value
    elif control == 'usb_key':
        press_usb_key(value)
    else:
        print(control,'not implemented')

#------------------------------------------------------------------------------#
#           send metadata to display                                           #
#------------------------------------------------------------------------------#
def display_metadata(track,album,artist):
    return

#------------------------------------------------------------------------------#
#           display play mode                                                  #
#------------------------------------------------------------------------------#
def playmode(play_mode):
    return

#------------------------------------------------------------------------------#
#           mute or unmute speakers                                            #
#------------------------------------------------------------------------------#
def switch_output(output):
    if output == 'speaker':
        print('switching to speakers')
        GPIO.output(conf['OUT_PINS']['SPEAKER_ENABLE'], True)
        GPIO.output(conf['OUT_PINS']['HEADPHONE_ENABLE'], False)
    elif output == 'headphone':
        print('switching to headphone')
        GPIO.output(conf['OUT_PINS']['SPEAKER_ENABLE'], False)
        GPIO.output(conf['OUT_PINS']['HEADPHONE_ENABLE'], True)
    elif output == 'mute':
        print('muting')
        GPIO.output(conf['OUT_PINS']['SPEAKER_ENABLE'], False)
        GPIO.output(conf['OUT_PINS']['HEADPHONE_ENABLE'], False)

#------------------------------------------------------------------------------#
#           perform get request                                                #
#------------------------------------------------------------------------------#
def performe_get_request(path):
    content = urllib.request.urlopen('http://' + host + ':' + str(port) + '/' + path).read()

#------------------------------------------------------------------------------#
#           perform post request                                               #
#------------------------------------------------------------------------------#
def performe_post_request(path, data):
    path = 'http://' + host + ':' + str(port) + '/' + path
    try:
        r = requests.post(url = path, data = data)
    except:
        print('unable to handle request')

#------------------------------------------------------------------------------#
#           handle button press                                                #
#------------------------------------------------------------------------------#
def handle_button(pin):
    time.sleep(0.1)
    if GPIO.input(pin) == False:
        if pin == conf['IN_PINS']['ENCODER_1_BTN']:
            toggle_back_light()

#------------------------------------------------------------------------------#
#           handle button press                                                #
#------------------------------------------------------------------------------#
def press_usb_key(key):
    if key == 'next':
        bus.write_byte(i2c_address, 1)
    elif key == 'prev':
        bus.write_byte(i2c_address, 2)
    elif key == 'play':
        bus.write_byte(i2c_address, 3)
    elif key == 'pause':
        bus.write_byte(i2c_address, 4)

#------------------------------------------------------------------------------#
#           get data if interrupt pin was triggered                            #
#------------------------------------------------------------------------------#
def get_i2c_data(pin):
    global volume
    code = bus.read_byte(i2c_address)
    #print('I2C: ', code)
    if code == 20:
        volume = volume + 1
        if volume > 100:
            volume = 100
    elif code == 21:
        volume = volume - 1
        if volume < 0:
            volume = 0
    elif code == 24:
        toggle_back_light()
    elif code == 23:
        command_queue.append('next')
        time.sleep(0.1)
    elif code == 22:
        command_queue.append('prev')
        time.sleep(0.1)
    elif code == 25:
        shift_mode()
        time.sleep(0.1)
    elif code == 26:
        command_queue.append('toggle')
        time.sleep(0.1)
    elif code == 1:
        GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], 1)
        switch_output(active_output)
    elif code == 2:
        GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], 0)
        display_enabled = False
        switch_output('mute')
        return_code = subprocess.call("/sbin/poweroff", shell=True)
    elif code == 3:
        return
        GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], 0)
        display_enabled = False
        switch_output('mute')
        return_code = subprocess.call("/sbin/poweroff", shell=True)

#------------------------------------------------------------------------------#
#           handle button press                                                #
#------------------------------------------------------------------------------#
def shift_mode():
    global current_mode
    count = 0
    found = 0
    for item in modes:
        if current_mode == modes[count]:
            found = count
        count = count + 1
    found = found + 1
    if found > len(modes)-1:
        found = 0
    current_mode = modes[found]
    data = {}
    data['mode'] = found
    performe_post_request('smode', data)
    set_switches(current_mode)

#------------------------------------------------------------------------------#
#           set GPIO's acording to mode                                        #
#------------------------------------------------------------------------------#
def set_switches(mode):
    global out_device
    for item in conf['SWITCHES']:
        if item == mode:
            for io in conf['SWITCHES'][item]:
                GPIO.output(conf['OUT_PINS'][io], conf['SWITCHES'][item][io])
                #print('setting',conf['OUT_PINS'][io],'to',conf['SWITCHES'][item][io])
            time.sleep(1)
            try:
                out_device = alsaaudio.PCM(alsaaudio.PCM_PLAYBACK, device='hw:1,0')
            except:
                print('failed to open audio device')
            return()
    for io in conf['SWITCHES']['default']:
        try:
            out_device.close()
        except:
            print('failed to close audio device')
        GPIO.output(conf['OUT_PINS'][io], conf['SWITCHES']['default'][io])
        #print('setting',conf['OUT_PINS'][io],'to',conf['SWITCHES'][item][io])

#------------------------------------------------------------------------------#
#           handle encoder change                                              #
#------------------------------------------------------------------------------#
def read_encoder(pin):
    global ENCODER_1_LAST
    global ENCODER_2_LAST
    global volume
    global command_queue
    item = None
    if pin == conf['IN_PINS']['ENCODER_1_PIN_A'] or pin == conf['IN_PINS']['ENCODER_1_PIN_B']:
        if pin == conf['IN_PINS']['ENCODER_1_PIN_A']:
            item = (pin, 1, GPIO.input(conf['IN_PINS']['ENCODER_1_PIN_B']))
        else:
            item = (pin, GPIO.input(conf['IN_PINS']['ENCODER_1_PIN_A']),1)
        if item == (conf['IN_PINS']['ENCODER_1_PIN_A'],1,1) and ENCODER_1_LAST[1] == 0:	# Is it in END position?
            volume = volume - 1
        elif item == (conf['IN_PINS']['ENCODER_1_PIN_B'],1,1) and ENCODER_1_LAST[2] == 0:	# Same but for ENC_B
            volume = volume + 1
        ENCODER_1_LAST = item
        if volume > 100:
            volume = 100
        if volume < 0:
            volume = 0
        if hw_test:
            print('volume:',volume)

#------------------------------------------------------------------------------#
#           monitor changes and update display                                           #
#------------------------------------------------------------------------------#
def run_change_monitor():
    print('starting change monitor')
    global command_queue
    global remote_change
    global volume
    translate = [0,1,3,8,16,22,27,32,36,38,41,44,46,48,50,52,53,55,57,58,59,61,
                62,63,64,65,66,67,68,69,70,70,71,72,73,74,75,75,76,76,77,78,78,
                79,79,79,80,81,82,82,83,83,83,84,84,85,85,86,86,87,87,87,88,88,
                89,89,90,90,90,91,91,91,92,92,92,93,93,93,94,94,94,94,95,95,95,
                96,96,96,97,97,97,97,98,98,98,98,99,99,99,99,100]
    old_volume = 0
    time.sleep(1)
    while True:
        time.sleep(0.1)
        while len(command_queue) > 0:
            for item in command_queue:
                command_queue.pop()
                performe_get_request(item)
        if old_volume != volume:
            mixer.setvolume(translate[volume])
            if remote_change == False:
                data = {}
                data['value'] = str(volume)
                data['control'] = 'volume'
                performe_post_request('setrcontrols', data)
            else:
                remote_change = False
            old_volume = volume

#------------------------------------------------------------------------------#
#           start thread for change monitor                                    #
#------------------------------------------------------------------------------#
def change_monitor():
    try:
        _thread.start_new_thread( run_change_monitor, () )
    except:
        print("Error: unable to start thread run_change_monitor")

#-----------------------------------------------------------------#
#             toggle backlight                                    #
#-----------------------------------------------------------------#
def toggle_back_light():
    global display_enabled
    if display_enabled:
        GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], 0)
        display_enabled = False
        bus.write_byte(i2c_address, 5)
    else:
        GPIO.output(conf['OUT_PINS']['DISPLAY_ENABLE'], 1)
        display_enabled = True
        bus.write_byte(i2c_address, 6)

#-----------------------------------------------------------------#
#             translate key code to string                        #
#-----------------------------------------------------------------#
def key_code_to_action(code):
    if hw_test:
        print('received IR code:', code)
        return()
    global volume
    if code == 103:
        volume = volume + 1
    if code == 108:
        volume = volume - 1
    if volume > 100:
        volume = 100
    if volume < 0:
        volume = 0
    if code == 105:
        command_queue.append('next')
        time.sleep(0.1)
    if code == 106:
        command_queue.append('prev')
        time.sleep(0.1)
    if code == 28:
        toggle_back_light()
    if code == 139:
        shift_mode()
        time.sleep(0.1)
    if code == 164:
        command_queue.append('toggle')
        time.sleep(0.1)

#-----------------------------------------------------------------#
#                 background thred to get keycode                 #
#-----------------------------------------------------------------#
def run_ir_monitor(lirc_device):
    repeat_cout = 0
    for event in lirc_device.read_loop():
        if event.type == ecodes.EV_KEY:
            if event.value == 1:
                key_code_to_action(event.code)
            elif event.value == 2:
                repeat_cout = repeat_cout +1
                if repeat_cout > 4:
                    key_code_to_action(event.code)
            elif event.value == 0:
                repeat_cout = 0

#------------------------------------------------------------------------------#
#           start thread for change monitor                                    #
#------------------------------------------------------------------------------#
def ir_monitor():
    try:
        _thread.start_new_thread( run_ir_monitor, (lirc_device, ) )
    except:
        print("Error: unable to start thread run_ir_monitor")

#------------------------------------------------------------------------------#
#           start x_window system                                              #
#------------------------------------------------------------------------------#
def run_x_windows():
    #return
    return_code = subprocess.call("/usr/bin/startx -- -nocursor > /dev/null 2>&1", shell=True)

#------------------------------------------------------------------------------#
#           start thread x_window system                                       #
#------------------------------------------------------------------------------#
def x_windows():
    try:
        _thread.start_new_thread( run_x_windows, () )
    except:
        print("Error: unable to start thread run_x_windows")

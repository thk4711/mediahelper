#!/usr/bin/python3.5

from http.server import BaseHTTPRequestHandler, HTTPServer
from cgi import parse_header, parse_multipart
from urllib.parse import parse_qs
import asyncio
import websockets
import json
import time
import alsaaudio
import threading
import _thread
import argparse
import select
import os
import pprint
import math
from random import randint

ser              = None
args             = None
desired_mode     = None
play_mode        = None
status_data      = ''
old_status_data  = {'track':'', 'album':'', 'artist':'', 'playmode':None}
controls         = {}
modules          = {}
last_play_modes  = {}
conf             = {}
status           = {}
mode_config      = {}
mode_order       = []
active_controls  = []
mode_trans       = {}
interfaces       = {}
interface_config = {}
diff             = {}
remote_cmd       = False
data_changed     = False
need_to_send     = False
web_ui_change    = False
active_output    = 'speaker'

#------------------------------------------------------------------------------#
#        read plugin modules                                                   #
#------------------------------------------------------------------------------#
def start_plugins():
    modules = {}
    interfaces = {}
    mode_config = {}
    interface_config = {}
    mode_order = []
    mode_trans = {}
    plugin_dirs = sorted(next(os.walk('plugins/active/'))[1])
    count = 0
    plugins = {}
    tmp = None
    for dir in plugin_dirs:
        count = count + 1
        tmp_name = 'lib' + str(count)
        plugin = {}
        code =  'import plugins.active.' + dir + '.plugin as ' + tmp_name
        print(code)
        code += ';tmp = ' + tmp_name + '.get_properties()'
        code += ';plugin[\'dir\'] = \'' + dir + '\''
        code += ';plugin[\'type\'] = tmp[\'type\']'
        code += ';plugin[\'tmp\'] = \'' + tmp_name + '\''
        code += ';plugins[tmp[\'name\']] = plugin'
        code += '\nif plugin[\'type\'] == \'service\':'
        code += '\n    mode_order.append(tmp[\'name\'])'
        exec(code)
    for plugin in plugins:
        if plugins[plugin]['type'] == 'service':
            print('adding service module: ' + plugin)
            code =  'modules[\'' +plugin + '\'] = ' + plugins[plugin]['tmp']
            code += ';tmp = ' + plugins[plugin]['tmp'] + '.get_properties()'
            code += ';mode_config[\'' + plugin + '\'] = tmp'
            code += ';mode_config[\'' + plugin + '\'][\'path\'] = \'plugins/active/' + plugins[plugin]['dir'] + '\''
            code += ';mode_trans[\'' + plugin + '\'] = tmp[\'short_name\']'
            exec(code)
        if plugins[plugin]['type'] == 'interface':
            print('adding interface module: ' + plugin)
            code =  'interfaces[\'' +plugin + '\'] = ' + plugins[plugin]['tmp']
            code += ';tmp = ' + plugins[plugin]['tmp'] + '.get_properties()'
            code += ';interface_config[\'' + plugin + '\'] = tmp'
            code += ';interface_config[\'' + plugin + '\'][\'path\'] = \'plugins/active/' + plugins[plugin]['dir'] + '\''
            exec(code)
    return(modules, interfaces, mode_config, interface_config, mode_order, mode_trans)

#------------------------------------------------------------------------------#
#     create html and javascript for buttons                                   #
#------------------------------------------------------------------------------#
def create_button_html():
    html = ''
    data = {}
    js   = '<script>\n'
    for part in mode_order:
        html += "<button id='" + part + "' class='btn btn-default'>\n"
        html += mode_config[part]['button'] + '\n'
        html += "</button>\n"
        js += "\t$('#" + part + "').on('click', function(){switch_mode('" + part + "');});\n"
    js += '</script>\n'
    data['html'] = html
    data['js']   = js
    return(json.dumps(data))

#------------------------------------------------------------------------------#
#     create html and javascript for sliders                                   #
#------------------------------------------------------------------------------#
def create_slider_html():
    data = {}
    html = ''
    volume_control_present = False
    other_control_present = False
    for item in active_controls:
        control = item['name']
        if item['type'] == 'switch':
            continue
        if control == 'volume':
            volume_control_present = True
        else:
            other_control_present = True
    if volume_control_present == False and other_control_present == False:
        data['html']=''
        data['controls']=[]
        return(json.dumps(data))
    if volume_control_present:
        html += "<table style='margin-top: 5px; margin-bottom: 0px;'>"
        html += "<tr><td width = '70'>volume<br>&nbsp</td><td><input id='volume' type='text' data-slider-min='0' data-slider-max='100' data-slider-step='1' data-slider-value='0'/><br>&nbsp</td></tr>\n"
        html += '</table>'
    if other_control_present:
        html += "<span id='sp_other' onclick='togle()'>more controls </span>"
        html += "<table id='other_controls'style='margin-top: 5px; margin-bottom: 0px; display:none;'>"
        sl_html = ''
        sw_html = ''
        for item in active_controls:
            control = item['name']
            if item['type'] == 'slider':
                if control != 'volume':
                    sl_html += "<tr><td width = '70'>" + control +"<br>&nbsp</td><td><input id='" + control + "' type='text' data-slider-min='0' data-slider-max='100' data-slider-step='1' data-slider-value='30'/><br>&nbsp</td></tr>\n"
            if item['type'] == 'switch':
                sw_html += "<tr><td width = '70' style='padding-top: 10px;'>" + control +"<br>&nbsp</td><td style='padding-left: 20px;'><label class='switch'><input id='" + control + "' type='checkbox' checked><span class='switch_slider round'</span></lable><br>&nbsp</td></tr>\n"
        html += sl_html + sw_html + '</table>'
    data['html']     = html
    data['controls'] = active_controls
    return(json.dumps(data))

#------------------------------------------------------------------------------#
#           add control to active controls if not present                      #
#------------------------------------------------------------------------------#
def add_to_active_controls(control,type):
    global active_controls
    new_item = {}
    new_item['name'] = control
    new_item['type'] = type
    not_present = True
    for item in active_controls:
        if item['name'] == control:
            not_present = False
    if not_present:
        active_controls.append(new_item)

#------------------------------------------------------------------------------#
#           do something at startup                                            #
#------------------------------------------------------------------------------#
def init():
    global modules, interfaces, mode_config, interface_config, mode_order, mode_trans
    global conf
    global last_play_modes
    global desired_mode
    global controls
    global args
    global status
    service_string=''
    read_status()
    t_conf = read_config('media_helper.conf')
    conf   = get_args(t_conf)
    modules, interfaces, mode_config, interface_config, mode_order, mode_trans = start_plugins()
    count = 0
    for mode in mode_order:
        modules[mode].init(mode_config[mode]['path'])
        last_play_modes[mode] = False
        if count == 0:
            service_string = service_string + mode_config[mode]['short_name']
        else:
            service_string = service_string + ',' + mode_config[mode]['short_name']
        count = count + 1
    for item in interfaces:
        print(interface_config[item]['path'])
        interfaces[item].init(interface_config[item]['path'],conf.port,service_string)
        for item in interface_config[item]['con_trols']:
            add_to_active_controls(item['name'],item['type'])
    if status['mode'] not in mode_order:
        status['mode'] = mode_config[mode_order[0]]['name']
        save_status()
    for item in active_controls:
        control = item['name']
        tmp_control = {}
        tmp_control['enabled'] = False
        tmp_control['type'] = item['type']
        tmp_control['value'] = status[control]
        tmp_control['old_value'] = status[control]
        if item['type'] == 'slider':
            if control == 'volume':
                tmp_control['mixer'] = alsaaudio.Mixer(device=conf.sound_card, control=conf.mixer_volume)
            if control == 'bass':
                tmp_control['mixer'] = alsaaudio.Mixer(device=conf.sound_card, control=conf.mixer_bass)
            if control == 'treble':
                tmp_control['mixer'] = alsaaudio.Mixer(device=conf.sound_card, control=conf.mixer_treble)
        controls[control] = tmp_control
        if control == 'volume':
            set_control(control,status['speakervol'])
        else:
            set_control(control,status[control])
    switch_to(status['mode'])

#------------------------------------------------------------------------------#
#           get json data using http in python3                                #
#------------------------------------------------------------------------------#
def get_args(t_conf):
    parser = argparse.ArgumentParser(description='media helper')
    parser.add_argument('-p', '--port', type=int, help='WEB server port', required=False, default=int(t_conf['port']))
    parser.add_argument('-w', '--ws_port', type=int, help='WEB socket port', required=False, default=int(t_conf['ws_port']))
    parser.add_argument('-s', '--ws_base', type=str, help='WEB socket port', required=False, default=t_conf['ws_base'])
    parser.add_argument('-v', '--mixer_volume', type=str, help='alsa volume mixer', required=False, default=t_conf['mixer_volume'])
    parser.add_argument('-b', '--mixer_bass', type=str, help='alsa bass mixer', required=False, default=t_conf['mixer_bass'])
    parser.add_argument('-t', '--mixer_treble', type=str, help='alsa treble mixer', required=False, default=t_conf['mixer_treble'])
    parser.add_argument('-c', '--sound_card', type=str, help='alsa sound card name', required=False, default=t_conf['sound_card'])
    args = parser.parse_args()
    print('using port ', args.port)
    print('using alsa card', args.sound_card)
    print('using alsa volume mixer', args.mixer_volume)
    print('using alsa bass mixer', args.mixer_bass)
    print('using alsa treble mixer', args.mixer_treble)
    return(args)
     
#------------------------------------------------------------------------------#
#    find desired_mode and play_mode                                           #
#------------------------------------------------------------------------------#
def find_play_mode():
    global play_mode
    for mode in mode_order:
        current_mode = modules[mode].get_play_status()
        if last_play_modes[mode] == False and current_mode == True:
            switch_to(mode)
            last_play_modes[mode] = True
            play_mode = True
            return()
        if last_play_modes[mode] == True and current_mode == False:
            last_play_modes[mode] = False
        if mode == desired_mode:
            play_mode = current_mode
        else:
            if current_mode == True:
                modules[mode].stop()

#------------------------------------------------------------------------------#
#           find out what is going on at the moment                            #
#------------------------------------------------------------------------------#
def get_status_info():
    global old_status_data
    find_play_mode()
    data={}
    data['play_mode'] = play_mode
    if data['play_mode'] != old_status_data['playmode']:
        old_status_data['playmode'] = data['play_mode']
        handle_interfaces('playmode', data['play_mode'])
    data['desired_mode'] = desired_mode
    for item in active_controls:
        control = item['name']
        data[control] = controls[control]['value']
    data['controls'] = mode_config[desired_mode]['controls']
    if play_mode == False:
        data['cover'] = '/images/pause.png'
        data['track'] = ' '
        data['album'] = ' '
        data['artist'] = ' '
    else:
        metadata=modules[desired_mode].get_metadata()
        data['track']  = metadata['track']
        data['album']  = metadata['album']
        data['artist'] = metadata['artist']
        data['cover']  = metadata['cover']

    changed = False
    for item in ['track', 'album', 'artist']:
        if data[item] != old_status_data[item]:
            changed = True
            old_status_data[item] = data[item]
    if changed:
        handle_interfaces('metadata', data['track'], data['album'], data['artist'], data['cover'])
    return(json.dumps(data))

#------------------------------------------------------------------------------#
#           send config to web page                                            #
#------------------------------------------------------------------------------#
def deliver_config():
    con = {}
    con['port']     = conf.port
    con['ws_base']  = conf.ws_base
    con['ws_port']  = conf.ws_port
    return(bytes(json.dumps(con), 'utf-8'))

#------------------------------------------------------------------------------#
#           read content of file in bin mode                                   #
#------------------------------------------------------------------------------#
def read_bin_file(file_name):
    if os.path.exists(file_name):
        with open(file_name, 'rb') as file:
            data = file.read()
        return(data)
    else:
        return(bytes('Not found', 'utf-8'))

#------------------------------------------------------------------------------#
#           watch control changes                                              #
#------------------------------------------------------------------------------#
def control_watch():
    global controls
    poll = select.poll()
    descriptors1 = None
    descriptors2 = None
    descriptors3 = None
    if 'volume' in controls:
        descriptors1 = controls['volume']['mixer'].polldescriptors()
        poll.register(descriptors1[0][0])
    if 'bass' in controls:
        descriptors2 = controls['bass']['mixer'].polldescriptors()
        poll.register(descriptors2[0][0])
    if 'treble' in controls:
        descriptors3 = controls['treble']['mixer'].polldescriptors()
        poll.register(descriptors3[0][0])
    print('starting monitor for alsa controls ...')
    time.sleep(2)
    while True:
        events = poll.poll()
        if 'volume' in controls:
            controls['volume']['mixer'].handleevents()
        if 'bass' in controls:
            controls['bass']['mixer'].handleevents()
        if 'treble' in controls:
            controls['treble']['mixer'].handleevents()
        for e in events:
            for item in active_controls:
                control = item['name']
                if item['type'] == 'slider':
                    alsa_val = controls[control]['mixer'].getvolume()
                    value = alsa_val[0]
                    if value != controls[control]['old_value']:
                        controls[control]['old_value'] = value
                        controls[control]['value'] = value
                        handle_interfaces(control, value)
                        status[control] = value
                        save_status()

#------------------------------------------------------------------------------#
#           set controls in alsa                                               #
#------------------------------------------------------------------------------#
def set_control(control, new_value):
    if controls[control]['type'] == 'slider':
        controls[control]['mixer'].setvolume(new_value)
    #else:
    #controls[control]['old_value'] = new_value
    controls[control]['value'] = new_value
    handle_interfaces(control, new_value)
    if control == 'volume':
        if active_output == 'speaker':
            control = 'speakervol'
        if active_output == 'headphone':
            control = 'headphonevol'
    status[control] = new_value
    save_status()

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
#           handle interfaces                                                  #
#------------------------------------------------------------------------------#
def handle_interfaces(action, data1=None, data2=None, data3=None, data4=None):
    print('handeling',action,data1,data2,data3)
    global remote_cmd
    global need_to_send
    global diff
    diff = {}
    print('remote', remote_cmd)
    if ( remote_cmd == True):
        remote_cmd = False
        #return()
    for item in interfaces:
        if action == 'change_mode':
            interfaces[item].change_mode(data1, data2)
            diff['desired_mode'] = data1
        elif action == 'metadata':
            interfaces[item].display_metadata(data1, data2, data3)
            diff['track']  = data1
            diff['album']  = data2
            diff['artist'] = data3
            diff['cover']  = data4
            diff['play_mode'] = play_mode
            diff['desired_mode'] = desired_mode

        elif action == 'playmode':
            interfaces[item].playmode(data1)
            diff['play_mode'] = data1
        else:
            interfaces[item].handle_control(action,data1)
            print('adding', action)
            diff[action] = data1
        need_to_send = True

#------------------------------------------------------------------------------#
#           swicht mode to ...                                                 #
#------------------------------------------------------------------------------#
def switch_to(mode):
    if mode == desired_mode:
        return
    global desired_mode
    if desired_mode == 'bluetooth':
        metadata=modules[desired_mode].module_stop()
    desired_mode = mode
    if desired_mode == 'bluetooth':
        metadata=modules[desired_mode].module_start()
    handle_interfaces('change_mode', mode_config[desired_mode]['name'], mode_config[desired_mode]['short_name'])
    status['mode'] = mode
    save_status()

#------------------------------------------------------------------------------#
#           save status as json                                                #
#------------------------------------------------------------------------------#
def save_status():
    with open('status.json', 'w') as outfile:
        json.dump(status, outfile)
    outfile.close()

#------------------------------------------------------------------------------#
#           read status from json                                              #
#------------------------------------------------------------------------------#
def read_status():
    global status
    if not os.path.isfile('status.json'):
        print('status file does not exist - creating it')
        status['mode'] = 'line1'
        status['volume']       = 0
        status['speakervol']   = 0
        status['headphonevol'] = 0
        status['bass']         = 0
        status['treble']       = 0
        status['loudness']     = 0
        save_status()
    with open('status.json') as infile:
        status = json.load(infile)
    infile.close()

#------------------------------------------------------------------------------#
#                       handle http post request                               #
#------------------------------------------------------------------------------#
def respond_to_post_request(path, post_data):
    global remote_cmd
    global data_changed
    global web_ui_change
    data_changed = True
    #print('>>>>POST->:', path )
    if path == '/mode':
        mode = post_data['mode'][0]
        switch_to(mode)
    if path == '/smode':
        mode_num = post_data['mode'][0]
        mode = mode_order[int(mode_num)]
        #print('smode', mode)
        #remote_cmd = True
        switch_to(mode)
    if path == '/setcontrols':
        control = post_data['control'][0]
        value   = post_data['value'][0]
        set_control(control,int(value))
        web_ui_change = True
    if path == '/setrcontrols':
        control = post_data['control'][0]
        value = post_data['value'][0]
        #print('setting', control, value)
        remote_cmd = True
        set_control(control,int(value))

#------------------------------------------------------------------------------#
#                       handle http get request                                #
#------------------------------------------------------------------------------#
def respond_to_get_request(path):
    global active_output
    if 'status' not in path:
        print('>>>>Req->:', path )
    else:
        print('.', end='', flush=True)
    if path == '/':
        path = '/index.html'
    if path in '/next/prev/play/pause/toggle':
        playback_control(path)
    elif path == '/statusinfo':
        if data_changed == True:
            data = bytes(get_status_info(), 'utf-8')
            return(data)
        else:
            b_data = bytes(status_data, 'utf-8')
            return(b_data)
    elif path == '/controls':
        c_data = {}
        c_data['controls'] = mode_config[desired_mode]['controls']
        return(bytes(json.dumps(c_data), 'utf-8'))
    elif path == '/getconfig':
        return(deliver_config())
    elif '/coverimage/' in path:
        cover_uri = path.replace('/coverimage/','')
        return(modules[desired_mode].read_cover_image(cover_uri))
    elif '/shairport_' in path:
        return(modules[desired_mode].read_cover_image(path))
    elif '/getbuttons' in path:
        bu_data = bytes(create_button_html(), 'utf-8')
        return(bu_data)
    elif '/getsliders' in path:
        bu_data = bytes(create_slider_html(), 'utf-8')
        return(bu_data)
    elif '/getmodes' in path:
        bu_data = bytes(json.dumps(mode_order), 'utf-8')
        return(bu_data)
    elif '/speaker' in path:
        active_output = 'speaker'
        if status['speakervol'] > status['headphonevol']:
            handle_interfaces('output','speaker')
            time.sleep(0.3)
            set_control('volume',status['speakervol'])
        else:
            set_control('volume',status['speakervol'])
            time.sleep(0.3)
            handle_interfaces('output','speaker')
    elif '/headphone' in path:
        active_output = 'headphone'
        if status['headphonevol'] > status['speakervol']:
            handle_interfaces('output','headphone')
            time.sleep(0.3)
            set_control('volume',status['headphonevol'])
        else:
            set_control('volume',status['headphonevol'])
            time.sleep(0.3)
            handle_interfaces('output','headphone')
    else:
        file_name = path.lstrip('/')
        return(read_bin_file(file_name))
    return(bytes('OK', 'utf-8'))

#------------------------------------------------------------------------------#
#           performe playback control actions                                  #
#------------------------------------------------------------------------------#
def playback_control(path):
    if path == '/next':
        modules[desired_mode].next()
        if desired_mode == 'usb':
            handle_interfaces('usb_key', 'next')
    elif path == '/prev':
        modules[desired_mode].prev()
        if desired_mode == 'usb':
            handle_interfaces('usb_key', 'prev')
    elif path == '/play':
        modules[desired_mode].play()
        if desired_mode == 'usb':
            handle_interfaces('usb_key', 'play')
    elif path == '/pause':
        modules[desired_mode].stop()
        if desired_mode == 'usb':
            handle_interfaces('usb_key', 'pause')
    elif path == '/toggle':
        if play_mode:
            modules[desired_mode].stop()
            if desired_mode == 'usb':
                handle_interfaces('usb_key', 'pause')
        else:
            modules[desired_mode].play()
            if desired_mode == 'usb':
                handle_interfaces('usb_key', 'play')

#------------------------------------------------------------------------------#
#           start thread for watching dummy control alsa device                #
#------------------------------------------------------------------------------#
def run_control_watch():
    try:
        _thread.start_new_thread( control_watch, () )
    except:
        print("Error: unable to start thread control watch")

#------------------------------------------------------------------------------#
#           http request handler                                               #
#------------------------------------------------------------------------------#
class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        path = self.path
        if '.css' in path:
            self.send_header('Content-type', 'text/css')
        elif '.js' in path:
            self.send_header('Content-type', 'text/javascript')
        else:
            self.send_header('Content-type', 'text/html')
        self.end_headers()
    # process get requests
    def do_GET(self):
        self._set_headers()
        path = self.path
        data = respond_to_get_request(path)
        self.wfile.write(data)
    # process post requests
    def do_POST(self):
        #content_length = int(self.headers['Content-Length'])
        #post_data = self.rfile.read(content_length)
        #path = self.path
        #self._set_headers()
        #post_data = post_data.decode("utf-8")
        #respond_to_post_request(path, post_data)
        ctype, pdict = parse_header(self.headers['content-type'])
        path = self.path
        if ctype == 'multipart/form-data':
            post_data = parse_multipart(self.rfile, pdict)
        elif ctype == 'application/x-www-form-urlencoded':
            length = int(self.headers['content-length'])
            post_decoded = self.rfile.read(length).decode('utf-8')
            post_data = parse_qs(post_decoded,
                                keep_blank_values=1,
                                encoding="utf-8",
                                errors="strict",
                                )
        else:
            post_data = {}
        respond_to_post_request(path, post_data)
        self._set_headers()
        self.wfile.write(bytes('ok', 'utf-8'))
    # send headder
    def do_HEAD(self):
        self._set_headers()
    def log_message(self, format, *args):
        return

#------------------------------------------------------------------------------#
#           run the http server in backgroung                                  #
#------------------------------------------------------------------------------#
def run_http():
    server_class=HTTPServer
    handler_class=Server
    port = int(conf.port)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print('starting http server at port',  port)
    http_thread = threading.Thread(target = httpd.serve_forever, args=())
    http_thread.daemon = True
    http_thread.start()

#------------------------------------------------------------------------------#
#           update status data in background                                   #
#------------------------------------------------------------------------------#
def status_update():
    global status_data
    global data_changed
    while True:
        status_data = get_status_info()
        data_changed = False
        time.sleep(1)

#------------------------------------------------------------------------------#
#          start status update                                                 #
#------------------------------------------------------------------------------#
def run_status_update():
    print('starting status updater')
    status_thread = threading.Thread(target = status_update(), args=())
    status_thread.start()

#------------------------------------------------------------------------------#
#           send updated data using websocket                                  #
#------------------------------------------------------------------------------#
async def ws_update(vu_socket, path):
    global need_to_send
    global web_ui_change
    while True:
        if need_to_send:
            #print(diff)
            if web_ui_change == False:
                #print('sending', json.dumps(diff))
                await vu_socket.send(json.dumps(diff))
            else:
                web_ui_change = False
                print("supressing")
            need_to_send = False
        await asyncio.sleep(0.1)

#------------------------------------------------------------------------------#
#           run the web socket server                                          #
#------------------------------------------------------------------------------#
def run_ws():
    port = int(conf.ws_port)
    print('starting websocket server at port', port )
    update_server = websockets.serve(ws_update, '*', port)
    asyncio.get_event_loop().run_until_complete(update_server)
    update_thread = threading.Thread(target = asyncio.get_event_loop().run_forever, args=())
    update_thread.daemon = True
    update_thread.start()

#------------------------------------------------------------------------------#
#           main program                                                       #
#------------------------------------------------------------------------------#
if __name__ == "__main__":
    init()
    run_ws()
    find_play_mode()
    run_http()
    run_control_watch()
    run_status_update()
    while True:
        time.sleep(2000)

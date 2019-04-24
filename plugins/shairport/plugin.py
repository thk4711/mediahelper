import json
import os
import subprocess
import psutil
module_path = None

#------------------------------------------------------------------------------#
#        start some processes in background                                    #
#------------------------------------------------------------------------------#
def init(path):
    global module_path
    module_path = path
    check_if_running()
    data = {'track':'','album':'','artist':'','filetype':'','md5':''}
    j_string = json.dumps(data)
    file = open('/tmp/shairport-metadata.json', 'w')
    file.write(j_string)
    file.close()
    pid=os.fork()
    if pid==0: # new process
        os.system("cat /tmp/shairport-sync-metadata | " + module_path + "/shairport-metadata.py")
        exit()
    else:
        with open(module_path + "/shairport-metadata.pid", "w") as pid_file:
            pid_file.write(str(pid))
        pid_file.close()

#------------------------------------------------------------------------------#
#        find out weather somthing is already running                          #
#------------------------------------------------------------------------------#
def check_if_running():
    old_pid = None
    if not os.path.exists(module_path + "/shairport-metadata.pid"):
        with open(module_path + "/shairport-metadata.pid", "w") as pid_file:
            pid_file.write(str(1234))
    with open(module_path + "/shairport-metadata.pid") as pid_file:
        old_pid = int(pid_file.readline())
    pid_file.close()
    for proc in psutil.process_iter():
        kill = False
        cmd_string = ' '.join(proc.cmdline())
        if 'shairport-metadata.py' in cmd_string:
            kill = True
        elif 'shairport-sync-metadata' in cmd_string:
            kill = True
        elif 'helper.py' in cmd_string and old_pid == proc.pid:
            kill = True
        if kill:
            proc.kill()

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    props['type']       = 'service'
    props['name']       = 'airplay'
    props['short_name'] = 'AIP'
    props['controls']   = True
    props['button']     = "&#xF3D2;"
    return(props)

#------------------------------------------------------------------------------#
#           interact with the api of spotify-connect-web                       #
#------------------------------------------------------------------------------#
def talk_to_dbus(action):
    method = ''
    ret = ''
    cmd = '/usr/bin/qdbus --system org.gnome.ShairportSync /org/gnome/ShairportSync '
    if action == 'next':
        method = 'org.gnome.ShairportSync.RemoteControl.Next'
    elif action == 'prev':
        method = 'org.gnome.ShairportSync.RemoteControl.Previous'
    elif action == 'play':
        method = 'org.gnome.ShairportSync.RemoteControl.Play'
    elif action == 'pause':
        method = 'org.gnome.ShairportSync.RemoteControl.Pause'
    ret_code = os.system(cmd + method)
    if (ret_code) != 0:
        ret = ('action ' + action + ' failed')
    else:
        ret = 'OK'
    return(ret)

#------------------------------------------------------------------------------#
#                           execute comand on OS level                         #
#------------------------------------------------------------------------------#
def execute_os_command(command):
    cmd_array = command.split()
    process = subprocess.Popen( cmd_array, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    out = out.decode('utf8')
    lines = out.split('\n')
    return(lines, err)

#------------------------------------------------------------------------------#
#          read cover image fom spotify connect web                            #
#------------------------------------------------------------------------------#
def read_cover_image(cover_uri):
    data = None
    image_path = '/tmp/shairport-image.'
    if '.jpg' in cover_uri:
        image_path = image_path + 'jpg'
    elif '.jpeg' in cover_uri:
        image_path = image_path + 'jpeg'
    elif '.png' in cover_uri:
        image_path = image_path + 'png'
    else:
        return(bytes('Not found', 'utf-8'))
    with open(image_path, 'rb') as file:
        data = file.read()
    return(data)

#------------------------------------------------------------------------------#
#                  get metadata from spotify-connect-web                       #
#------------------------------------------------------------------------------#
def get_metadata():
    meta_data = {}
    data = json.load(open('/tmp/shairport-metadata.json'))
    meta_data['track']  = data['track']
    meta_data['album']  = data['album']
    meta_data['artist'] = data['artist']
    meta_data['cover']  = '/tmp/shairport_' + data['md5'] + '.' + data['filetype']
    return(meta_data)

#------------------------------------------------------------------------------#
#                  get play status                                             #
#------------------------------------------------------------------------------#
def get_play_status():
    cmd = '/usr/bin/qdbus --system org.gnome.ShairportSync /org/gnome/ShairportSync org.gnome.ShairportSync.RemoteControl.PlayerState'
    lines,error = execute_os_command(cmd)
    if 'Playing' in lines[0]:
        return(True)
    else:
        return(False)

#------------------------------------------------------------------------------#
#                  get play status                                             #
#------------------------------------------------------------------------------#
def get_active():
    active_status = 'active'
    if active_status == 'active':
        return(True)
    else:
        return(False)

#------------------------------------------------------------------------------#
#         play next song                                                       #
#------------------------------------------------------------------------------#
def next():
    talk_to_dbus('next')

#------------------------------------------------------------------------------#
#         play previuous song                                                  #
#------------------------------------------------------------------------------#
def prev():
    talk_to_dbus('prev')

#------------------------------------------------------------------------------#
#         start playing                                                        #
#------------------------------------------------------------------------------#
def play():
    talk_to_dbus('play')

#------------------------------------------------------------------------------#
#         stop playing                                                         #
#------------------------------------------------------------------------------#
def stop():
    talk_to_dbus('pause')

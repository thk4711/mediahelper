#!/usr/bin/python3.5

import os
import sys
import pprint
import time
script_path = os.path.dirname(sys.argv[0])
sys.path.append(script_path)
import plugin as hw

#------------------------------------------------------------------------------#
#           switch i2s inputs                                                  #
#------------------------------------------------------------------------------#
def test_input():
    modes = []
    for mode in hw.conf['SWITCHES']:
        modes.append(mode)
    while True:
        os. system("clear")
        print('Please select mode')
        count = 1
        for mode in modes:
            print(count, ':', mode)
            count += 1
        print('q : Quit')
        key = input()
        if key == 'q':
            break
        select = int(key)
        if select < 1 or select > count-1:
            print('unknown mode')
        else:
            print('switching to', modes[select-1])
            hw.set_switches(modes[select-1])
        time.sleep(2)

#------------------------------------------------------------------------------#
#           test volume adjustment                                             #
#------------------------------------------------------------------------------#
def test_volume():
    while True:
        os. system("clear")
        print('Please select volume')
        print('1 : 0')
        print('2 : 10')
        print('3 : 30')
        print('4 : 50')
        print('q : Quit')
        key = input()
        if key == 'q':
            break
        elif key == '1':
            hw.mixer.setvolume(0)
        elif key == '2':
            hw.mixer.setvolume(10)
        elif key == '3':
            hw.mixer.setvolume(30)
        elif key == '4':
            hw.mixer.setvolume(50)
        else:
            print('wrong input')
        time.sleep(2)

#------------------------------------------------------------------------------#
#           switch audio outputs                                               #
#------------------------------------------------------------------------------#
def test_output():
    while True:
        os. system("clear")
        print('Please select output')
        print('1 : Speaker')
        print('2 : Headphone')
        print('3 : Mute')
        print('q : Quit')
        key = input()
        if key == 'q':
            break
        elif key == '1':
            hw.switch_output('speaker')
        elif key == '2':
            hw.switch_output('headphone')
        elif key == '3':
            hw.switch_output('mute')
        else:
            print('wrong input')
        time.sleep(2)

#------------------------------------------------------------------------------#
#           toggle screen                                                      #
#------------------------------------------------------------------------------#
def toggle_screen():
    while True:
        os. system("clear")
        print('Please select action')
        print('1 : toggle screen')
        print('q : Quit')
        key = input()
        if key == 'q':
            break
        elif key == '1':
            hw.toggle_back_light()
        else:
            print('wrong input')
        time.sleep(2)

#------------------------------------------------------------------------------#
#           toggle screen                                                      #
#------------------------------------------------------------------------------#
def test_usb_key():
    while True:
        os. system("clear")
        print('Please select key')
        print('1 : Next')
        print('2 : Previous')
        print('3 : Play')
        print('3 : Pause')
        print('q : Quit')
        key = input()
        if key == 'q':
            break
        elif key == '1':
            hw.press_usb_key('next')
        elif key == '2':
            hw.press_usb_key('prev')
        elif key == '3':
            hw.press_usb_key('play')
        elif key == '4':
            hw.press_usb_key('pause')
        else:
            print('wrong input')
        time.sleep(2)

hw.init(script_path,'8081','',True)
while True:
    os. system("clear")
    print('Please select test')
    print('1 : Test I2S input switch')
    print('2 : Test audio output')
    print('3 : Test volume adjustment')
    print('4 : Toggle screen')
    print('5 : Test USB key')
    print('q : Quit')
    key = input()
    if key == 'q':
        break
    elif key == '1':
        test_input()
    elif key == '2':
        test_output()
    elif key == '3':
        test_volume()
    elif key == '4':
        toggle_screen()
    elif key == '5':
        test_usb_key()
    else:
        print('wrong input')
    time.sleep(1)

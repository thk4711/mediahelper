#!/usr/bin/python
module_path = None

#------------------------------------------------------------------------------#
#        do nothing                                                            #
#------------------------------------------------------------------------------#
def init(path):
    global module_path
    module_path = path
    return()

#------------------------------------------------------------------------------#
#        report properies                                                      #
#------------------------------------------------------------------------------#
def get_properties():
    props = {}
    props['type']       = 'service'
    props['name']       = 'line1'
    props['short_name'] = 'LI1'
    props['controls']   = False
    props['button']     = """<svg width="50" height="50">
                                <path style="fill:rgb(255,255,255)" transform="scale(1.8,1.8)"
                                    d="m 13.656416,1.875675 c -1.808333,0 -3.503477,0.555024 -4.9375002,1.4375 l -4.09375,2.5625 H 0.25016577 v 2 h 4.65625003 0.28125 l 0.25,-0.15625 4.3437498,-2.6875 C 10.947393,4.314401 12.264749,3.875675 13.656416,3.875675 h 5.59375 v 1 1 6 1 1 h -2 v -9 h -2 v 9 h -1.59375 c -1.391667,0 -2.709023,-0.438726 -3.8750004,-1.15625 l -4.3437498,-2.6875 -0.1875,-0.1249996 V 8.875675 h -2 V 9.8756754 H 0.25016577 V 11.875675 H 4.6251658 l 4.09375,2.5625 c 1.4340232,0.882476 3.1291672,1.4375 4.9375002,1.4375 h 6.59375 1 v -1 -2 h 4 1 v -1 -1.9999996 h 2 V 7.875675 h -2 v -2 -1 h -1 -4 v -2 -1 h -1 z m 7.59375,5 h 3 v 4 h -3 z" overflow="visible" font-family="Bitstream Vera Sans"/>
                                <text <tspan x="40" y="43" style="fill:#ffffff;font-size:20px;font-family:roboto">1</tspan></text>
                            </svg>"""
    return(props)

#------------------------------------------------------------------------------#
#       report empty metadata                                                  #
#------------------------------------------------------------------------------#
def get_metadata():
    meta_data = {}
    meta_data['track']  = ''
    meta_data['album']  = ''
    meta_data['artist'] = ''
    meta_data['cover']  = '/images/dummy.jpg'
    return(meta_data)

#------------------------------------------------------------------------------#
#      tune to a station                                                       #
#------------------------------------------------------------------------------#
def play():
    get_metadata()

#------------------------------------------------------------------------------#
#      do nothing                                                              #
#------------------------------------------------------------------------------#
def stop():
    get_metadata()

#------------------------------------------------------------------------------#
#          always report false                                                 #
#------------------------------------------------------------------------------#
def get_play_status():
    return(False)

#------------------------------------------------------------------------------#
#      do nothing                                                              #
#------------------------------------------------------------------------------#
def next():
    get_metadata()

#------------------------------------------------------------------------------#
#      do nothing                                                              #
#------------------------------------------------------------------------------#
def prev():
    get_metadata()

import json
import sys
import numpy as np
import cv2
from os import path

from optparse import OptionParser
parser = OptionParser()
parser.add_option("-f", "--file", dest="filename",
                  help="read FILE as video source. The basename will be used as the json-metadata base name. global paths should be used", metavar="FILE")
parser.add_option("-m", "--mutant", dest="mutant",
                  help="name of MUTANT shown in video", metavar="MUTANT")
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")
(options, args) = parser.parse_args()

vpath = ''
vbasename = ''
vextension = ''
vmutant = ''

class VideoMeta:
    def __init__(self):
        self.mutant = ''
        self.directory = '.'
        self.filename = ''
        self.backing_seq = [] #list of tuples
        self.foi = [] #list of frameDetail objects

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


class FrameDetail:
    def __init__(self):
        self.frame_num = 0
        self.head_pos = (0,0)
        self.tail_pos = (0,0)
        self.dorsal_curve = [] # x0, y0, x1, y1, ...
        self.ventral_curve = []

def write_video_JSON(obj, filename):
    json_file = open(filename, 'w')
    json_file.write(obj.to_JSON())

def read_video_JSON(filename):
    json_file = open(filename, 'r')

    obj = json.load(json_file)
    print obj
    meta = VideoMeta()
    meta.mutant = obj['mutant']
    meta.directory = obj['directory']
    meta.filename = obj['filename']
    meta.backing_seq = obj['backing_seq']
    meta.foi = obj['foi']
    return meta

def nothing(x):
    pass

class Error(Exception):
    pass
class ErrorMSG(Error):
    def __init__(self, msg):
        self.msg = msg
class FileError(Error):
    def __init__(self, msg, f):
        self.msg = msg
        self.f = f

class UI:
    maxFrames = 0
    window_name = 'Contours. Elegans tracker'
    switch_loop = 'Loop seg'
    switch_play = 'Play'
    frame = 0;
    tb_frame = 0;
    loop_seg = 0;
    play = 0;
    cap = None

    def __init__(self, cap):
        cv2.namedWindow(self.window_name)
        UI.maxFrames = int(cap.get(7))

        #trackbars
        def updateTrackbar(x):
            cap.set(1,x)
            UI.frame = x
        cv2.createTrackbar('Seek Frame', UI.window_name, 0, UI.maxFrames-1, updateTrackbar)
        #switches
        cv2.createTrackbar(UI.switch_loop, UI.window_name, 0, 1, nothing)
        cv2.createTrackbar(UI.switch_play, UI.window_name, 0, 1, nothing)
        UI.cap = cap

    def update(self, cap):
        UI.play     = cv2.getTrackbarPos('Play', 'Contours. Elegans tracker')
        UI.tbFrame  = cv2.getTrackbarPos('Seek Frame', 'Contours. Elegans tracker')
        UI.loop_seg = cv2.getTrackbarPos('Loop seg', 'Contours. Elegans tracker')

        UI.frame = int(UI.cap.get(1))
        if UI.frame > UI.maxFrames-3:
            UI.frame = 0
            tbFrame = 0
        if UI.play == 0:
            UI.frame -= 1
            UI.cap.set(1, UI.frame)
        tbFrame = UI.frame
        cv2.setTrackbarPos('Seek Frame', 'Contours. Elegans tracker', UI.frame)


def main():
    vid_meta = VideoMeta()

    if options.filename is None:
        vpath = './'
        vbasename = 'default'
        vextension = '.avi'
    else:
        vpath = path.expandvars(path.expanduser(options.filename))
        if not path.isabs(vpath):
            raise FileError("Bad non-absolute path: ", vpath)
        vpath = path.split(options.filename)[0]
        vbasename = path.split(options.filename)[1][0:-4]
        vextension = path.split(options.filename)[1][-4:]
    if options.mutant is None:
        raise ErrorMSG('no mutant specified, use the --mutant flag')
    else:
        vmutant = options.mutant

    vid_meta.directory = vpath
    vid_meta.filename = vbasename + vextension
    vid_meta.mutant = vmutant

    print vid_meta.to_JSON()

    cap = cv2.VideoCapture(vpath + '/' + vbasename + vextension)
    if not cap.isOpened():
        raise FileError("Cannot open ", (vpath + '/' + vbasename + vextension))

    ui = UI(cap);

    while(cap.isOpened()):
        ret, frame = cap.read()

        ui.update(cap)
        cv2.imshow('Contours. Elegans tracker', frame)

        c = cv2.waitKey(1)
        if c & 0xFF == ord('q'):
            break
        if c & 0xFF == ord(' '):
            ui.play = not ui.play
            cv2.setTrackbarPos('Play', 'Contours. Elegans tracker', ui.play)
        if c == 2424832:
            cap.set(1, ui.frame-1)
        if c == 2555904:
            cap.set(1, ui.frame+1)
    cap.release()
    cv2.destroyAllWindows()

    write_video_JSON(vid_meta, vbasename + '.json')
    read_video_JSON(vbasename + '.json')

if __name__ == "__main__":
    try:
        main()
    except ErrorMSG as e:
        print e.msg
    except FileError as e:
        print e.msg + e.f



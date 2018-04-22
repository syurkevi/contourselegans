import sys
import numpy as np
from sets import Set
import cv2
from os import path
import math
import matplotlib.pyplot as plt
from ContourDataObjs import  UIState, VideoMeta, FrameDetail, UI
import json_tricks as json
from UtilityFunctions import *
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--file", dest="filename",
                  help="read FILE as video source. The basename will be used as the json-metadata base name if one is not provided. global paths should be used", metavar="FILE")
parser.add_option("-j", "--json", dest="json_filename",
                  help="read FILE as json metadata source. file assumed to be in same directory as video. (a 'sidecar' file)", metavar="FILE")
parser.add_option("-m", "--mutant", dest="mutant",
                  help="name of MUTANT shown in video", metavar="MUTANT")
parser.add_option("-q", "--quiet",
                  action="store_false", dest="verbose", default=True,
                  help="don't print status messages to stdout")
parser.add_option("-n", "--nojson",
                  action="store_false", dest="load_json", default=True,
                  help="don't load existing json file at startup")
parser.add_option("-t", "--tutorial",
                  action="store_true", dest="tutorial", default=False,
                  help="output tutorial text describing user interface")


(options, args) = parser.parse_args()

vpath = ''
vbasename = ''
vjson_filename = ''
vextension = ''
vmutant = ''

#todo: metrics:
#D/V length
#local curavture at equally spaced points H->T
#average d/v curvature

#todo:
#CSV outputs


def write_video_JSON(obj, filename):
    json_file = open(filename, 'w')
    #json_file.write(obj.to_JSON())
    json.dump(obj, json_file, sort_keys=True, indent=4)

def read_video_JSON(filename):
    json_file = open(filename, 'r')
    print "loading json " + filename
    return json.load(json_file, cls_lookup_map=globals())

def handleRecalcInput(c, fk, vmeta, frame):
#recalculate hack
    if c & 0xFF == ord('r'):
        print('recalculating')
        if fk in vmeta.foi:
            vmeta.foi[fk].metrics_calc = False
        else:
            print('adding to foi')
            frame_data = FrameDetail(UI.frame, frame)
            vmeta.foi[fk] = frame_data

def main():
    vid_meta = VideoMeta()
    if options.tutorial:
        print('''  Contours.Elegans -- Nematode Analysis Program\n
                UI tutorial:
                This program allows the "slicing" of video into segments of backwards locomotion.
                The segments provide contour analysis for the dorsal and ventral segments of a nematode.
                Sveral metrics are measured:
                \t- Average Curvature
                \t- Maximum/Minimum Curvature
                \t- Local Curvature
                \n The key-based UI is as follows:
                \t --> \ <-- Left/Right arrows jump between next/previous consecutive frames
                \t Space - toggle video playback
                \t   M   - adds a beginning or endpoint for a video-slice of interest
                \t   C   - calculates metrics and saves current frame of interest
                \t   L   - enables looping of video-slices
                \t   D   - next left-click will choose the dorsal curve
                \t   V   - next left-click will choose the ventral curve
                \t   H   - next left-click will place the location of the head
                \t   T   - next left-click will place the location of the tail
                \t   S   - calcuateds raw contours before selection and analysis
                \t   P   - toggle plot of of video slice
                ''')

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
    if options.json_filename is None:
        vjson_filename = vbasename
    else:
        vjson_filename = path.split(options.json_filename)[1][0:-5]

    if options.mutant is None:
        raise ErrorMSG('no mutant specified, use the --mutant flag')
    else:
        vmutant = options.mutant

    vid_meta.directory = vpath
    vid_meta.filename = vbasename + vextension
    vid_meta.json_filename = vjson_filename
    vid_meta.mutant = vmutant

    if options.load_json:
        try:
            vid_meta = read_video_JSON(vpath + '/' + vjson_filename + '.json')
        except Exception as e:
            print "Could not read existing JSON file: "  + vpath + '/' + vjson_filename + '.json'
            print e
        else:
            print vid_meta.to_JSON()

    cap = cv2.VideoCapture(vpath + '/' + vbasename + vextension)
    if not cap.isOpened():
        raise FileError("Cannot open ", (vpath + '/' + vbasename + vextension))

    ui = UI(cap, vid_meta);

    def mouseHandler(event, x, y, flags, param):
        ui.mouseInput(event, x, y, flags, param)

    while(cap.isOpened()):
        ret, frame = cap.read()
        raw_frame = frame.copy()

        ui.update(cap, vid_meta)
        cn = ui.predictActiveSeg(frame, vid_meta)

        #update calculations
        if ui.frame_key() in vid_meta.foi:
            if(vid_meta.foi[ui.frame_key()].head_pos != (0,0) and
                vid_meta.foi[ui.frame_key()].tail_pos != (0,0) and
                vid_meta.foi[ui.frame_key()].ventral_curve     and
                vid_meta.foi[ui.frame_key()].dorsal_curve      and
                not vid_meta.foi[ui.frame_key()].metrics_calc):
                #set curve lengths
                ##ventral
                cnt = np.asarray(vid_meta.foi[ui.frame_key()].ventral_curve)

                cnt = cnt[::2, :] #every second point in contour

                vid_meta.foi[ui.frame_key()].ventral_length = contour_length(cnt);
                av_curvature, curvatures = local_curvature(cnt);
                vid_meta.foi[ui.frame_key()].ventral_curvatures = curvatures
                vid_meta.foi[ui.frame_key()].average_ventral_curvature = av_curvature

                ##dorsal
                cnt = np.asarray(vid_meta.foi[ui.frame_key()].dorsal_curve)

                cnt = cnt[::2, :] #every second point in contour

                vid_meta.foi[ui.frame_key()].dorsal_length = contour_length(cnt);
                av_curvature, curvatures = local_curvature(cnt);
                vid_meta.foi[ui.frame_key()].dorsal_curvatures = curvatures
                vid_meta.foi[ui.frame_key()].average_dorsal_curvature = av_curvature
                #done calculating
                vid_meta.foi[ui.frame_key()].metrics_calc = True

        #draw contours curve
        dispframe = frame.copy()
        if ui.frame_key() in UI.raw_contours_ref:
            for cn in range(len(UI.raw_contours_ref[ui.frame_key()])):
                cnt = UI.raw_contours_ref[ui.frame_key()][cn]
                dispframe = cv2.drawContours(dispframe, [cnt], 0, (0, 155, (30 * cn) % 255), 3)

        dispframe = vid_meta.drawVentral(dispframe, ui.frame_key())
        dispframe = vid_meta.drawDorsal(dispframe, ui.frame_key())

        #draw head tail
        if ui.frame_key() in vid_meta.foi:
            cv2.circle(dispframe, tuple(vid_meta.foi[ui.frame_key()].head_pos), 5, (200, 100, 0),3)
            cv2.circle(dispframe, tuple(vid_meta.foi[ui.frame_key()].tail_pos), 3, (100, 50, 0),3)

        if frame.shape[1] > ui.maxWidth:
            ui.scaleFactor = float(ui.maxWidth) / float(frame.shape[0])
            scaled_frame = cv2.resize(dispframe, (0,0), fx=ui.scaleFactor, fy=ui.scaleFactor)

        cv2.imshow('Contours. Elegans tracker', scaled_frame)

        c = cv2.waitKeyEx(1)
        if c & 0xFF == ord('q') or c & 0xFF == 27:
            break

        ui.keyInput(c, frame)
        handleRecalcInput(c, ui.frame_key(), vid_meta, frame)
        cv2.setMouseCallback('Contours. Elegans tracker', mouseHandler)
        ui.displayPlot(vid_meta)
        base_path = vpath +  "/"
        ui.frameDump(base_path, vid_meta, raw_frame, dispframe)

    cap.release()
    cv2.destroyAllWindows()

    write_video_JSON(vid_meta, vpath +  "/" + vid_meta.json_filename + '.json')

if __name__ == "__main__":
    try:
        main()
    except ErrorMSG as e:
        print e.msg
    except FileError as e:
        print e.msg + e.f



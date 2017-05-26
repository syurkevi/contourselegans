import json_tricks.np as json
import sys
import numpy as np
from sets import Set
import cv2
from os import path
import math
import matplotlib.pyplot as plt
from UtilityFunctions import *

class UIState(object):
    NONE = 0
    PLACE_HEAD = 1
    PLACE_TAIL = 2
    CHOOSE_DORSAL = 3
    CHOOSE_VENTRAL = 4
    SPLIT_CURVES = 5


class VideoMeta(object):
    def __init__(self):
        self.mutant = ''
        self.directory = '.'
        self.filename = ''
        self.json_filename = ''
        self.backing_seq = [] #list of tuples
        self.foi = {} #list of frameDetail objects

    def to_JSON(self):
        return json.dumps(self, 
                         sort_keys=True, indent=4)

    def drawDorsal(self, image, frame_number, scale=1.0):
        if frame_number in self.foi:
            cnt = np.asarray(self.foi[frame_number].dorsal_curve)
            self.drawContour(image, cnt, (0, 0, 255), scale)
        return image

    def drawVentral(self, image, frame_number, scale=1.0):
        if frame_number in self.foi:
            cnt = np.asarray(self.foi[frame_number].ventral_curve)
            self.drawContour(image, cnt, (0, 255, 0), scale)
        return image

    def drawContour(self, image, contour, color, scale):
        for i in range(len(contour)-2):
            cv2.line(image, (contour[i][0],contour[i][1]), (contour[i+1][0], contour[i+1][1]), color, 3)
        return image

class FrameDetail(object):
    def __init__(self, fnum, frame):
        self.human_modified = False
        self.frame_num = fnum
        self.head_pos = (0,0)
        self.tail_pos = (0,0)
        self.dorsal_curve  = [] # x0, y0, x1, y1, ...
        self.ventral_curve = []
        self.dorsal_length  = 0
        self.ventral_length = 0
        self.dorsal_curvatures  = []
        self.ventral_curvatures = []
        self.average_dorsal_curvature  = 0
        self.average_ventral_curvature = 0
        self.metrics_calc = False
        self.calculate(frame)

    def calculate(self, frame):
        gframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gframe = cv2.GaussianBlur(gframe, (5,5), 0)
        gframe = cv2.bilateralFilter(gframe,9,75,75)
        frame = gframe
        ret, thresh = cv2.threshold(gframe, 127, 255, 0)
        #ret, thresh = cv2.threshold(gframe, 50, 255, 0)
        image, contours, hierarchy = cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
        UI.raw_contours_ref[str(UI.frame)] = contours
        print "calculating"

class UI(object):
    mouse_state = UIState.NONE
    maxFrames = 0
    window_name = 'Contours. Elegans tracker'
    switch_loop = 'Loop seg'
    switch_play = 'Play'
    show_plot = False
    frame = 0;
    tb_frame = 0;
    loop_seg = 0;
    play = 0;
    cap_ref = None
    contour_ref = None
    vid_metadata_ref = None
    raw_contours_ref = {}
    active_seq = (0, 0)
    tmpMarker = Set([])
    scaleFactor = 0.6
    maxWidth = 600

    def __init__(self, cap, vmeta):
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
        UI.cap_ref = cap
        UI.vid_metadata_ref = vmeta
    def frame_key(self):
        return str(UI.frame)

    def update(self, cap, vidmeta):
        UI.play     = cv2.getTrackbarPos('Play', 'Contours. Elegans tracker')
        UI.tbFrame  = cv2.getTrackbarPos('Seek Frame', 'Contours. Elegans tracker')
        UI.loop_seg = cv2.getTrackbarPos('Loop seg', 'Contours. Elegans tracker')

        UI.frame = int(UI.cap_ref.get(1))
        if UI.frame > UI.maxFrames-3:
            UI.frame = 0
            tbFrame = 0
        if UI.play == 0:
            UI.frame -= 1
            UI.cap_ref.set(1, UI.frame)

        UI.active_seq = findSeg(UI.frame, vidmeta.backing_seq)
        if not UI.active_seq:
            UI.active_seq = (0, cap.get(7))
        if UI.loop_seg:
            if UI.frame >= UI.active_seq[1]-1:
                UI.frame = UI.active_seq[0]
                cap.set(1, UI.frame)

        tbFrame = UI.frame
        cv2.setTrackbarPos('Seek Frame', 'Contours. Elegans tracker', UI.frame)

        if(len(UI.tmpMarker)>1):
            seq_tup = (0,0)
            seq_tup = (UI.tmpMarker.pop(),0)
            e = UI.tmpMarker.pop();
            if e < seq_tup[0]:
                seq_tup = (e, seq_tup[0])
            else:
                seq_tup = (seq_tup[0], e)
            UI.tmpMarker.clear()
            vidmeta.backing_seq.append(seq_tup)

    def predictActiveSeg(self, frame, vidmeta):
        prev_frame_key = str(UI.frame-1)
        if self.frame_key() in vidmeta.foi and prev_frame_key in vidmeta.foi:
            if vidmeta.foi[self.frame_key()].head_pos == (0,0):
                gframe = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gframe = cv2.GaussianBlur(gframe, (5,5), 0)
                gframe = cv2.bilateralFilter(gframe,9,75,75)

                corners = cv2.goodFeaturesToTrack(gframe, 10, 0.01, 20)
                corners = np.int0(corners)
                corners = corners.tolist()
                nhead = closest_point_idx(vidmeta.foi[prev_frame_key].head_pos, corners)
                ntail = closest_point_idx(vidmeta.foi[prev_frame_key].tail_pos, corners)
                vidmeta.foi[self.frame_key()].head_pos = tuple(corners[nhead][0])
                vidmeta.foi[self.frame_key()].tail_pos = tuple(corners[ntail][0])


    def keyInput(self, c, frame):
        #print c
        if c & 0xFF == ord(' '):
            UI.play = not UI.play
            cv2.setTrackbarPos('Play', 'Contours. Elegans tracker', UI.play)
        if c == 2424832:
            UI.cap_ref.set(1, UI.frame-1)
        if c == 2555904:
            UI.cap_ref.set(1, UI.frame+1)
        if c == ord('m'):
            UI.tmpMarker.add(UI.frame)
        if c == ord('c'):
            frame_data = FrameDetail(UI.frame, frame)
            UI.vid_metadata_ref.foi[str(UI.frame)] = frame_data
        if c == ord('l'):
            UI.loop_seg = not UI.loop_seg
            cv2.setTrackbarPos('Loop seg', 'Contours. Elegans tracker', UI.loop_seg)
        if c == ord('d'):
            UI.mouse_state = UIState.CHOOSE_DORSAL
        if c == ord('v'):
            UI.mouse_state = UIState.CHOOSE_VENTRAL
        if c == ord('h'):
            UI.mouse_state = UIState.PLACE_HEAD
        if c == ord('t'):
            UI.mouse_state = UIState.PLACE_TAIL
        if c == ord('p'):
            UI.show_plot = True
        if c == ord('s'):
            if self.frame_key() in UI.raw_contours_ref:
#MAKE THIS A FUNCTION. WTF DOES IT DO?
#split nearest contour
                contours = UI.raw_contours_ref[self.frame_key()]
                ncont = nearest_contour(UI.vid_metadata_ref.foi[self.frame_key()].head_pos, contours)
                epsilon = 0.05*cv2.arcLength(ncont,True)
                #approx_contour = cv2.approxPolyDP(ncont, epsilon, True)
                h_idx = closest_point_idx(UI.vid_metadata_ref.foi[self.frame_key()].head_pos, ncont)
                t_idx = closest_point_idx(UI.vid_metadata_ref.foi[self.frame_key()].tail_pos, ncont)
                if(h_idx < t_idx):
                    cnt_1 = ncont[h_idx : t_idx - 1]
                    cnt_2 = np.concatenate((ncont[t_idx :] , ncont[: h_idx]))
                else:
                    cnt_1 = ncont[t_idx : h_idx -1]
                    cnt_2 = np.concatenate((ncont[h_idx :] , ncont[: t_idx]))
                UI.raw_contours_ref[self.frame_key()][:]=[]
                UI.raw_contours_ref[self.frame_key()].append(cnt_1)
                UI.raw_contours_ref[self.frame_key()].append(cnt_2)

    def mouseInput(self, event, x, y, flags, param):
        x = int(x/self.scaleFactor)
        y = int(y/self.scaleFactor)
        if event == cv2.EVENT_LBUTTONUP:
            if UI.mouse_state == UIState.CHOOSE_DORSAL:
                if self.frame_key() in UI.raw_contours_ref:
                    contours = UI.raw_contours_ref[self.frame_key()]
                    ncont = nearest_contour((x,y), contours)
                    UI.vid_metadata_ref.foi[self.frame_key()].dorsal_curve = cv_cont_to_jlist(ncont)
                    print "chose dorsal"
            if UI.mouse_state == UIState.CHOOSE_VENTRAL:
                if self.frame_key() in UI.raw_contours_ref:
                    contours = UI.raw_contours_ref[self.frame_key()]
                    ncont = nearest_contour((x,y), contours)
                    UI.vid_metadata_ref.foi[self.frame_key()].ventral_curve = cv_cont_to_jlist(ncont)
                    print "chose ventral"
            if UI.mouse_state == UIState.PLACE_HEAD:
                if self.frame_key() in UI.vid_metadata_ref.foi:
                    UI.vid_metadata_ref.foi[self.frame_key()].head_pos = (x,y)
                    print "Placing head at: " + str((x,y))
                UI.mouse_state = UIState.NONE
            if UI.mouse_state == UIState.PLACE_TAIL:
                if self.frame_key() in UI.vid_metadata_ref.foi:
                    UI.vid_metadata_ref.foi[self.frame_key()].tail_pos = (x,y)
                    print "Placing tail at: " + str((x,y))
                UI.mouse_state = UIState.NONE

    def displayPlot(self,  vmeta):
        if UI.show_plot:
            av_dorsal_cv  = []
            av_ventral_cv = []

            dorsal_len  = []
            ventral_len = []
            for i in range(int(UI.active_seq[0]), int(UI.active_seq[1])):
                i = str(i)
                if(i in vmeta.foi and vmeta.foi[i].dorsal_length != 0):
                    av_dorsal_cv.append(vmeta.foi[i].average_dorsal_curvature)
                    av_ventral_cv.append(vmeta.foi[i].average_ventral_curvature)
                    dorsal_len.append(vmeta.foi[i].dorsal_length)
                    ventral_len.append(vmeta.foi[i].ventral_length)
                else:
                    av_dorsal_cv.append(0)
                    av_ventral_cv.append(0)
                    dorsal_len.append(0)
                    ventral_len.append(0)

            dlocal_curvatures  = []
            vlocal_curvatures = []
            if(self.frame_key() in vmeta.foi and vmeta.foi[self.frame_key()].dorsal_length != 0):
                dlocal_curvatures = vmeta.foi[self.frame_key()].dorsal_curvatures
                vlocal_curvatures = vmeta.foi[self.frame_key()].ventral_curvatures

            f1 = plt.figure()
            f2 = plt.figure()
            f3 = plt.figure()
            ax1 = f1.add_subplot(111)
            ax1.plot(av_dorsal_cv, 'r')
            ax1.plot(av_ventral_cv, 'g')

            ax2 = f2.add_subplot(111)
            ax2.plot(dorsal_len, 'r')
            ax2.plot(ventral_len, 'g')


            print dlocal_curvatures.tolist()
            ax3 = f3.add_subplot(111)
            ax3.plot(dlocal_curvatures.tolist(), 'r')
            ax3.plot(vlocal_curvatures.tolist(), 'g')
            plt.show()
            UI.show_plot = False


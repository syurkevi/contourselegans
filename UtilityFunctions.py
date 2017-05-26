import json_tricks.np as json
import sys
import numpy as np
from sets import Set
import cv2
from os import path
import math
import matplotlib.pyplot as plt
import UtilityFunctions

def findSeg(frame, segments):
    res = None
    for seg in segments:
        if frame > seg[0] and frame < seg[1]:
            res = seg
            break
    return res

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

#contour related and utility functions
def distance(p1, p2):
    return math.sqrt((p2[0] - p1[0])*(p2[0] - p1[0]) + (p2[1] - p1[1])*(p2[1] - p1[1]))
def distance2(p1, p2):
    return (p2[0] - p1[0])*(p2[0] - p1[0]) + (p2[1] - p1[1])*(p2[1] - p1[1])
#todo: rewrite w lambda func later
def nearest_contour(test_point, contours):
    min_contour = None
    min_dist_contour = 10000000
    for cnt in contours:
        c_mindist = 100000000
        for c in cnt:
            if distance(test_point, c[0]) < c_mindist:
                c_mindist = distance(test_point, c[0])
        if c_mindist < min_dist_contour:
            min_contour = cnt
            min_dist_contour = c_mindist
    return min_contour

def closest_point_idx(target_point, contour):
    min_dist = 10000000
    min_point_id = 0
    for pt in range(len(contour)):
        if distance(target_point, contour[pt][0]) < min_dist:
            min_dist = distance(target_point, contour[pt][0])
            min_point_id = pt
    return min_point_id

def cv_cont_to_jlist(ncont):
    return [x[0] for x in ncont.tolist()]

def contour_length(cnt):
    ln = 0;
    for i in range(len(cnt)-2):
        ln += distance((cnt[i][0], cnt[i][1]), (cnt[i+1][0], cnt[i+1][1]))
    return ln

def curvature(p1, p2, p3):
    A = np.array(p1)
    B = np.array(p2)
    C = np.array(p3)
    a = np.linalg.norm(C - B)
    b = np.linalg.norm(C - A)
    c = np.linalg.norm(B - A)
    s = (a + b + c) / 2
    R = a*b*c / 4 / np.sqrt(s * (s - a) * (s - b) * (s - c))
    b1 = a*a * (b*b + c*c - a*a)
    b2 = b*b * (a*a + c*c - b*b)
    b3 = c*c * (a*a + b*b - c*c)
    P = np.column_stack((A, B, C)).dot(np.hstack((b1, b2, b3)))
    P /= b1 + b2 + b3
    return R

def local_curvature(cnt):
    a = np.array(cnt)
    dx_dt = np.gradient(a[:,0])
    dy_dt = np.gradient(a[:,1])
    velocity = np.array([ [dx_dt[i], dy_dt[i]] for i in range(dx_dt.size) ])
    ds_dt = np.sqrt(dx_dt * dx_dt + dy_dt * dy_dt)
    tangent = np.array([1/ds_dt] * 2).transpose() * velocity
    tangent_x = tangent[:,0]
    tangent_y = tangent[:,1]
    deriv_tangent_x = np.gradient(tangent_x)
    deriv_tangent_y = np.gradient(tangent_y)
    dT_dt = np.array([ [deriv_tangent_x[i], deriv_tangent_y[i]] for i in range(deriv_tangent_x.size)])
    length_dT_dt = np.sqrt(deriv_tangent_x * deriv_tangent_x + deriv_tangent_y * deriv_tangent_y) + 0.000001
    normal = np.array([1/length_dT_dt]*2).transpose() * dT_dt
    d2s_dt2 = np.gradient(ds_dt)
    d2x_dt2 = np.gradient(dx_dt)
    d2y_dt2 = np.gradient(dy_dt)

    curvature = (d2x_dt2 * dy_dt - dx_dt * d2y_dt2) / (dx_dt * dx_dt + dy_dt * dy_dt)**1.5

    av_c = np.sum(curvature) / len(curvature)
    return av_c, curvature

    #local_curvatures = []
    #for i in range(1, len(cnt)-1):
        #local_curvatures.append(curvature(cnt[i-1], cnt[i], cnt[i+1]))
    #return local_curvatures

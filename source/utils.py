import cv2
import os
import random
import json
import numpy as np

from PySide2.QtGui import QImage, QPixmap
from PySide2.QtWidgets import QLayout, QLabel,QVBoxLayout
from PySide2.QtCore import QSize

def numpytoPixmap(cvImg):
    cvImg = cvImg.astype('uint8')
    height, width, channel = cvImg.shape
    bytesPerLine = 3 * width
    qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
    return QPixmap(qImg)

def addBlankToLayout(layout, blankSize):
    assert isinstance(layout, QLayout)
    blank = QLabel("")
    if isinstance(layout, QVBoxLayout):
        blank.setFixedSize(QSize(1, blankSize))
    else:
        blank.setFixedSize(QSize(blankSize, 1))
    layout.addWidget(blank)


class ImageInputs:
    def __init__(self, path):

        folderName = path.split('/')[-1]
        self.path = path
        imagePath = path[:-len(folderName)]

        if not os.path.exists('%s/trimap_candidate'%imagePath):
            os.makedirs('%s/trimap_candidate/1'%imagePath)
            os.makedirs('%s/trimap_candidate/2'%imagePath)
            os.makedirs('%s/trimap_candidate/3'%imagePath)
        if not os.path.exists('%s/result_candidate'%imagePath):
            os.makedirs('%s/result_candidate/alpha'%imagePath)
            os.makedirs('%s/result_candidate/trimap'%imagePath)

        # if not os.path.exists('%s/results'%imagePath):
        #     os.mkdir('%s/results'%imagePath)
        if not os.path.exists('%s/trimaps'%imagePath):
            os.mkdir('%s/trimaps'%imagePath)

        dir_path = [imagePath + 'images/']
        dir_path += [imagePath + 'trimaps/']
        dir_path += [imagePath + 'trimap_candidate/1/']
        dir_path += [imagePath + 'trimap_candidate/2/']
        dir_path += [imagePath + 'trimap_candidate/3/']
        dir_path += [imagePath + 'result_candidate/alpha/']
        dir_path += [imagePath + 'result_candidate/trimap/']

        add = ['{}.jpg', '{}.png', '{}.png', '{}.png', '{}.png', '{}.png', '{}.png']

        imgs = [i.split('.')[0] for i in os.listdir(dir_path[1])]
        self.imgTotal = len(imgs)
        imgs = sorted(imgs)
        self.list = []
        for num,i in enumerate(imgs):
            s = []
            for j, ad in zip(dir_path, add):
                img = ad.format(i)
                path = os.path.join(j, img)
                s.append(path)


            path_list = []
            img_paths = s[0:1]
            tri_paths = s[1:-2]
            res_paths = s[-2:]

            path_list.append(img_paths)
            path_list.append(tri_paths)
            path_list.append(res_paths)
            path_list.append(num)
            self.list.append(path_list)

        self.imgIndexF = {}
        if os.path.exists('../imgIndex'):
            with open('../imgIndex', "r", encoding='utf-8') as f:
                self.imgIndexF = json.load(f)
                imgIndex = self.imgIndexF.get(self.path)
                if not imgIndex:
                    imgIndex = 0
                    self.imgIndexF[self.path] = 0
        else:
            imgIndex = 0
            self.imgIndexF[self.path] = 0

        self.len = len(self.list)
        self.cnt = -1 + imgIndex
    
    def __call__(self):
        self.cnt += 1
        if self.cnt >= self.len:
            return None
        imgPaths, triPaths, resPaths = self.list[self.cnt][:3]
        self.nowImg = cv2.imread(imgPaths[0])
        self.candidateTris = []
        if os.path.exists(resPaths[1]):
            self.candidateTris.append(cv2.imread(resPaths[1]))
        else:
            for triPath in triPaths:
                self.candidateTris.append(cv2.imread(triPath))
        self.nowAlpha = None
        self.imgIndexF[self.path] = self.cnt
        with open('../imgIndex', "w") as f:
            json.dump(self.imgIndexF, f)
        self.imgName = imgPaths[0]

        if os.path.exists(resPaths[0]):
            self.nowAlpha = cv2.imread(resPaths[0])

        return self.nowImg, self.candidateTris, self.nowAlpha, self.imgName

    def previous(self):
        if self.cnt > 0:
            self.cnt -= 1
            imgPaths, triPaths, resPaths = self.list[self.cnt][:3]
            self.nowImg = cv2.imread(imgPaths[0])
            self.imgIndexF[self.path] = self.cnt
            with open('../imgIndex', "w") as f:
                json.dump(self.imgIndexF, f)
            self.candidateTris = []
            if os.path.exists(resPaths[1]):
                self.candidateTris.append(cv2.imread(resPaths[1]))
            else:
                for triPath in triPaths:
                    self.candidateTris.append(cv2.imread(triPath))
            self.nowAlpha = None
            if os.path.exists(resPaths[0]):
                self.nowAlpha = cv2.imread(resPaths[0])
            if self.nowAlpha is None:
                self.nowAlpha = np.zeros(self.nowImg.shape)
            self.imgName = imgPaths[0]

        return self.nowImg, self.candidateTris, self.nowAlpha, self.imgName
    
    def save(self, trimap):
        triPath = self.list[self.cnt][2][1]
        cv2.imwrite(triPath, trimap.astype('uint8'))

    def saveAlpha(self, alpha):
        alphaPath = self.list[self.cnt][2][0]
        cv2.imwrite(alphaPath, alpha)

    def saveBoth(self, alpha, foreground):
        alphaPath = self.list[self.cnt][2][0]
        b_channel, g_channel, r_channel = cv2.split(foreground)
        a_channel = alpha.mean(axis = 2)
        img_bgra = cv2.merge((b_channel, g_channel, r_channel, a_channel))
        cv2.imwrite(alphaPath, img_bgra)

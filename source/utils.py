import cv2
import os
import re,json
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
    def __init__(self,path):
        imglist = os.listdir(path)
        folderName = path.split('/')[-1]
        self.path = path
        imglist = sorted(imglist)
        data = []
        imagePath = path[:-len(folderName)]
        if not os.path.exists('%s/results'%imagePath):
            os.mkdir('%s/results'%imagePath)
        if not os.path.exists('%s/trimaps'%imagePath):
            os.mkdir('%s/trimaps'%imagePath)
        for num, i in enumerate(imglist):
            if bool(re.search('jpg|png|JPG|PNG|JPEG',i)):
                data.append(['%s/%s/%s' % (imagePath,folderName, i),
                             imagePath+'trimaps/%s' % (i.split('.')[0]+'.png'),
                             imagePath+'results/%s' % (i.split('.')[0]+'.png'),
                             num])
        self.imgIndexF = {}
        if os.path.exists('../imgIndex'):
            with open('../imgIndex', "r",encoding='utf-8') as f:
                self.imgIndexF = json.load(f)
                imgIndex = self.imgIndexF.get(path)
                if not imgIndex:
                    imgIndex = 0
                    self.imgIndexF[path] = 0
        else:
            imgIndex = 0
            self.imgIndexF[path]=0
        self.list = data
        self.len = len(self.list)
        self.cnt = -1 + imgIndex

    def __call__(self):
        self.cnt += 1
        if self.cnt >= self.len:
            return None
        imgPath, triPath, alphaPath,_ = self.list[self.cnt][:4]
        self.nowImg = cv2.imread(imgPath)
        if os.path.exists(triPath):
            self.nowTri = cv2.imread(triPath)
            self.nowTriExist = True
        else:
            self.nowTri = np.ones(self.nowImg.shape) * 255
            self.nowTriExist = False
        self.nowAlpha = None
        self.imgIndexF[self.path] = self.cnt
        with open('../imgIndex', "w") as f:
            json.dump(self.imgIndexF, f)
        self.imgName = imgPath
        if os.path.exists(alphaPath):
            self.nowAlpha = cv2.imread(alphaPath)
        return self.nowImg, self.nowTri, self.nowAlpha, self.imgName,self.nowTriExist

    def previous(self):
        if self.cnt > 0:
            self.cnt -= 1
            imgPath, triPath, alphaPath,_ = self.list[self.cnt][:4]
            self.nowImg = cv2.imread(imgPath)
            self.imgIndexF[self.path] = self.cnt
            with open('../imgIndex', "w") as f:
                json.dump(self.imgIndexF, f)
            if os.path.exists(triPath):
                self.nowTri = cv2.imread(triPath)
                self.nowTriExist = True
            else:
                self.nowTri = np.ones(self.nowImg.shape) * 255
                self.nowTriExist = False
            self.nowAlpha = None
            self.imgName = imgPath
            if os.path.exists(alphaPath):
                self.nowAlpha = cv2.imread(alphaPath)

        return self.nowImg, self.nowTri, self.nowAlpha, self.imgName,self.nowTriExist
    
    def save(self, trimap):
        imgPath, triPath = self.list[self.cnt][:2]
        cv2.imwrite(triPath, trimap.astype('uint8'))

    def saveAlpha(self, alpha):
        alphaPath = self.list[self.cnt][2]
        cv2.imwrite(alphaPath, alpha)

    def saveBoth(self, alpha, foreground):
        alphaPath = self.list[self.cnt][2]
        b_channel, g_channel, r_channel = cv2.split(foreground)
        a_channel = alpha.mean(axis = 2)
        img_bgra = cv2.merge((b_channel, g_channel, r_channel, a_channel))
        cv2.imwrite(alphaPath, img_bgra)

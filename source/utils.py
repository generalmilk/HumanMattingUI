import cv2
import os
import json
import sys,re
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
        imageResultName = re.findall('data_(\d*)', imagePath.split('/')[-2])
        if bool(imageResultName):
            resultImgPath = 'result_' + imageResultName[0]
        else:
            resultImgPath = 'result'
        if not os.path.exists('%s/%s/alpha' % (imagePath, resultImgPath)):
            os.makedirs('%s/%s/alpha' % (imagePath, resultImgPath))
        if not os.path.exists('%s/%s/trimap' % (imagePath, resultImgPath)):
            os.makedirs('%s/%s/trimap' % (imagePath, resultImgPath))

        dir_path = [imagePath + '%s/' % folderName]
        dir_path += [imagePath + 'trimaps/']
        dir_path += [imagePath + 'candidates/trimap/face/']
        dir_path += [imagePath + 'candidates/trimap/filler_3/']
        dir_path += [imagePath + 'candidates/trimap/filler_4/']
        dir_path += [imagePath + 'candidates/trimap/filler_5/']

        dir_path += [imagePath + '%s/alpha/' % resultImgPath]
        dir_path += [imagePath + '%s/trimap/' % resultImgPath]
        add = ['{}.jpg', '{}.png', '{}.png', '{}.png', '{}.png', '{}.png', '{}.png','{}.png']
        imgs = [i.split('.')[0] for i in os.listdir(dir_path[0]) if i.split('.')[1]=='jpg']
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
            tri_path = s[1:2]
            tri_paths = s[2:-2]
            res_paths = s[-2:]

            path_list.append(img_paths)
            path_list.append(tri_paths)
            path_list.append(res_paths)
            path_list.append(num)
            path_list.append(tri_path)
            self.list.append(path_list)

        self.imgIndexF = {}
        if os.path.exists('imgIndex'):
            with open('imgIndex', "r", encoding='utf-8') as f:
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
            self.cnt=self.len-1
        imgPaths, triPaths, resPaths,_,triPath = self.list[self.cnt][:5]
        self.nowImg = cv2.imread(imgPaths[0])
        self.candidateTris = []
        if os.path.exists(resPaths[1]):
            self.candidateTris.append(cv2.imread(resPaths[1]))
        elif os.path.exists(triPath[0]):
            self.candidateTris.append(cv2.imread(triPath[0]))
        else:
            for triPath in triPaths:
                if os.path.exists(triPath):
                    self.candidateTris.append(cv2.imread(triPath))
            if not self.candidateTris:
                self.candidateTris = [np.ones(self.nowImg.shape)*255.0]
        self.nowAlpha = None
        self.imgIndexF[self.path] = self.cnt
        with open('imgIndex', "w") as f:
            json.dump(self.imgIndexF, f)
        self.imgName = imgPaths[0]

        if os.path.exists(resPaths[0]):
            alpha = cv2.imread(resPaths[0], cv2.IMREAD_UNCHANGED)
            b, g, r, a = cv2.split(alpha)
            a = np.stack([a] * 3, axis=2)/255.0
            self.nowAlpha = a

        # if self.nowAlpha is None:
        #     self.nowAlpha = np.ones(self.nowImg.shape)*255.0

        return self.nowImg, self.candidateTris, self.nowAlpha, self.imgName,self.cnt,self.len

    def previous(self):
        self.cnt -= 1
        if self.cnt < 0:
            self.cnt = 0

        if self.cnt >=0:
            imgPaths, triPaths, resPaths,_,triPath = self.list[self.cnt][:5]
            self.nowImg = cv2.imread(imgPaths[0])
            self.imgIndexF[self.path] = self.cnt
            with open('imgIndex', "w") as f:
                json.dump(self.imgIndexF, f)
            self.candidateTris = []
            if os.path.exists(resPaths[1]):
                self.candidateTris.append(cv2.imread(resPaths[1]))
            elif os.path.exists(triPath[0]):
                self.candidateTris.append(cv2.imread(triPath[0]))
            else:
                for triPath in triPaths:
                    if os.path.exists(triPath):
                        self.candidateTris.append(cv2.imread(triPath))
                if not self.candidateTris:
                    self.candidateTris = [np.ones(self.nowImg.shape)*255.0]
            self.nowAlpha = None
            if os.path.exists(resPaths[0]):
                self.nowAlpha = [cv2.imread(resPaths[0])]
            # if self.nowAlpha is None:
            #     self.nowAlpha = np.ones(self.nowImg.shape)*255.0
            self.imgName = imgPaths[0]

            return self.nowImg, self.candidateTris, self.nowAlpha, self.imgName,self.cnt,self.len

    
    def save(self, trimap):
        triPath = self.list[self.cnt][2][1]
        cv2.imwrite(triPath, trimap.astype('uint8'))

    def saveAlpha(self, alpha):
        alphaPath = self.list[self.cnt][2][0]

        cv2.imwrite(alphaPath, alpha)

    def saveBoth(self, alpha, foreground):
        alphaPath = self.list[self.cnt][2][0]
        b_channel, g_channel, r_channel = cv2.split(foreground.astype('uint8'))
        a_channel = alpha.mean(axis = 2).astype('uint8')
        img_bgra = cv2.merge((b_channel, g_channel, r_channel, a_channel))
        cv2.imwrite(alphaPath, img_bgra)

    def lastImage(self, alpha, foreground):
        b_channel, g_channel, r_channel = cv2.split(foreground)
        a_channel = alpha.mean(axis = 2)
        img_bgra = cv2.merge((b_channel, g_channel, r_channel, a_channel))
        return img_bgra
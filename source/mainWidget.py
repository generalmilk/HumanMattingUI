import sys
import json
import os, copy
import numpy as np
import cv2

from PySide2.QtWidgets import (QApplication, QVBoxLayout, QWidget,
                               QHBoxLayout, QSlider, QFileDialog, QMessageBox, QGroupBox, QGridLayout, QPushButton)
from PySide2.QtCore import Slot, Qt, QSize
from PySide2.QtGui import QPixmap, QImage, QCursor, QFont, QIcon

from widgets import MyPushButton, ClickLabel, MySlider, MyButtonGroup, MyToolButton, MyColorButton, HoverButtonTop, HoverButtonBottom
from utils import numpytoPixmap, ImageInputs, addBlankToLayout
from matting.solve_foreground_background import solve_foreground_background
import tools
import config
import algorithm
from selectDialog import SelectDialog


class MyWidget(QWidget):
    def setImage(self, x, pixmap=None, array=None, resize=False, grid=False):
        assert pixmap is None or not grid, "Pixmap cannot draw grid."

        if pixmap is None:
            if array is None:
                self.texts[x].setPixmap(None)
                return

            array = array.astype('uint8')

            if grid:
                array = cv2.resize(array, self.rawSize)

                for i in self.splitArrX[:-1]:
                    i = int(i * self.f)
                    array[i] = np.array((0, 255, 0))
                for i in self.splitArrY[:-1]:
                    i = int(i * self.f)
                    array[:, i] = np.array((0, 255, 0))

                resize = False

            pixmap = numpytoPixmap(array)
        imgx, imgy = self.scale
        if resize:
            pixmap = pixmap.scaled(imgx, imgy, Qt.KeepAspectRatio)
        self.texts[x].setPixmap(pixmap)

    def setFinal(self):
        fileName = self.imgName.split('/')[-1]
        imagePath = self.imgName[:-len(fileName)]
        folderName = imagePath.split('/')[-2]
        # self.path = path
        # imagePath = path[:-len(folderName)]

        if fileName:
            fileName = fileName.split('.')[0] + '.png'
        else:
            fileName = 'None'

        mouse = self.mouse
        try:
            status = self.selectDialog.selectTrue
        except:
            status = False

        if self.final is None and not status:
            self.setImage(-1)
        else:
            if status==True:
                alpha = self.imageResult1[self.selectDialog.selectId]
                b, g, r, a = cv2.split(alpha)
                bgr = np.stack([b, g, r], axis=2)
                a = np.stack([a] * 3, axis=2) / 255.0
                show = self.changeBackground(a, True, bgr)
                self.selectDialog.selectTrue = False
            elif not mouse and os.path.exists(imagePath[:-len(folderName)-1]+'results/alpha/' + fileName):
                alpha = cv2.imread(imagePath[:-len(folderName)-1]+'results/alpha/' + fileName, cv2.IMREAD_UNCHANGED)
                b, g, r, a = cv2.split(alpha)
                bgr = np.stack([b, g, r], axis=2)
                a = np.stack([a] * 3, axis=2) / 255.0
                show = self.changeBackground(a, True, bgr)
                self.setImage(-1, array=show, resize=True, grid=self.gridFlag)
            else:
                alpha = self.final.mean(axis=2) / 255.0
                show = self.changeBackground(alpha,False)
                self.mouse = False
            self.setImage(-1, array=show, resize=True, grid=self.gridFlag)

    def setSet(self):
        try:
            show = self.image * (1 - self.imageAlpha) + self.trimap * self.imageAlpha
            self.setImage(0, array=show)
        except:
            pass

    def setSetToggle(self, Alpha):
        try:
            show = self.image * (1 - Alpha) + self.trimap * Alpha
            self.setImage(0, array=show)
        except:
            pass

    def changeBG(self, bgid):
        self.bgid = bgid
        self.background = config.getBackground(self.rawSize[::-1], self.bgid)
        QApplication.processEvents()
        self.setFinal()

    def changeBackground(self, alpha,result,bgr=None):
        if not result:
            image, trimap = self.resizeToNormal()
            F, B = solve_foreground_background(image, alpha)
            F = F * (F >= 0)
            F = 255 * (F > 255) + F * (F <= 255)
            self.foreground = F
            alpha = np.stack([alpha] * 3, axis=2)
            show = F * alpha + (1 - alpha) * self.background
        else:
            self.foreground = bgr
            self.final = (alpha*255.0).astype('uint8')
            F = self.foreground
            show = F * alpha + (1 - alpha) * self.background
        return show


    def openSelectDialog(self, image, trimaps, imgPath):
        imgData = imgPath.split('/')
        imgName = imgData[-1]
        imgId = imgData[-1].split('.')[0]
        imgFolder = imgData[-2]
        resPath = imgPath[:len(imgPath) - int(len(imgName) + len(imgFolder) + 1)]
        dir_path = [resPath + 'candidates/result/face/%s.png' % imgId]
        dir_path += [resPath + 'candidates/result/filler_3/%s.png' % imgId]
        dir_path += [resPath + 'candidates/result/filler_4/%s.png' % imgId]
        dir_path += [resPath + 'candidates/result/filler_5/%s.png' % imgId]
        self.imageResult = []
        for i in dir_path:
            if os.path.exists(i):
                self.imageResult.append(cv2.imread(i, cv2.IMREAD_UNCHANGED))
        self.imageResult1 = copy.deepcopy(self.imageResult)
        self.selectDialog = SelectDialog(image, self.imageResult)
        if self.selectDialog.exec_():
            return trimaps[self.selectDialog.selectId]
        else:
            return trimaps[0]

    def open(self):
        list_file = QFileDialog.getExistingDirectory(self, 'open dir', '.')
        self.imageList = ImageInputs(list_file)
        self.newSet()
        QApplication.processEvents()
        # self.setImageAlpha(self.imageAlpha)



    def newSet(self, prev=False):
        for text in self.texts:
            text.setPixmap(None)
        if prev:
            self.image, self.trimaps, self.final, self.imgName = self.imageList.previous()
            if len(self.trimaps) == 1:
                self.trimap = self.trimaps[0]
            else:
                self.trimap = self.openSelectDialog(self.image, self.trimaps, self.imgName)
        else:
            try:
                self.image, self.trimaps, self.final, self.imgName = self.imageList()
            except:
                return None
            if len(self.trimaps) == 1:
                self.trimap = self.trimaps[0]
            else:
                self.trimap = self.openSelectDialog(self.image, self.trimaps, self.imgName)
        if len(self.trimap.shape) == 2:
            self.trimap = np.stack([self.trimap] * 3, axis=2)
        assert self.image.shape == self.trimap.shape

        h, w = self.image.shape[:2]
        imgw, imgh = self.scale
        self.f = min(imgw / w, imgh / h)
        self.rawSize = (w, h)
        self.rawImage = self.image
        self.background = config.getBackground((h, w), self.bgid)
        self.image = cv2.resize(self.image, None, fx=self.f, fy=self.f)
        self.trimap = cv2.resize(self.trimap, None, fx=self.f, fy=self.f, interpolation=cv2.INTER_NEAREST)

        self.history = []
        self.alphaHistory = []
        self.outputs = []

        # self.run()
        self.setSet()
        QApplication.processEvents()
        self.setFinal()
        self.getGradient()
        self.setWindowTitle(self.imgName.split('/')[-1])

    def popup(self):  # 下一页
        self.saveAlpha()
        self.newSet()

    def abandon(self):
        imgData = self.imgName.split('/')
        imgName = imgData[-1]
        imgFolder = imgData[-2]
        resPath = self.imgName[:len(self.imgName) - int(len(imgName) + len(imgFolder) + 1)]

        if imgData:
            fileName = imgName.split('.')[0]+'.png'
        else:
            fileName = 'None'
        resultFolder = [resPath+'results/alpha/',resPath+'results/trimap/']
        for path in resultFolder:
            if os.path.exists(path+fileName):
                os.remove(path+fileName)
        self.newSet()

    def getGradient(self):
        self.grad = algorithm.calcGradient(self.image)

    def resizeToNormal(self):
        # f = 1 / self.f
        # image = cv2.resize(self.image, self.rawSize)
        image = self.rawImage
        trimap = cv2.resize(self.trimap, self.rawSize, interpolation=cv2.INTER_NEAREST)
        return image, trimap

    def splitUp(self):
        def splitArr(arr):
            las = 0
            new = []
            for i in arr:
                new.append((las + i) // 2)
                new.append(i)
                las = i
            return new

        if len(self.splitArrX) < 128:
            self.splitArrX = splitArr(self.splitArrX)
            self.splitArrY = splitArr(self.splitArrY)
            self.resultTool.setArr(self.splitArrX, self.splitArrY)

    def splitDown(self):
        if len(self.splitArrX) > 2:
            self.splitArrX = self.splitArrX[1::2]
            self.splitArrY = self.splitArrY[1::2]
            self.resultTool.setArr(self.splitArrX, self.splitArrY)

    def solveForeground(self):
        self.setHistory()
        self.trimap = np.ones(self.trimap.shape) * 255

    def showGrid(self):
        self.gridFlag = not self.gridFlag

    def setImageAlpha(self, num):
        self.imageAlpha = num
        self.setSet()
        self.imageAlphaSlider.setValue(num)
        QApplication.processEvents()

    def setFiller(self, num):
        self.filler.setTheta(num)
        self.fillerSlider.setValue(num)

        if self.lastCommand == "Filler":
            self.undo()
            self.tool.refill()

    def fillerUp(self, num=1):
        theta = self.filler.getTheta()
        self.setFiller(theta * (1.01 ** num))

    def setPen(self, num):
        self.pen.setThickness(num)
        self.penSlider.setValue(num)

    def penUp(self, num=1):
        thickness = self.pen.getThickness()
        self.setPen(thickness + num)

    def unknownUp(self):
        if self.lastCommand != "FillUnknown":
            return
        self.undo()
        self.fillWidth += 1
        self.fillUnknown(True)

    def unknownDown(self):
        if self.lastCommand != "FillUnknown":
            return

        if self.fillWidth == 1:
            return

        self.undo()
        self.fillWidth -= 1
        self.fillUnknown(True)

    def fillUnknown(self, refill=False):
        self.setHistory("FillUnknown")
        self.trimap = algorithm.fillUnknown(self.trimap, width=self.fillWidth)

    def squeeze(self):
        self.setHistory()
        self.trimap = algorithm.squeeze(self.trimap)

    def undo(self):
        self.lastCommand = None
        if len(self.history) > 0:
            self.reHistory.append(self.trimap)
            self.trimap = self.history.pop()
            self.setSet()
            QApplication.processEvents()

    def redo(self):
        self.lastCommand = None
        if len(self.reHistory) > 0:
            self.history.append(self.trimap)
            self.trimap = self.reHistory.pop()
            self.setSet()
            QApplication.processEvents()

    def undoAlpha(self):
        if len(self.alphaHistory) > 0:
            self.history.append(self.trimap)
            self.final = self.alphaHistory.pop()
            self.setSet()
            QApplication.processEvents()

    def save(self):
        image, trimap = self.resizeToNormal()
        self.imageList.save(trimap)

    def saveAlpha(self):
        self.imageList.saveBoth(self.final, self.foreground)
        self.save()
        # self.saveStatus = 1
        # QMessageBox.information(self, "", "sucess", QMessageBox.Yes)

    def run(self):
        self.mouse = True
        image, trimap = self.resizeToNormal()
        self.outputs = []
        for i, func in enumerate(self.functions):
            output = func(image, trimap)
            if output.ndim == 2:
                output = np.stack([output] * 3, axis=2)
            self.outputs.append(output)
        if True:  # self.final is None:
            self.final = self.outputs[-1].copy()
        QApplication.processEvents()

    def getToolObject(self, id):
        if id in [0, 1, 2]:
            return self.tool

    def click(self, pos, id):
        tool = self.getToolObject(id)
        if tool is not None:
            tool.click(pos)

    def drag(self, pos, id):
        tool = self.getToolObject(id)
        if tool is not None:
            tool.drag(pos)

    def release(self, pos, id):
        tool = self.getToolObject(id)
        if tool is not None:
            tool.release(pos)

    def setColor(self, color):
        color = config.painterColors[color]
        self.tool.setColor(color)

    def setHistory(self, command=None):
        self.lastCommand = command
        self.history.append(self.trimap.copy())

    def setAlphaHistory(self):
        self.alphaHistory.append(self.final.copy())

    def setTool(self, toolName):
        assert toolName in tools.painterTools, toolName + " not implement!!"
        self.tool = tools.painterTools[toolName]
        assert self.tool.toolName == toolName, toolName + " mapping wrong object"

    def initImageLayout(self):

        self.hImageGroupBox = QGroupBox()
        imageLayout = QGridLayout()

        imageSourceGroupBox = QGroupBox()
        imageResultGroupBox = QGroupBox()

        imgx, imgy = self.scale
        self.texts = []
        for i in range(1):
            text = ClickLabel(self, i, "None")
            text.setAlignment(Qt.AlignTop)
            text.setFixedSize(QSize(imgx, imgy))
            self.texts.append(text)

        text = ClickLabel(self, 1, "")
        text.setAlignment(Qt.AlignTop)
        text.setFixedSize(QSize(imgx, imgy))
        self.texts.append(text)

        texts = self.texts[:3] + self.texts[-1:]

        imageSourceLayout = QHBoxLayout()
        imageSourceLayout.addWidget(texts[0])
        imageSourceGroupBox.setLayout(imageSourceLayout)
        imageResultLayout = QHBoxLayout()
        imageResultLayout.addWidget(texts[1])
        imageResultGroupBox.setLayout(imageResultLayout)

        imageLayout.addWidget(imageSourceGroupBox, 0, 0)
        imageLayout.addWidget(imageResultGroupBox, 0, 1)

        self.hImageGroupBox.setLayout(imageLayout)

    def setSlider(self, obj, command):
        if command == 'ImageAlphaSlider':
            self.imageAlphaSlider = obj
        elif command == 'FillerSlider':
            self.fillerSlider = obj
        elif command == 'PenSlider':
            self.penSlider = obj

    def setButtonGroup(self, obj, command):
        if command == 'Foreground&Background&Unknown':
            self.trimapButtonGroup = obj
        elif command == 'Grid&Red&Green&Blue':
            self.backgroundButtonGroup = obj

    def initToolLayout(self):
        bx, by = self.buttonScale
        bC = self.buttonCol
        blankSize = self.blankSize
        self.toolWidgets = []

        self.toolLayout = QHBoxLayout()
        self.toolLayout.addStretch(1)

        self.toolLayoutLeft = QVBoxLayout()
        self.toolLayoutLeft.setMargin(10)
        # self.toolLayoutLeft.addStretch(1)

        self.toolLayoutRight = QVBoxLayout()
        self.toolLayoutRight.setMargin(10)
        self.toolLayoutRight.addStretch(1)

        for line in config.toolTexts:
            tempLine = []
            for tool in line:
                tempTool = []
                if not isinstance(tool, list):
                    tool = [tool]
                n = len(tool)
                for command in tool:
                    if command[0] == '#':
                        continue
                    elif command == '*':
                        tempLine.append(None)
                    elif command[-1] == '-':
                        command = command[:-1]
                        temp = MySlider(self, command, Qt.Horizontal)
                        self.setSlider(temp, command)
                        temp.setTickPosition(QSlider.TicksBothSides)
                        lef, rig, typ = config.sliderConfig[command]
                        temp.setSliderType(lef, rig, type=typ)
                        temp.setFixedSize(QSize(bx * 3 + config.defaultBlank * 2, by))
                        self.setSlider(temp, command)

                        tempTool.append(temp)
                    elif command[-1] == '=':
                        command = command[:-1]
                        buttonGroup = MyButtonGroup(self, command)
                        subCommands = command.split('&')
                        id = 0
                        for subCommand in subCommands:
                            temp = MyColorButton(self, subCommand)
                            if subCommand == "Foreground":
                                temp.setIcon(QIcon("icon/icon_1.png"))
                            elif subCommand == "Background":
                                temp.setIcon(QIcon("icon/icon_2.png"))
                            elif subCommand == "Unknown":
                                temp.setIcon(QIcon("icon/icon_3.png"))
                            buttonGroup.addRadioButton(temp, id)
                            tempTool.append(temp)
                            id += 1
                        self.setButtonGroup(buttonGroup, command)

                    else:
                        temp = MyPushButton(self, config.getText(command), command)
                        temp.setFixedSize(QSize(bx, (by - config.defaultBlank * (n - 1)) // n))
                        tempTool.append(temp)

                if len(tempTool) > 0:
                    tempLine.append(tempTool)
            if len(tempLine) > 0:
                self.toolWidgets.append(tempLine)

    def initAlphaSliderLayout(self):
        self.vboxAlphaBox = QGroupBox()
        self.vboxAlphaBox.setFixedWidth(120)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        TrimapBtn = HoverButtonTop(self,"Trimap")
        TrimapBtn.setText('蒙板')
        layout.addWidget(TrimapBtn)
        TrimapBtn.clicked.connect(lambda:self.Trimap_click(1))

        temp = MySlider(self, 'ImageAlphaSlider', Qt.Vertical)
        self.setSlider(temp, 'ImageAlphaSlider')
        temp.setTickPosition(QSlider.TicksBothSides)
        lef, rig, typ = config.sliderConfig['ImageAlphaSlider']
        temp.setSliderType(lef, rig, type=typ)
        temp.setFixedWidth(100)
        self.setSlider(temp, 'ImageAlphaSlider')
        layout.addWidget(temp)

        ImageBtn = HoverButtonBottom(self,"Image")
        ImageBtn.setText('原图')
        layout.addWidget(ImageBtn)
        ImageBtn.clicked.connect(lambda:self.Image_click(0))

        self.vboxAlphaBox.setLayout(layout)

    def Trimap_click(self, num):
        self.setImageAlpha(num)

    def Image_click(self, num):
        self.setImageAlpha(num)

    def initToolLeftGridLayout(self):
        bx, by = self.buttonScale
        bC = self.buttonCol
        blankSize = self.blankSize

        self.toolLeftGridGroupBox = QGroupBox()
        layout = QGridLayout()

        # Foreground Background Unknown
        buttonGroup = MyButtonGroup(self, "Foreground&Background&Unknown")
        self.colorBox = QGroupBox()
        colorLayout = QVBoxLayout()
        foregroundRadio = MyColorButton(self, "Foreground")
        foregroundRadio.setIcon(QIcon("icon/icon_1.png"))
        colorLayout.addWidget(foregroundRadio)
        buttonGroup.addRadioButton(foregroundRadio, 0)

        backgroundRadio = MyColorButton(self, "Background")
        backgroundRadio.setIcon(QIcon("icon/icon_2.png"))
        colorLayout.addWidget(backgroundRadio)
        buttonGroup.addRadioButton(backgroundRadio, 1)

        unknownRadio = MyColorButton(self, "Unknown")
        unknownRadio.setIcon(QIcon("icon/icon_3.png"))
        colorLayout.addWidget(unknownRadio)
        buttonGroup.addRadioButton(unknownRadio, 2)
        self.colorBox.setLayout(colorLayout)
# ~~~~~

        buttonGroup2 = MyButtonGroup(self, "Pen&Filler")
        self.colorBox2 = QGroupBox()
        colorLayout = QVBoxLayout()
        penRadio = MyToolButton(self, "画笔")
        penRadio.setIcon(QIcon("icons/brush.png"))
        # penRadio.setIcon(QIcon("icon/icon_1.png"))
        colorLayout.addWidget(penRadio)
        buttonGroup2.addRadioButton(penRadio, 0)

        fillerRadio = MyToolButton(self, "油漆桶")
        fillerRadio.setIcon(QIcon("icons/filler.png"))
        colorLayout.addWidget(fillerRadio)
        buttonGroup2.addRadioButton(fillerRadio, 1)
        self.colorBox2.setLayout(colorLayout)
# ~~~~~
        # drawButtonGroup = MyButtonGroup(self, "Pen&Filler")
        # self.toolBox = QGroupBox()
        # colorLayout = QVBoxLayout()
        # penRadio = MyColorButton(self, "Pen")
        # foregroundRadio.setIcon(QIcon("icon/icon_1.png"))
        # colorLayout.addWidget(foregroundRadio)
        # buttonGroup.addRadioButton(foregroundRadio, 0)

        # fillerRadio = MyColorButton(self, "Filler")
        # backgroundRadio.setIcon(QIcon("icon/icon_2.png"))
        # colorLayout.addWidget(backgroundRadio)
        # buttonGroup.addRadioButton(backgroundRadio, 1)


        # pen
        penButton = MyPushButton(self, config.getText("Pen"), "Pen")
        penButton.setFixedSize(QSize(80, 40))
        # pen slider
        penSlider = MySlider(self, "PenSlider", Qt.Horizontal)
        self.setSlider(penSlider, "PenSlider")
        penSlider.setTickPosition(QSlider.TicksBothSides)
        lef, rig, typ = config.sliderConfig["PenSlider"]
        penSlider.setSliderType(lef, rig, type=typ)
        penSlider.setFixedSize(QSize(bx * 3 + config.defaultBlank * 2, by))
        self.setSlider(penSlider, "PenSlider")

        # filler
        fillerButton = MyPushButton(self, config.getText("Filler"), "Filler")
        fillerButton.setFixedSize(QSize(80, 40))
        # filler slider
        fillerSlider = MySlider(self, "FillerSlider", Qt.Horizontal)
        self.setSlider(fillerSlider, "FillerSlider")
        fillerSlider.setTickPosition(QSlider.TicksBothSides)
        lef, rig, typ = config.sliderConfig["FillerSlider"]
        fillerSlider.setSliderType(lef, rig, type=typ)
        fillerSlider.setFixedSize(QSize(bx * 3 + config.defaultBlank * 2, by))
        self.setSlider(fillerSlider, "FillerSlider")

        # clean trimap
        cleantrimapButton = MyPushButton(self, config.getText("SolveForeground"), "SolveForeground")
        cleantrimapButton.setIcon(QIcon("icons/clearscreen.png"))
        undoButton = MyPushButton(self, config.getText("Undo"), "Undo")
        undoButton.setIcon(QIcon("icons/undo.png"))
        redoButton = MyPushButton(self, config.getText("Redo"), "Redo")
        redoButton.setIcon(QIcon("icons/redo.png"))
        # cleantrimapButton.setFixedSize(QSize(80,40))

        fileUnknownButton = MyPushButton(self, config.getText("FillUnknown"), "FillUnknown")
        unknownUpButton = MyPushButton(self, config.getText("UnknownUp"), "UnknownUp")
        unknownDownButton = MyPushButton(self, config.getText("UnknownDown"), "UnknownDown")
        # fileUnknownButton.setFixedSize(QSize(self.width(),40))
        #fileUnknownButton.setFixedHeight(60)
        # unknownUpButton.setFixedHeight(40)
        # unknownUpButton.setFixedSize(QSize(self.width(),40))

        runButton = MyPushButton(self, config.getText("Run"), "Run")
        runButton.setFixedHeight(60)
        runButton.setStyleSheet("QPushButton{color:white;font-size:18px;}"
                                "QPushButton:hover{background-color:#05f}"
                                "QPushButton{background-color:#477be4}"
                                "QPushButton{border:2px}"
                                "QPushButton{border-radius:10px}"
                                "QPushButton{padding:2px 4px}")
        penSlider.setStyleSheet("QSlider{padding:0px 0px}")
        layout.setSpacing(0)
        layout.addWidget(self.colorBox, 0, 0, 2, 1)
        layout.addWidget(self.colorBox2, 0, 1, 2, 1)

        # layout.addWidget(penButton, 0, 1)
        layout.addWidget(penSlider, 0, 2, 2, 4)
        # layout.addWidget(fillerButton, 1, 1)
        layout.addWidget(fillerSlider, 0, 2, 4, 4)
        layout.addWidget(cleantrimapButton, 2, 0)
        layout.addWidget(undoButton, 2, 1)
        layout.addWidget(redoButton, 2, 2)
        layout.addWidget(fileUnknownButton, 3, 0, 2, 1)
        layout.addWidget(unknownUpButton, 3, 1)
        layout.addWidget(unknownDownButton, 3, 2)
        layout.addWidget(runButton, 2, 4, 2, 2)
        self.toolLeftGridGroupBox.setLayout(layout)

    def initToolRightGridLayout(self):
        bx, by = self.buttonScale
        bC = self.buttonCol
        blankSize = self.blankSize

        self.toolWidgets = []

        self.toolRightGridGroupBox = QGroupBox()
        self.toolRightGridGroupBox.setFixedWidth(400)
        layout = QGridLayout()

        # Foreground Background Unknown
        buttonGroup = MyButtonGroup(self, "Grid&Red&Green&Blue")
        self.colorBox = QGroupBox()
        colorLayout = QHBoxLayout()
        GridRadio = MyColorButton(self, "Grid")
        GridRadio.setIcon(QIcon(QPixmap("iconss/grid.png")))
        colorLayout.addWidget(GridRadio)
        buttonGroup.addRadioButton(GridRadio, 0)

        redRadio = MyColorButton(self, "Red")
        redRadio.setIcon(QIcon(QPixmap("iconss/red.png")))
        colorLayout.addWidget(redRadio)
        buttonGroup.addRadioButton(redRadio, 1)

        greenRadio = MyColorButton(self, "Green")
        greenRadio.setIcon(QIcon(QPixmap("iconss/green.png")))
        colorLayout.addWidget(greenRadio)
        buttonGroup.addRadioButton(greenRadio, 2)

        blueRadio = MyColorButton(self, "Blue")
        blueRadio.setIcon(QIcon(QPixmap("iconss/blue.png")))
        colorLayout.addWidget(blueRadio)
        self.colorBox.setLayout(colorLayout)
        buttonGroup.addRadioButton(blueRadio, 3)

        # Previous
        previousButton = MyPushButton(self, config.getText("Previous"), "Previous")
        # Next
        nextButton = MyPushButton(self, config.getText("Submit"), "Submit")
        # Abandon
        abandonButton = MyPushButton(self, config.getText("Abandon"), "Abandon")

        # clean trimap
        # openButton = QPushButton("Open")
        # openButton = MyPushButton(self, config.getText("Open"), "Open")
        openButton = MyPushButton(self, config.getText("Open"), "Open")
        # saveButton = MyPushButton(self, config.getText("SaveAlpha"), "SaveAlpha")
        previousButton.setFixedHeight(40)
        nextButton.setFixedHeight(40)
        abandonButton.setFixedHeight(40)
        openButton.setFixedHeight(40)
        # saveButton.setFixedHeight(60)
        openButton.setStyleSheet("QPushButton{color:white;font-size:18px;}"
                                 "QPushButton:hover{background-color:#008000}"
                                 "QPushButton{background-color:#008000}"
                                 "QPushButton{border:2px}"
                                 "QPushButton{border-radius:4px}"
                                 "QPushButton{padding:2px 4px}")
        previousButton.setStyleSheet("QPushButton{color:#444;font-size:18px;}"
                                 "QPushButton:hover{background-color:#b7b7b7}"
                                 "QPushButton{background-color:#e7e7e7;border-color: #b7b7b7;}"
                                 "QPushButton{border:1px solid transparent;}"
                                 "QPushButton{border-radius:4px}"
                                 "QPushButton{padding:2px 4px}")
        nextButton.setStyleSheet("QPushButton{color:#fff;font-size:18px;}"
                                 "QPushButton:hover{background-color:#337ab7;border-color: #2e6da4;}"
                                 "QPushButton{background-color:#3c8dbc;border-color: #367fa9;}"
                                 "QPushButton{border:1px solid transparent;}"
                                 "QPushButton{border-radius:4px}"
                                 "QPushButton{padding:2px 4px}")
        abandonButton.setStyleSheet("QPushButton{color:white;font-size:18px;}"
                                 "QPushButton:hover{background-color:#B22222}"
                                 "QPushButton{background-color:#B22222;}"
                                 "QPushButton{border:2px}"
                                 "QPushButton{border-radius:4px}"
                                 "QPushButton{padding:2px 4px}")

        # layout.setSpacing(10)
        layout.addWidget(self.colorBox, 0, 0, 1, 2)
        # layout.addWidget(previousButton, 1, 1)
        # layout.addWidget(nextButton, 1, 2)
        # layout.addWidget(abandonButton, 1, 3)
        layout.addWidget(openButton, 1, 0)
        layout.addWidget(previousButton, 1, 1)
        layout.addWidget(nextButton, 2, 0)
        layout.addWidget(abandonButton, 2, 1)
        self.toolRightGridGroupBox.setLayout(layout)

    def __init__(self, functions):

        QWidget.__init__(self)
        self.setMinimumSize(1100, 715)
        self.setMaximumSize(1100, 715)
        self.functions = functions
        self.lastCommand = None
        self.history = []
        self.reHistory = []

        # self.imageList = imageList
        self.scale = config.imgScale
        self.n = 4 + len(functions)

        self.buttonScale = config.buttonScale
        self.buttonCol = config.buttonCol
        self.blankSize = config.blankSize

        self.filler = tools.painterTools['Filler']
        self.pen = tools.painterTools['Pen']
        self.tool = self.filler
        self.tool.setWidget(self)
        self.gridFlag = False

        self.fillWidth = 5
        self.drewAction = 0
        self.bgid = 2
        self.mouse = False

        self.outputs = []
        self.final = None

        self.imageAlpha = 0.3

        MyPushButton.setWidget(self)
        self.initImageLayout()
        self.initToolLayout()
        self.initAlphaSliderLayout()
        self.initToolLeftGridLayout()
        self.initToolRightGridLayout()

        # self.setImageAlpha(self.imageAlpha)
        self.setFiller(self.filler.getTheta())
        self.setPen(5)
        self.trimapButtonGroup.button(1).setChecked(True)
        self.backgroundButtonGroup.button(0).setChecked(True)

        self.mainLayout = QVBoxLayout()
        imageBoxLayout = QHBoxLayout()
        imageBoxLayout.addWidget(self.vboxAlphaBox)
        imageBoxLayout.addWidget(self.hImageGroupBox)
        self.mainLayout.addLayout(imageBoxLayout)
        toolBoxLayout = QHBoxLayout()
        toolBoxLayout.addWidget(self.toolLeftGridGroupBox)
        toolBoxLayout.addWidget(self.toolRightGridGroupBox)
        self.mainLayout.addLayout(toolBoxLayout)
        # self.mainLayout.addLayout(self.toolLayout)

        self.setLayout(self.mainLayout)


def initialWidget(*args):
    # inp = ImageInputs(inputList)
    app = QApplication(sys.argv)

    widget = MyWidget(functions=args)
    # widget.resize(800, 600)
    widget.show()

    t = app.exec_()
    sys.exit(t)

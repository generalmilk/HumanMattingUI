import sys
import json
import os
import numpy as np
import cv2
import tkinter.messagebox

from PySide2.QtWidgets import (QApplication, QVBoxLayout, QWidget,
                               QHBoxLayout, QSlider, QFileDialog, QMessageBox)
from PySide2.QtCore import Slot, Qt, QSize
from PySide2.QtGui import QPixmap, QImage, QCursor, QFont, QIcon

from widgets import MyPushButton, ClickLabel, MySlider, MyButtonGroup, MyRadioButton
from utils import numpytoPixmap, ImageInputs, addBlankToLayout
from matting.solve_foreground_background import solve_foreground_background
import tools
import config

import algorithm


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
        if self.final is None:
            self.setImage(-1)
        else:
            alpha = self.final.mean(axis=2) / 255.0
            show = self.changeBackground(alpha)
            self.setImage(-1, array=show, resize=True, grid=self.gridFlag)

    def setSet(self):
        self.setImage(0, array=self.image)
        self.setImage(1, array=self.trimap)
        show = self.image * (1 - self.imageAlpha) + self.trimap * self.imageAlpha
        self.setImage(2, array=show)

    def changeBG(self, bgid):
        # self.bgid += 1
        self.bgid = bgid
        self.background = config.getBackground(self.rawSize[::-1], self.bgid)
        QApplication.processEvents()
        self.setFinal()

    def changeBackground(self, alpha):
        image, trimap = self.resizeToNormal()
        F, B = solve_foreground_background(image, alpha)
        F = F * (F >= 0)
        F = 255 * (F > 255) + F * (F <= 255)
        self.foreground = F
        alpha = np.stack([alpha] * 3, axis=2)
        show = F * alpha + (1 - alpha) * self.background
        return show

    def setResult(self):
        return
        for i, output in enumerate(self.outputs):
            alpha = output.mean(axis=2) / 255.0
            show = self.changeBackground(alpha)
            self.setImage(i + 3, array=show, resize=True, grid=self.gridFlag)

    def open(self):
        list_file = QFileDialog.getExistingDirectory(self, 'open dir', '.')
        self.imageList = ImageInputs(list_file)
        self.saveStatus=1
        self.newSet()
        self.setImageAlpha(self.imageAlpha)

    def newSet(self, prev=False):
        for text in self.texts:
            text.setPixmap(None)
        if prev:
            self.image, self.trimap, self.final, self.imgName, self.nowTriExist = self.imageList.previous()
        else:
            self.image, self.trimap, self.final, self.imgName, self.nowTriExist = self.imageList()
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
        if self.nowTriExist:
            self.run()
        self.setSet()
        self.setFinal()
        self.getGradient()
        self.setWindowTitle(self.imgName)
        self.saveStatus = 0
        QApplication.processEvents()


    def popup(self):
        if self.saveStatus==1:
            self.newSet()
        else:
            answer = QMessageBox.information(self, "", "Are you sure don't save it？", QMessageBox.Yes,QMessageBox.No)
            if answer == QMessageBox.Yes:
                self.saveStatus = 1
                self.newSet()
            else:
                self.saveStatus = 0

    def getGradient(self):
        self.grad = algorithm.calcGradient(self.image)

    def resizeToNormal(self):
        f = 1 / self.f
        # image = cv2.resize(self.image, self.rawSize)
        image = self.rawImage
        trimap = cv2.resize(self.trimap, self.rawSize)
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
        QApplication.processEvents()

    def showGrid(self):
        self.gridFlag = not self.gridFlag
        QApplication.processEvents()

    def setImageAlpha(self, num):
        self.imageAlpha = num
        self.setSet()
        self.imageAlphaSlider.setValue(num)
        QApplication.processEvents()

    def setFiller(self, num):
        self.filler.setTheta(num)
        self.fillerSlider.setValue(num)

        if self.lastCommand == "Filler":
            # self.undo()
            self.lastCommand = None
            if len(self.history) > 0:
                self.reHistory.append(self.trimap)
                self.trimap = self.history.pop()
                self.setSet()
            self.tool.refill()
            # QApplication.processEvents()

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
        QApplication.processEvents()

    def unknownDown(self):
        if self.lastCommand != "FillUnknown":
            return

        if self.fillWidth == 1:
            return

        self.undo()
        self.fillWidth -= 1
        self.fillUnknown(True)
        QApplication.processEvents()

    def fillUnknown(self, refill=False):
        self.setHistory("FillUnknown")
        self.trimap = algorithm.fillUnknown(self.trimap, width=self.fillWidth)
        QApplication.processEvents()

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
        # self.imageList.saveAlpha(self.final)
        self.imageList.saveBoth(self.final, self.foreground)
        self.save()
        self.saveStatus = 1
        QMessageBox.information(self, "", "sucess", QMessageBox.Yes)

    def run(self):
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
            # if id > 2 and id < self.n or id == -1:
            #     return self.resultTool.setId(id)

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
        # if toolName == "Filler":
        #     self.setColor("Background")
        # if toolName == "Pen":
        #     self.setColor("Unknown")
        assert self.tool.toolName == toolName, toolName + " mapping wrong object"

    def initImageLayout(self):
        imgx, imgy = self.scale
        self.texts = []
        for i in range(3):
            text = ClickLabel(self, i, "None")
            text.setAlignment(Qt.AlignTop)
            text.setFixedSize(QSize(imgx, imgy))
            self.texts.append(text)

        # for i, f in enumerate(self.functions):
        #     text = ClickLabel(self, i + 3, "")
        #     text.setAlignment(Qt.AlignTop)
        #     text.setFixedSize(QSize(imgx, imgy))
        #     self.texts.append(text)

        text = ClickLabel(self, -1, "")
        text.setAlignment(Qt.AlignTop)
        text.setFixedSize(QSize(imgx, imgy))
        self.texts.append(text)

        # self.newSet()

        texts = self.texts[:3] + self.texts[-1:]

        row = config.imgRow
        col = (len(texts) + row - 1) // row

        self.imageLayout = QVBoxLayout()
        for i in range(row):
            rowLayout = QHBoxLayout()
            for j in texts[i * col: (i + 1) * col]:
                rowLayout.addWidget(j)
            self.imageLayout.addLayout(rowLayout)

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
        elif command == 'Checkerboard&Red&Green&Blue':
            self.backgroundButtonGroup = obj

    def initToolLayout(self):
        bx, by = self.buttonScale
        bC = self.buttonCol
        blankSize = self.blankSize
        self.toolWidgets = []
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
                            temp = MyRadioButton(self, subCommand)
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

        self.toolLayout = QVBoxLayout()
        self.toolLayout.setAlignment(Qt.AlignTop)
        for line in self.toolWidgets:
            bR = (len(line) - 1) // bC + 1

            for row in range(bR):
                lineLayout = QHBoxLayout()
                lineLayout.setAlignment(Qt.AlignLeft)

                for tool in line[row * bC: (row + 1) * bC]:
                    if tool is not None:
                        singleToolLayout = QVBoxLayout()
                        for obj in tool:
                            if obj is not None:
                                singleToolLayout.addWidget(obj)
                        lineLayout.addLayout(singleToolLayout)
                self.toolLayout.addLayout(lineLayout)
                addBlankToLayout(self.toolLayout, blankSize[0])

            addBlankToLayout(self.toolLayout, blankSize[1])

    def __init__(self, functions):
        QWidget.__init__(self)

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
        # self.resultTool = tools.Concater()
        self.gridFlag = False
        self.imgName = 'None'
        self.fillWidth = 5

        self.bgid = 0

        self.outputs = []
        self.final = None

        self.imageAlpha = 0.3

        MyPushButton.setWidget(self)
        self.initImageLayout()
        self.initToolLayout()

        # self.setImageAlpha(self.imageAlpha)
        self.setFiller(self.filler.getTheta())
        self.setPen(5)
        self.trimapButtonGroup.button(1).setChecked(True)
        self.backgroundButtonGroup.button(0).setChecked(True)

        self.mainLayout = QHBoxLayout()
        self.mainLayout.addLayout(self.imageLayout)
        self.mainLayout.addLayout(self.toolLayout)

        self.setLayout(self.mainLayout)


def initialWidget(*args):
    app = QApplication(sys.argv)
    widget = MyWidget(functions=args)
    widget.show()

    t = app.exec_()
    sys.exit(t)

from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
	QPushButton, QRadioButton, QButtonGroup, QDialog)
from PySide2.QtCore import Qt, QSize
from widgets import BtnLabel
from PySide2.QtGui import QCursor
import cv2
import numpy as np
import config
from utils import numpytoPixmap


class SelectDialog(QDialog):
	def __init__(self,widget,image, imageResult):
		super(SelectDialog, self).__init__()
		self.widget = widget
		self.image = image.copy()
		self.candidateResults = imageResult
		labelW = 200 #控制图片大小
		h, w = self.image.shape[:2]
		if w > labelW:
			ratio = float(labelW) / float(w)
		else:
			labelW = w
			ratio = 1
		labelH = int(h * ratio)
		self.image = cv2.resize(self.image, (labelW, labelH),cv2.INTER_NEAREST)
		for i in range(len(self.candidateResults)):
			self.candidateResults[i] = cv2.resize(self.candidateResults[i], (labelW, labelH))
		# self.resize(labelW * 3 + 150, 800)
		#设置图片宽高结束
		# self.selectTrue = False
		self.Vlayout = QVBoxLayout() #整体布局
		self.Vlayout.setAlignment(Qt.AlignCenter)
		image_label = QLabel()
		image_label.setFixedSize(QSize(labelW, labelH))
		image_label.setPixmap(numpytoPixmap(self.image))
		size = self.image.shape[:2]
		self.firstImageLayout = QHBoxLayout() #原图的布局
		self.firstImageLayout.addWidget(image_label)
		self.Vlayout.addLayout(self.firstImageLayout) #插入原图布局
		self.buttonGroup = QButtonGroup()
		id = 0
		self.resultLayout = QHBoxLayout() #四个结果图的布局
		self.selectAlphas = []
		for i,alpha in enumerate(self.candidateResults):
			bg = config.getBackground(size,2)
			b,g,r,a = cv2.split(alpha)
			bgr = np.stack([b,g,r], axis=2)
			a = np.stack([a] * 3, axis=2)/255.0
			alpha = self.changeBackground(bgr,a,bg)
			self.selectAlphas.append([bgr,a])
			final_label = BtnLabel(self,i)  # 自动以Label类
			final_label.setFixedSize(QSize(labelW, labelH))
			final_label.setPixmap(numpytoPixmap(alpha))
			final_label.setCursor(QCursor(Qt.PointingHandCursor))
			radioButton = QRadioButton(str(id))  # 创建单选按钮
			self.buttonGroup.addButton(radioButton, id)
			id += 1
			self.Hlayout = QVBoxLayout()  # 一张图和一个radio的布局
			self.Hlayout.addWidget(final_label)
			self.Hlayout.addWidget(radioButton)
			self.resultLayout.addLayout(self.Hlayout)

		self.Vlayout.addLayout(self.resultLayout)  # 插入四个结果布局

		self.abandonlayout = QHBoxLayout() #放弃按钮布局
		abandonButton = BtnLabel(self,5)
		abandonButton.setFixedWidth(200)
		abandonButton.setStyleSheet("QPushButton{color:black;font-size:18px;}"
								 "QPushButton{width:200}"
                                 "QPushButton:hover{background-color:#871926}"
                                 "QPushButton{background-color:#871926;}"
                                 "QPushButton{border:2px}"
                                 "QPushButton{border-radius:4px}"
                                 "QPushButton{padding:2px 4px}")
		# abandonButton.clicked.connect(self.abandonClick)
		self.abandonlayout.addWidget(abandonButton)
		self.Vlayout.addLayout(self.abandonlayout)

		self.setLayout(self.Vlayout)

		self.buttonGroup.button(0).setChecked(True)

	#放弃
	# def abandonClick(self):
	# 	self.widget.abandon()
	# 	self.close()

	def abandonClick(self,i):
		self.selectId = i
		# self.selectAlpha = self.selectAlphas[self.selectId]
		self.selectTrue = True
		self.accept()


	def selectImg(self,i):
		self.selectId = i
		if self.selectId <=3:
			self.selectAlpha = self.selectAlphas[self.selectId]
			self.selectTrue = True
			self.accept()
		else:
			self.selectAlpha = self.selectAlphas[0]
			self.accept()
			# self.widget.newSet()




	def changeBackground(self,bgr,alpha,background):
		show = bgr * alpha + (1 - alpha) * background
		return show

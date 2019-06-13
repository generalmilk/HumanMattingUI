from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
	QPushButton, QRadioButton, QButtonGroup, QDialog)
from PySide2.QtCore import Qt, QSize
import cv2
from matting.solve_foreground_background import solve_foreground_background
import numpy as np

from utils import numpytoPixmap
import config


class SelectDialog(QDialog):
	def __init__(self, image, trimaps,images):
		super(SelectDialog, self).__init__()

		self.image = image.copy()
		# self.candidateTrimaps = []
		self.candidateResults = []
		for image in images:
			# self.candidateTrimaps.append(image)
			self.candidateResults.append(image)
		labelW = 200 #控制图片大小
		h, w = self.image.shape[:2]
		if w > labelW:
			ratio = float(labelW) / float(w)
		else:
			labelW = w
			ratio = 1
		labelH = int(h * ratio)
		self.image = cv2.resize(self.image, (labelW, labelH))
		for i in range(len(self.candidateResults)):
			self.candidateResults[i] = cv2.resize(self.candidateResults[i], (labelW, labelH), interpolation=cv2.INTER_NEAREST)
		self.resize(labelW * 3 + 150, 800)
		#设置图片宽高结束


		widget = QWidget()
		self.Vlayout = QVBoxLayout() #整体布局
		self.Vlayout.setAlignment(Qt.AlignCenter)
		image_label = QLabel()
		image_label.setFixedSize(QSize(labelW, labelH))
		image_label.setPixmap(numpytoPixmap(self.image))

		self.firstImageLayout = QHBoxLayout() #原图的布局
		self.firstImageLayout.addWidget(image_label)
		self.Vlayout.addLayout(self.firstImageLayout) #插入原图布局
		self.buttonGroup = QButtonGroup()
		id = 0
		self.resultLayout = QHBoxLayout() #四个结果图的布局
		for i,result in enumerate(self.candidateResults):
			# foreground = self.changeBackground1(result,self.image)
			# result = self.saveBoth1(result, trimaps[i])
			image_label = QLabel()
			image_label.setFixedSize(QSize(labelW, labelH))
			image_label.setPixmap(numpytoPixmap(self.image))
			final_label = QLabel()
			final_label.setFixedSize(QSize(labelW, labelH))
			final_label.setPixmap(numpytoPixmap(result))
			radioButton = QRadioButton(str(id)) # 创建单选按钮
			self.buttonGroup.addButton(radioButton, id)
			id += 1
			self.Hlayout = QVBoxLayout() #一张图和一个radio的布局
			self.Hlayout.addWidget(final_label)
			self.Hlayout.addWidget(radioButton)
			self.resultLayout.addLayout(self.Hlayout)

		self.Vlayout.addLayout(self.resultLayout) #插入四个结果布局

		#控制ok按钮逻辑
		self.button = QPushButton('OK')
		self.button.setFixedSize(QSize(100, 50))
		self.button.clicked.connect(self.select)
		self.btnLayout = QHBoxLayout()
		self.btnLayout.setAlignment(Qt.AlignCenter)
		self.btnLayout.addWidget(self.button)


		self.Vlayout.addLayout(self.btnLayout) #插入按钮布局

		# scrollArea = QScrollArea()
		# scrollArea.setWidget(widget)
		# layout = QVBoxLayout(self)
		# layout.addWidget(scrollArea)
		self.setLayout(self.Vlayout)




		self.buttonGroup.button(0).setChecked(True)
		self.selectId = 0

	def select(self):
		self.selectId = self.buttonGroup.checkedId()
		self.accept()

	def saveBoth1(self, alpha, foreground):
		b_channel, g_channel, r_channel = cv2.split(foreground)
		a_channel = alpha.mean(axis=2)
		img_bgra = cv2.merge((b_channel, g_channel, r_channel, a_channel))
		return img_bgra

	# def changeBackground1(self, alpha,image):
	# 	F, B = solve_foreground_background(image, alpha)
	# 	F = F * (F >= 0)
	# 	foreground = 255 * (F > 255) + F * (F <= 255)
	# 	return foreground

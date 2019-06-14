from PySide2.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea,
	QPushButton, QRadioButton, QButtonGroup, QDialog)
from PySide2.QtCore import Qt, QSize
import cv2
import numpy as np
import config

from utils import numpytoPixmap


class SelectDialog(QDialog):
	def __init__(self, image,imageResult):
		super(SelectDialog, self).__init__()

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
		self.resize(labelW * 3 + 150, 800)
		#设置图片宽高结束


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
		for i,alpha in enumerate(self.candidateResults):
			bg = config.getBackground(size,0)
			b,g,r,a = cv2.split(alpha)
			bgr = np.stack([b,g,r], axis=2)
			a = np.stack([a] * 3, axis=2)/255.0
			alpha = self.changeBackground(bgr,a,bg)

			final_label = QLabel()
			final_label.setFixedSize(QSize(labelW, labelH))
			final_label.setPixmap(numpytoPixmap(alpha))
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

		self.setLayout(self.Vlayout)

		self.buttonGroup.button(0).setChecked(True)
		self.selectId = 0

	def select(self):
		self.selectId = self.buttonGroup.checkedId()
		self.accept()


	def changeBackground(self,bgr,alpha,background):
		show = bgr * alpha + (1 - alpha) * background
		return show

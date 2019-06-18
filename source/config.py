import numpy as np

from tools import painterTools

painterColors = {'Foreground':  (255, 255, 255),
                 'Background':  (0, 0, 0),
                 'Unknown':     (128, 128, 128)}

buttonString = \
'''Foreground&Background&Unknown=
Pen * PenSlider-
Filler * FillerSlider-
SolveForeground Undo Redo
FillUnknown UnknownUp UnknownDown
Grid&Red&Green&Blue=
Open Previous Submit Abandon Run #Save SaveAlpha'''

# SplitUp|SplitDown ShowGrid UndoAlpha
buttonKeys = [[tool.split('|') for tool in block.split(' ')] for block in buttonString.split('\n')]
commandText = {
    'Top': '0%',
    'Bottom': '100%',
    'SaveAlpha': 'Save',
    'Save': 'Save Trimap',
    'FillUnknown': '填充未知区',
    'FillerUpTen': 'Filler+10',
    'FillerDownTen': 'Filler-10',
    'UnknownUp': '扩大未知',
    'UnknownDown': '缩小未知',
    'SplitUp': 'Split Up',
    'SplitDown': 'Split Down',
    'ShowGrid': 'Show Grid',
    'UndoAlpha': 'Undo Alpha',
    'SolveForeground': '清除蒙版',
    'ChangeBG': 'Change Background',
    'Undo':'上一步',
    'Redo':'下一步',
    'Pen':'笔',
    'Filler':'油漆桶',
    'Run':'运行',
    'Open':'打开文件',
    'Previous':'上一张',
    'Submit':'提交',
    'Abandon':'放弃修改',

    }

# 渲染按钮对应 text
def getText(command):
    if command not in commandText:
        return command
    return commandText[command]

sliderConfig = {
    "ImageAlphaSlider":     (0, 1, "continuous"), #连续
    "FillerSlider":         (1, 250, "log"),
    "PenSlider":     (1, 21, "discrete") #离散
}


toolKeys = list(painterTools.keys())
toolKeys.sort()
colorKeys = list(painterColors.keys())
colorKeys.sort()

toolTexts = buttonKeys

# 按钮间距
blankSize = [10, 15]
defaultBlank = 5

for i in range(len(blankSize) - 1)[::-1]:
    blankSize[i + 1] -= blankSize[i]
buttonScale = (120, 40)
buttonCol = 3

imgScale = (300, 300)
imgRow = 1

defaultSplit = 3

GridBG = np.ones([20, 20, 3]).astype("uint8") * 255
GridBG[:10, :10] = 128
GridBG[10:, 10:] = 128
blueBG = np.array([[[255, 0, 0]]])
greenBG = np.array([[[0, 255, 0]]])
redBG = np.array([[[0, 0, 255]]])

backgrounds = [GridBG, redBG, greenBG, blueBG]

def getBackground(size, background = 2):
    background = background % len(backgrounds)
    background = backgrounds[background]
    bh, bw = background.shape[:2]
    h, w = size[:2]
    dh = h // bh + 10
    dw = w // bw + 10
    line = np.concatenate([background] * dw, axis = 1)
    bg = np.concatenate([line] * dh, axis = 0)[:h, :w]
    return bg

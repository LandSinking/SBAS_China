from __future__ import absolute_import
from logging import exception

import sys
import numpy as np

from datetime import date
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.dates as mdt
from math import ceil
import pandas as pd
import argparse
import importlib
from pathlib import Path
import asf_search as asf
from tqdm import tqdm, trange

#===================Global variables===========================

flagAdd = False  # Add line or remove line
flagPair = False  # first point or second point

selectedArtist = []
labeledPoint = []
idx = -1

textPLT = None
currColor = 'deepskyblue'
pair = [-1, -1]
totalPairs = set()

#======================Functions===============================


# Filter the image list according to the accquire year: [minyear, maxyear)
def yearFilter(fileList, minYear, maxYear):
    if not (isinstance(minYear, int) & (isinstance(maxYear, int))):
        print('yearFilter is skipped beacuse the input range is not INT.')
        return fileList
    
    len1,len2=len(str(minYear)),len(str(maxYear))
    if len1!=len2:
        print('yearFilter is skipped beacuse the len(minYear)!=len(maxYear)')
        return fileList    
    accquireTime = np.array([int(x[17:(17+len1)]) for x in fileList])
    index = (minYear <= accquireTime) & (accquireTime < maxYear)
    return fileList[index]
    
        


# get frame ID for SIA images based on the ASF api: https://api.daac.asf.alaska.edu/services/search/param
def getFrame(inputList):       
    result = []    
    tempList=[]
    metadata = asf.search(granule_list=inputList.tolist(),processingLevel='SLC')    
    print(len(metadata))
    for x in metadata:        
        tempList.append(x.properties['sceneName'])
        result.append(x.properties['frameNumber'])
    return np.array(tempList),np.array(result)
    
# Filter the image list according to the frame: [minFrame, maxFrame)
def frameFilter(inputList, minFrame, maxFrame):
    if isinstance(minFrame, int) & (isinstance(maxFrame, int)):
        newList,imgFrame = getFrame(inputList)
        index = (minFrame <= imgFrame) & (imgFrame < maxFrame)
        return newList[index]
    else:
        print('frameFilter is skipped beacuse the input range is not INT.')
        return inputList


def getPlotXY(fileList, data):
    masterList = data[:,0]
    value = data[:,4]
    
    # np.array([int(x[17:21]) for x in masterList])
    dates = np.zeros(fileList.shape, dtype=int)
    baseline = np.zeros(fileList.shape, dtype=int)

    for i, currFile in enumerate(fileList):
        tempDate = date(int(currFile[17:21]), int(currFile[21:23]), int(currFile[23:25]))
        dates[i] = mdt.date2num(tempDate)
        tempIdx = np.where(masterList == currFile)[0]
        if tempIdx.size != 0:
            baseline[i] = value[tempIdx[0]]

    return dates, baseline


def getInitPairs(fileList, masterList, slaveList):
    pairs = set()
    for i in range(masterList.shape[0]):
        firstPair = np.where(fileList == masterList[i])[0]
        secondPair = np.where(fileList == slaveList[i])[0]
        if (firstPair.size != 0) and (secondPair.size != 0):
            tempPair = (firstPair[0], secondPair[0]) if firstPair[0] < secondPair[0] else (secondPair[0], firstPair[0])
            pairs.add(tempPair)
    return pairs


def OnBtnAddEvent(event):
    global flagAdd, flagPair, selectedArtist
    flagAdd = True
    flagPair = False
    if selectedArtist:
        selectedArtist[0].set_color(currColor)
        selectedArtist.clear()


def OnBtnRmEvent(event):
    global flagAdd
    flagAdd = False


def onPickEvent(event):
    global currColor
    if flagAdd:
        return
    if isinstance(event.artist, Line2D):
        thisline = event.artist
        if selectedArtist:
            if not thisline in selectedArtist:
                for tempLine in selectedArtist:
                    tempLine.set_color(currColor)
                thisline.set_color('r')
                selectedArtist.clear()
                selectedArtist.append(thisline)
            else:
                for tempLine in selectedArtist:
                    tempLine.set_color(currColor)
                selectedArtist.clear()
        else:
            selectedArtist.append(thisline)
            currColor = thisline.get_color()
            thisline.set_color('r')

        fig.canvas.draw()
        xdata = thisline.get_xdata()
        # ydata = thisline.get_ydata()
        print('pick line:', [mdt.num2date(xd).strftime('%Y-%m-%d') for xd in xdata])


def OnDelLineEvent(event):
    if event.key == 'delete' and selectedArtist:
        xdata = selectedArtist[0].get_xdata()
        ydata = selectedArtist[0].get_ydata()
        selectedArtist[0].remove()
        selectedArtist.clear()
        fig.canvas.draw()
        firstIdx = np.where((dates == xdata[0]) & (baseline == ydata[0]))[0][0]
        secondIdx = np.where((dates == xdata[1]) & (baseline == ydata[1]))[0][0]

        tempPair = (firstIdx, secondIdx) if firstIdx < secondIdx else (secondIdx, firstIdx)
        totalPairs.remove(tuple(tempPair))
        # print('delete:', tempPair)
        print('delete line:', [mdt.num2date(xd).strftime('%Y-%m-%d') for xd in xdata], ', remain pairs:',
              len(totalPairs))


def OnMouseEvent(event):
    global idx, pair, flagPair, flagAdd

    if (event.inaxes == None) or not flagAdd:
        return
    pair[int(flagPair)] = idx
    flagPair = not (flagPair)
    if not flagPair:  # add new Line
        pair.sort()
        tempPair = tuple(pair)
        if pair[0] != pair[1] and (tempPair not in totalPairs):
            totalPairs.add(tempPair)
            x0, y0 = dates[pair[0]], baseline[pair[0]]
            x1, y1 = dates[pair[1]], baseline[pair[1]]
            ax.plot_date((x0, x1), (y0, y1), 'orange', picker=True)
            ax.plot_date(x0, y0, c='green')
            ax.plot_date(x1, y1, c='green')
            pair = [-1, -1]
            # print(totalPairs)
            x0 = mdt.num2date(x0).strftime('%Y-%m-%d')
            x1 = mdt.num2date(x1).strftime('%Y-%m-%d')
            print('add Pairs:', [x0, x1], ', number of pairs:', len(totalPairs))


def mouseMoveEvent(event):
    global labeledPoint, idx, textPLT
    if event.inaxes == None:
        return

    xdist = dates - event.xdata
    ydist = baseline - event.ydata
    dist = xdist * xdist + ydist * ydist
    minDist = dist.min()
    idx = np.where(dist == minDist)[0][0]
    if minDist <= 4:
        if labeledPoint and (labeledPoint[0] != idx):
            prevIdx = labeledPoint[0]
            ptX = dates[prevIdx]
            ptY = baseline[prevIdx]
            ax.plot_date(ptX, ptY, c='green')
            labeledPoint.clear()
        if textPLT:
            textPLT.remove()

        labeledPoint.append(idx)
        ax.plot_date(dates[idx], baseline[idx], c='red')
        tempLabel = mdt.num2date(dates[idx]).strftime('%Y-%m-%d')
        textPLT = ax.text(dates[idx], baseline[idx], tempLabel, fontsize=11)
        fig.canvas.draw()
    else:
        if labeledPoint:
            idx = labeledPoint[0]
            ax.plot_date(dates[idx], baseline[idx], c='green')
            labeledPoint.clear()
        if textPLT:
            textPLT.remove()
            textPLT = None
        fig.canvas.draw()


#==========================processing========================================

# parsing
parser = argparse.ArgumentParser(description='Acquire some parameters for fusion restore')
parser.add_argument('-c', '--config', required=True, help='path to config file (*.py)')
opt = parser.parse_args()

# read the configFile
configFile = Path(opt.config)
sys.path.append(str(configFile.parent))
setting = importlib.import_module(configFile.stem)

startYear, endYear = setting.startYear, setting.endYear
startFrame, endFrame = setting.startFrame, setting.endFrame
fnInitPairs, fnFinalPairs = setting.fnInitPairs, setting.fnFinalPairs
figPairs = setting.figPairs
# read the csvFile
if not fnInitPairs.exists():
    print('\033[1;31;40mError: csvFile does not exist! \033[0m')
    exit(1)
# df = pd.read_csv(fnInitPairs)
fileID= open(fnInitPairs,encoding='utf-8')
data=np.loadtxt(fileID,str,delimiter=',',skiprows=1)
# Apply yearFilter and frameFilter
print('\033[1;32;40mFilter... \033[0m')
# masterList, slaveList = df['Reference'].values, df[' Secondary'].values
masterList, slaveList =data[:,0],data[:,2]

fileList = np.unique(np.concatenate((masterList, slaveList)))

fileList = yearFilter(fileList, startYear, endYear)
fileList = frameFilter(fileList, startFrame, endFrame)

dates, baseline = getPlotXY(fileList, data)
totalPairs = getInitPairs(fileList, masterList, slaveList)
print(f'\033[1;32;40m{len(totalPairs)} pairs remain... \033[0m')

fig, ax = plt.subplots(figsize=(15, 5))
ax.xaxis.set_major_formatter(mdt.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_minor_locator(mdt.MonthLocator())
ax.tick_params(axis='both', direction='out', labelsize=10)

for i in range(dates.shape[0]):
    ax.plot(dates[i], baseline[i], c='green')  # , picker=point_picker

for currPair in totalPairs:
    x0, y0 = dates[currPair[0]], baseline[currPair[0]]
    x1, y1 = dates[currPair[1]], baseline[currPair[1]]
    ax.plot((x0, x1), (y0, y1), 'deepskyblue', picker=True)
fig.autofmt_xdate()

btnAdd = plt.Button(plt.axes([0.125, 0.9, 0.1, 0.06]), 'Add pairs', hovercolor='y')
btnAdd.on_clicked(OnBtnAddEvent)
btnRemove = plt.Button(plt.axes([0.25, 0.9, 0.1, 0.06]), 'Remove pairs', hovercolor='y')
btnRemove.on_clicked(OnBtnRmEvent)

fig.canvas.mpl_connect('motion_notify_event', mouseMoveEvent)
fig.canvas.mpl_connect('button_press_event', OnMouseEvent)
fig.canvas.mpl_connect('key_press_event', OnDelLineEvent)
fig.canvas.mpl_connect('pick_event', onPickEvent)

plt.show()
fig.savefig(figPairs, dpi=300, bbox_inches='tight')
print(f'\033[1;32;40mImage saved to {figPairs}. \033[0m')
# After modification
masterList = []
slaveList = []
bline = []
for currPair in totalPairs:
    file0, file1 = fileList[currPair[0]], fileList[currPair[1]]
    tempLine = baseline[currPair[0]]

    if int(file0[17:25]) > int(file1[17:25]):
        file0, file1 = file1, file0
        tempLine = baseline[currPair[1]]
    masterList.append(file0)
    slaveList.append(file1)
    bline.append(tempLine)
masterList = np.array(masterList)
slaveList = np.array(slaveList)
bline = np.array(bline)
temp=np.zeros_like(masterList,dtype=np.int8)
outputDF = pd.DataFrame({
    'Reference': masterList,
    'ABC':temp,
    'Secondary': slaveList,
    'XYZ':temp,
    'Baseline': bline
})
outputDF.to_csv(fnFinalPairs, index=False)

print(f'\033[1;32;40mModified {masterList.shape[0]} pairs saved to {fnFinalPairs}. \033[0m')

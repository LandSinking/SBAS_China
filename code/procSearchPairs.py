import asf_search as asf
import pandas as pd
from dateutil.parser import parse as parse_date
from datetime import date
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.dates as mdt
from math import ceil
import pandas as pd
import argparse
import importlib
import numpy as np
from pathlib import Path
import asf_search as asf
from tqdm import tqdm, trange
import sys


# parsing
parser = argparse.ArgumentParser(description='Acquire some parameters for fusion restore')
parser.add_argument('-c', '--config', required=True, help='path to config file (*.py)')
parser.add_argument('-t', '--time_interval', default=64, type=int, help='max temporal baseline (days)')
opt = parser.parse_args()
max_temporal_baseline = opt.time_interval  #days
configFile = Path(opt.config)

# load config file
sys.path.append(str(configFile.parent))
setting = importlib.import_module(configFile.stem)
baseImage= setting.baseImage
figPairs = setting.figPairs
auxRoot =setting.auxRoot
postfix = setting.postfix
frame_start=setting.startFrame
frame_end=setting.endFrame
datestr="20140101"
stack_start=parse_date(datestr.replace(datestr[:len(str(setting.startYear))],str(setting.startYear)))
stack_end=parse_date(datestr.replace(datestr[:len(str(setting.endYear))],str(setting.endYear)))


# call ASF API to search for products
granules=asf.granule_search(baseImage)
searchResults = asf.baseline_search.stack_from_product(granules[0])
columns = list(searchResults[0].properties.keys()) + ['geometry', ] # add geometry column for spatial filtering
data = [list(scene.properties.values()) + [scene.geometry, ] for scene in searchResults]

# filter the products by temporal and frame criteria
stack = pd.DataFrame(data, columns=columns)
stack['startTime'] = stack.startTime.apply(parse_date)
stack = stack.loc[(stack_start <= stack.startTime) & (stack.startTime <= stack_end)]
stack = stack.loc[(frame_start <= stack.frameNumber) & (stack.frameNumber < frame_end)]
scenes=stack['sceneName'].drop_duplicates().values.tolist()

# get the X (date) and Y (spatial baseline) coordinates of each scene for plotting
dates = np.zeros(len(scenes), dtype=int) 
for i, currScene in enumerate(scenes):    
    tempDate = date(int(currScene[17:21]), int(currScene[21:23]), int(currScene[23:25]))
    dates[i] = mdt.date2num(tempDate)
baseline=np.nan_to_num(stack['perpendicularBaseline'].values,nan=0).astype(np.int32) 

# create pairs for the filtered scenes
totalPairs = set() # record the pairs of scene indices to be processed
for reference, rt in stack.loc[::-1, ['sceneName', 'temporalBaseline']].itertuples(index=False):
    secondaries = stack.loc[
        (stack.sceneName != reference)
        & (stack.temporalBaseline - rt <= max_temporal_baseline)
        & (stack.temporalBaseline - rt > 0)
    ]
    for secondary in secondaries.sceneName:
        indexFirstPair=scenes.index(reference)
        indexSecondPair=scenes.index(secondary)
        totalPairs.add((indexFirstPair,indexSecondPair))

# save the initial pairs to a csv file
masterList = np.array([scenes[currPair[0]] for currPair in totalPairs])
slaveList = np.array([scenes[currPair[1]] for currPair in totalPairs])
bline=np.array([baseline[currPair[0]] for currPair in totalPairs])
temp=np.zeros_like(masterList,dtype=np.int8)
print('masterList:', masterList.shape, 'bline:', bline.shape)

outputDF = pd.DataFrame({
    'Reference': masterList,
    'ABC':temp,
    'Secondary': slaveList,
    'XYZ':temp,
    'Baseline': bline
})
fnInitPairs = auxRoot.parent / f'{postfix}_init_pairs.csv'
outputDF.to_csv(fnInitPairs, index=False)

# logging the results for debugging purposes
print('columns:', columns)
print('num of scenes:', len(scenes))
temp=stack['frameNumber'].drop_duplicates().values.tolist()
print('frames:', temp)
print(f'\033[1;32;40m{len(totalPairs)} pairs remain... \033[0m')



#====================================== START of plotting ======================================
# plotting the scenes (points) and pairs (lines) for visualization and editing

flagAdd = False  # Add line or remove line
flagPair = False  # first point or second point

selectedLine = None
labeledPoint = []
idx = -1

textPLT = None
defaultLineColor = 'deepskyblue'
selectedLineColor='red'
addedLineColor='orange'
prevLineColor= None

pair = [-1, -1]

def OnBtnAddEvent(event):
    global flagAdd, flagPair, selectedLine
    flagAdd = True
    flagPair = False
    if selectedLine:
        selectedLine.set_color(prevLineColor)
        selectedLine=None
        

def OnBtnRmEvent(event):
    global flagAdd, selectedLine
    flagAdd = False
    if selectedLine:
        selectedLine.set_color(prevLineColor)
        selectedLine=None


def OnPickLineEvent(event):
    global prevLineColor, selectedLine
    if flagAdd:
        return
    if isinstance(event.artist, Line2D):
        thisline = event.artist
        if selectedLine:
            selectedLine.set_color(prevLineColor)
        selectedLine=thisline
        prevLineColor=thisline.get_color()
        thisline.set_color(selectedLineColor)
        fig.canvas.draw()
        xdata = thisline.get_xdata()
        # ydata = thisline.get_ydata()
        print('pick line:', [mdt.num2date(xd).strftime('%Y-%m-%d') for xd in xdata])


def OnDelLineEvent(event):
    global selectedLine
    if event.key == 'delete' and selectedLine:
        xdata = selectedLine.get_xdata()
        ydata = selectedLine.get_ydata()
        selectedLine.remove()
        selectedLine = None
        fig.canvas.draw()
        firstIdx = np.where((dates == xdata[0]) & (baseline == ydata[0]))[0][0]
        secondIdx = np.where((dates == xdata[1]) & (baseline == ydata[1]))[0][0]

        tempPair = (firstIdx, secondIdx) if firstIdx < secondIdx else (secondIdx, firstIdx)
        totalPairs.remove(tuple(tempPair))
        # print('delete:', tempPair)
        print('delete line:', [mdt.num2date(xd).strftime('%Y-%m-%d') for xd in xdata], ', remain pairs:',
              len(totalPairs))


def OnAddLineEvent(event):
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
            ax.plot_date((x0, x1), (y0, y1), addedLineColor, picker=True)
            pair = [-1, -1]
            # print(totalPairs)
            x0 = mdt.num2date(x0).strftime('%Y-%m-%d')
            x1 = mdt.num2date(x1).strftime('%Y-%m-%d')
            print('add Pairs:', [x0, x1], ', number of pairs:', len(totalPairs))


def OnNotifyEvent(event):
    global labeledPoint, idx, textPLT
    if event.inaxes == None:
        return

    xdist = dates - event.xdata
    ydist = baseline - event.ydata
    dist = xdist * xdist + ydist * ydist
    minDist = dist.min()
    idx = np.where(dist == minDist)[0][0]
    if minDist <= 200:
        if labeledPoint and (labeledPoint[0] != idx):
            prevIdx = labeledPoint[0]
            ptX = dates[prevIdx]
            ptY = baseline[prevIdx]
            ax.plot_date(ptX, ptY, c='green', ms=5)
            labeledPoint.clear()
        if textPLT:
            textPLT.remove()

        labeledPoint.append(idx)
        ax.plot_date(dates[idx], baseline[idx], c='red', ms=5)
        tempLabel = mdt.num2date(dates[idx]).strftime('%Y-%m-%d')
        textPLT = ax.text(dates[idx], baseline[idx], tempLabel, fontsize=11)
        fig.canvas.draw()
    else:
        if labeledPoint:
            idx = labeledPoint[0]
            ax.plot_date(dates[idx], baseline[idx], c='green',ms=5)
            labeledPoint.clear()
        if textPLT:
            textPLT.remove()
            textPLT = None
        fig.canvas.draw()


# new plot 
fig, ax = plt.subplots(figsize=(15, 5))
ax.xaxis.set_major_formatter(mdt.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_minor_locator(mdt.MonthLocator())
ax.tick_params(axis='both', direction='out', labelsize=10)

# drawing lines
for currPair in totalPairs:
    x0, y0 = dates[currPair[0]], baseline[currPair[0]]
    x1, y1 = dates[currPair[1]], baseline[currPair[1]]
    ax.plot_date((x0, x1), (y0, y1), defaultLineColor, picker=True)
fig.autofmt_xdate()

# drawing points
for i in range(dates.shape[0]):
    ax.plot_date(dates[i], baseline[i], c='green',ms=5)  # , picker=point_picker

# drawing buttons
btnAdd = plt.Button(plt.axes([0.125, 0.9, 0.1, 0.06]), 'Add pairs', hovercolor='y')
btnAdd.on_clicked(OnBtnAddEvent)
btnRemove = plt.Button(plt.axes([0.25, 0.9, 0.1, 0.06]), 'Remove pairs', hovercolor='y')
btnRemove.on_clicked(OnBtnRmEvent)

# connect events
fig.canvas.mpl_connect('motion_notify_event', OnNotifyEvent)
fig.canvas.mpl_connect('button_press_event', OnAddLineEvent)
fig.canvas.mpl_connect('key_press_event', OnDelLineEvent)
fig.canvas.mpl_connect('pick_event', OnPickLineEvent)

# show plot and allow user to edit pairs
plt.show()

# save the plot as an image
fig.savefig(figPairs, dpi=300, bbox_inches='tight')
print(f'\033[1;32;40mImage saved to {figPairs}. \033[0m')

#========================== END of plotting ==========================


# save the final pairs to a csv file
finalMasterList = []
finalSlaveList = []
finalBline = []
for currPair in totalPairs:
    file0, file1 = scenes[currPair[0]], scenes[currPair[1]]
    tempLine = baseline[currPair[0]]
    if int(file0[17:25]) > int(file1[17:25]):
        file0, file1 = file1, file0
        tempLine = baseline[currPair[1]]
    finalMasterList.append(file0)
    finalSlaveList.append(file1)
    finalBline.append(tempLine)
finalMasterList = np.array(finalMasterList)
finalSlaveList = np.array(finalSlaveList)
finalBline = np.array(finalBline)
temp=np.zeros_like(finalMasterList,dtype=np.int8)
outputDF = pd.DataFrame({
    'Reference': finalMasterList,
    'ABC':temp,
    'Secondary': finalSlaveList,
    'XYZ':temp,
    'Baseline': finalBline
})

fnFinalPairs = auxRoot / f'{postfix}_final_pairs.csv'
outputDF.to_csv(fnFinalPairs, index=False)
print(f'\033[1;32;40mModified {finalMasterList.shape[0]} pairs saved to {fnFinalPairs}. \033[0m')



#  python burstsearch.py -c K:\SBAS\config\CN_XTan.py

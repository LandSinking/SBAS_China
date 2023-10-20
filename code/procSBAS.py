import argparse
import shutil
import os
import sys
import zipfile
import importlib
from pathlib import Path
from mintpy import view, tsview, smallbaselineApp
import load2hdf5
from extractLULC import clipByMask
import osgeo_utils.gdal_calc as gc
from subprocess import run
# load2hdf5.py waterMask.rdr --dtype bool --dname mask -o waterMask.h5
parser = argparse.ArgumentParser(description='Acquire some parameters for fusion restore')
parser.add_argument('-c', '--config', required=True, help='path to config file (*.py)')
parser.add_argument('-l', '--lulcpath', default="",help='path to ESRI LULC files (*0101.tif)')
parser.add_argument('-r', '--restart', action='store_true', help='clear workplace and restart job')
parser.add_argument('-b', '--backup', action='store_true', help='clear workplace and use backup')
opt = parser.parse_args()
print(opt)


configFile = Path(opt.config)
sys.path.append(str(configFile.parent))
setting = importlib.import_module(configFile.stem)

workPath, cfgData, cfgProc = setting.mpyPath, setting.cfgData, setting.cfgProc
'''
STEP_LIST = [
    'load_data',
    'modify_network',
    'reference_point',
    'quick_overview',
    'correct_unwrap_error',
    'invert_network',
    'correct_LOD',
    'correct_SET',
    'correct_troposphere',
    'deramp',
    'correct_topography',
    'residual_RMS',
    'reference_date',
    'velocity',
    'geocode',
    'google_earth',
    'hdfeos5',
]
'''
zippedFiles = [
    'avgPhaseVelocity.h5', 'avgSpatialCoh.h5', 'coherenceSpatialAvg.txt', 'maskConnComp.h5',
    'maskTempCoh.h5', 'numInvIfgram.h5', 'numTriNonzeroIntAmbiguity.h5', 'smallbaselineApp.cfg',
    'temporalCoherence.h5'
]
backupFiles = ['timeseries.h5', 'geometryGeo.h5', 'ifgramStack.h5']
zipFilename = 'ckpt.zip'


def clearWorkplace(workPath):
    def clearfolder(folder):
        if folder.exists():
            try:
                shutil.rmtree(folder)
            except OSError as e:
                print("Error: %s : %s" % (folder, e.strerror))

    clearfolder(workPath / 'inputs')
    clearfolder(workPath / 'pic')

    for currFile in workPath.glob('*.*'):
        currFile.unlink()


def clear_correct_SET(workPath):
    for currFile in workPath.glob('*.*'):
        fn = currFile.name
        if (fn == zipFilename) or (fn in backupFiles) or (currFile.suffix == 'cfg'):
            continue
        else:
            currFile.unlink()

    workPath2 = workPath / 'inputs'
    for currFile in workPath2.glob('*.*'):
        if (currFile.name in backupFiles) or (currFile.suffix == 'cfg'):
            continue
        else:
            currFile.unlink()
    workPath3 = workPath / 'pic'
    if workPath3.exists():
        shutil.rmtree(workPath3)


def zip_correct_SET_files(workPath):
    filePath = Path(zipFilename)
    if filePath.exists():
        filePath.unlink()
    f = zipfile.ZipFile(filePath, 'w', zipfile.ZIP_DEFLATED)
    for currFile in zippedFiles:
        f.write(currFile)
    picPath = workPath / 'pic'
    for currFile in picPath.glob('*.*'):
        f.write(Path('pic') / currFile.name)
    f.close()


if opt.restart:
    clearWorkplace(workPath)

os.chdir(workPath)


if not opt.backup:
    # smallbaselineApp.main([str(cfgData), '--dostep', 'load_data'])
    run(f'smallbaselineApp.py {str(cfgData)} --dostep load_data', shell=True)
    if not opt.lulcpath=="": # create watermask.h5
        lulcFiles = list(Path(opt.lulcpath).glob('*0101.tif'))        
        geometryFile=workPath / 'inputs'/'geometryGeo.h5'
        lulcTiFF =str(configFile).replace('.py', '_lulc.tif')
        watermaskTiFF = str(configFile).replace('.py', '.tif')  
        if  Path(lulcTiFF).exists():
            Path(lulcTiFF).unlink()
        if  Path( watermaskTiFF).exists():
            Path( watermaskTiFF).unlink()
        watermaskH5 = workPath /'waterMask.h5'
        clipByMask(lulcFiles,geometryFile, lulcTiFF)   
        # gdal_calc.py -A input.tif --outfile=result.tif --calc="A*(A>0)" --NoDataValue=0
        # gc.main(['--quiet','-a',lulcTiFF, '--outfile',watermaskTiFF,'--calc', "a>1"])
        # load2hdf5.main([watermaskTiFF, '--dtype', 'byte', '--dname', 'mask', '-o', 'waterMask.h5','--force'])
    # smallbaselineApp.main([str(cfgProc), '--start', 'modify_network', '--stop', 'correct_SET'])
    run(f'smallbaselineApp.py {str(cfgProc)} --start modify_network --stop correct_SET', shell=True)
    zip_correct_SET_files(workPath)
else:
    clear_correct_SET(workPath)
    with zipfile.ZipFile(workPath / zipFilename) as f:
        f.extractall()
        f.close()

# smallbaselineApp.main([str(cfgProc), '--start', 'correct_troposphere'])
run(f'smallbaselineApp.py {str(cfgProc)} --start correct_troposphere', shell=True)
# view SBAS result
# view.main([f'{workPath}/velocity.h5'])
# tsview.main([f'{workPath}/timeseries.h5'])



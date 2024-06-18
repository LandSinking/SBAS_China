import os
import argparse
import zipfile
import glob
from typing import Iterable, Union
from osgeo import ogr, osr, gdal
from pyproj import CRS, Transformer
import pandas as pd
import argparse
import sys
import importlib
from pathlib import Path
from tqdm import trange
from shutil import copyfile
from math import floor,ceil

parser = argparse.ArgumentParser(description='Acquire some parameters')
parser.add_argument('-nu', '--nounzip', action='store_true', help='disable data unzip')
parser.add_argument('-nc', '--noclip', action='store_true', help='disable data clip')
parser.add_argument('-s', '--shapefile', default="", help='specific shapefile for clipping (*.shp)')
parser.add_argument('-c', '--config', required=True, help='path to config file (*.py)')
parser.add_argument('-u', '--unzipPath', default="", help='specific unzip path, will override unzipPath in config file')
opt = parser.parse_args()


def creatDir(inputPath: Union[Path, Iterable[Path]]):
    def creatDirImpl(currPath: Path):
        if not currPath.is_dir():
            currPath.mkdir()
            # print('Create directory: {}'.format(currPath))

    if isinstance(inputPath, Path):
        creatDirImpl(inputPath)
    else:
        for currPath in inputPath:
            creatDirImpl(currPath)

def createUTMshp(minLat, maxLat, minLon, maxLon, shapeName):
    midLon=(minLon+maxLon)/2
    midLat=(minLat+maxLat)/2
    utm_zone=int(midLon//6)+31
    epsg_code=utm_zone + 32600 + (midLat<0)*100    
    
    trans=Transformer.from_crs(CRS.from_epsg(4326),CRS.from_epsg(epsg_code))
    lonArray=[minLon,maxLon,maxLon,minLon]
    latArray=[minLat,minLat,maxLat,maxLat]
    xyCoords=trans.transform(latArray,lonArray)
    minX,maxX=floor(min(xyCoords[0])),ceil(max(xyCoords[0]))
    minY,maxY=floor(min(xyCoords[1])),ceil(max(xyCoords[1]))
    polygon = 'POLYGON((%f %f,%f %f,%f %f,%f %f,%f %f))' % (minX, minY, maxX, minY, maxX,maxY, minX, maxY,minX, minY)
    
    driver = ogr.GetDriverByName("ESRI Shapefile")
    datasource = driver.CreateDataSource(str(shapeName))
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)
    layer = datasource.CreateLayer(shapeName.stem, srs, ogr.wkbPolygon)
    fieldName = ogr.FieldDefn("ID", ogr.OFTString)
    fieldName.SetWidth(24)
    layer.CreateField(fieldName)
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("ID", '0')
    feature.SetGeometry(ogr.CreateGeometryFromWkt(polygon))
    layer.CreateFeature(feature)

def clipByOverlap(inputPath, outputPath):
    files = []
    postfixList = ["*unw_phase.tif", "*corr.tif", "*inc_map_ell.tif","*dem.tif", "*lv_phi.tif","*lv_theta.tif"]
    # postfixList = ["*inc_map_ell.tif","*dem.tif"]
    for dir, _, _ in os.walk(inputPath):
        for postfix in postfixList:
            files.extend(glob.glob(os.path.join(dir, postfix)))
    corners = [gdal.Info(f, format='json')['cornerCoordinates'] for f in files]
    ulx = max(corner['upperLeft'][0] for corner in corners)
    uly = min(corner['upperLeft'][1] for corner in corners)
    lrx = min(corner['lowerRight'][0] for corner in corners)
    lry = max(corner['lowerRight'][1] for corner in corners)

    # subset all input files to these common coordinates
    for fname in files:        
        outfile = fname.replace(".tif", "_clip.tif")
        outfile = outfile.replace(str(inputPath), str(outputPath))
        gdal.Translate(destName=outfile, srcDS=fname, projWin=[ulx, uly, lrx, lry])

def clipByMask(inputPath, outputPath, shapeName):
    files = []
    postfixList = ["*unw_phase.tif", "*corr.tif", "*dem.tif", "*lv_phi.tif","*lv_theta.tif", "*inc_map*.tif"]
    # postfixList = ["*dem.tif", "*lv_phi.tif","*lv_theta.tif"]
    
    for dir, _, _ in os.walk(inputPath):
        for postfix in postfixList:
            files.extend(glob.glob(os.path.join(dir, postfix)))
    demfile = []
    for filename in files:
        if filename.endswith('dem.tif'):
            demfile = filename            
            break
    
    filehandle = gdal.Open(demfile)
    trans = filehandle.GetGeoTransform()  # t1

    # sometimes the DEM projection is not the same as AOI projection,
    # which might lead to inconsistent image size for two parts of a city
    # AOI projection is perferable.

    prjFile=shapeName.with_suffix('.prj')    
    dstProj=str(prjFile) if prjFile.exists() else filehandle.GetProjection()
    print('Destination projection:',dstProj) 
    # print(demfile, trans)

    outfiles = []
    for i in trange(len(files)):
        # for i in trange(0):
        outfile = files[i].replace(".tif", "_clip.tif")
        outfile = outfile.replace(str(inputPath), str(outputPath))
        creatDir(Path(outfile).parent)
        gdal.Warp(outfile,
                  files[i],
                  format='GTiff',
                  cutlineDSName=str(shapeName),                  
                  dstSRS=dstProj,
                  xRes=abs(trans[1]),
                  yRes=abs(trans[5]),
                  cropToCutline=True,
                  dstNodata=0)
        outfiles.append(outfile)
    return (outfiles)


def copyMetadata(inputPath, outputPath):
    #for currPath in inputPath.glob('S1??_20*_VV????_INT40_G_ueF_????'):
    for currPath in inputPath.glob('S1*_VV_INT*'):
        source = inputPath / f'{currPath.name}' / f'{currPath.name}.txt'
        target = outputPath / f'{currPath.name}' / f'{currPath.name}.txt'
        copyfile(source, target)



def creatConfigProcess(configName, ref_yx, exclude_date, refer_date):
    CONFIG_TXT = f'''
mintpy.compute.cluster      = local
mintpy.load.processor          = hyp3
##---------interferogram datasets:
mintpy.load.unwFile          = {clipPath}/S1*/*unw_phase_clip.tif
mintpy.load.corFile          = {clipPath}/S1*/*corr_clip.tif
#mintpy.load.connCompFile     = {clipPath}/S1*/*_conncomp_clip.tif
##---------geometry datasets:
mintpy.load.demFile          = {clipPath}/S1*/*dem_clip.tif
mintpy.load.incAngleFile     = {clipPath}/S1*/*lv_theta_clip.tif
mintpy.load.azAngleFile      = {clipPath}/S1*/*lv_phi_clip.tif
#mintpy.load.waterMaskFile  = {clipPath}/S1*/*water_mask_clip.tif
########## 2. modify_network
mintpy.network.coherenceBased  = auto  #[yes / no], auto for no, exclude interferograms with coherence < minCoherence
mintpy.network.minCoherence    = auto  #[0.0-1.0], auto for 0.7
mintpy.network.excludeDate     = {exclude_date}
########## 3. reference_point
## Reference all interferograms to one common point in space
## auto - randomly select a pixel with coherence > minCoherence
## however, manually specify using prior knowledge of the study area is highly recommended
##   with the following guideline (section 4.3 in Yunjun et al., 2019):
## 1) located in a coherence area, to minimize the decorrelation effect.
## 2) not affected by strong atmospheric turbulence, i.e. ionospheric streaks
## 3) close to and with similar elevation as the AOI, to minimize the impact of spatially correlated atmospheric delay

mintpy.reference.yx            = {ref_yx}   #[1074,1100 / auto] y axis and x axis of image
mintpy.reference.lalo          = auto   #[31.8,130.8 / auto] latitude and longtitude.  

########## 5. invert_network
## Invert network of interferograms into time-series using weighted least sqaure (WLS) estimator.
## weighting options for least square inversion [fast option available but not best]:
## a. var - use inverse of covariance as weight (Tough et al., 1995; Guarnieri & Tebaldini, 2008) [recommended]
## b. fim - use Fisher Information Matrix as weight (Seymour & Cumming, 1994; Samiei-Esfahany et al., 2016).
## c. coh - use coherence as weight (Perissin & Wang, 2012)
## d. no  - uniform weight (Berardino et al., 2002) [fast]
## SBAS (Berardino et al., 2002) = minNormVelocity (yes) + weightFunc (no)
mintpy.networkInversion.weightFunc      = coh #[var / fim / coh / no], auto for var
mintpy.networkInversion.waterMaskFile   = auto #[filename / no], auto for waterMask.h5 or no [if not found]

## mask options for unwrapPhase of each interferogram before inversion (recommed if weightFunct=no):
## a. coherence        - mask out pixels with spatial coherence < maskThreshold
## b. connectComponent - mask out pixels with False/0 value
## c. no               - no masking [recommended].
## d. offsetSNR        - mask out pixels with offset SNR < maskThreshold [for offset]
mintpy.networkInversion.maskDataset   = coherence #[coherence / connectComponent / offsetSNR / no], auto for no
mintpy.networkInversion.maskThreshold = 0.3 #[0-inf], auto for 0.4

########## 9.2 reference_date
## Reference all time-series to one date in time
## reference: Yunjun et al. (2019, section 4.9)
## no     - do not change the default reference date (1st date)
mintpy.reference.date = {refer_date}   #[reference_date.txt / 20090214 / no], auto for reference_date.txt

########## 10. velocity
## Estimate linear velocity and its standard deviation from time-series
## and from tropospheric delay file if exists.
## reference: Fattahi and Amelung (2015, JGR)
mintpy.velocity.excludeDate    = {exclude_date}   #[exclude_date.txt / 20080520,20090817 / no], auto for exclude_date.txt
    '''
    with open(configName, "w") as fid:
        fid.write(CONFIG_TXT)


if __name__ == '__main__':

    # read the configFile
    configFile = Path(opt.config)

    sys.path.append(str(configFile.parent))
    setting = importlib.import_module(configFile.stem)
    savepath = setting.savePath
    auxPath = setting.auxRoot
    unzipPath = Path(opt.unzipPath) if (len(opt.unzipPath)!=0) else setting.unzipPath
    clipPath, mpyPath = setting.clipPath, setting.mpyPath
    minLat, maxLat = setting.minLat, setting.maxLat
    minLon, maxLon = setting.minLon, setting.maxLon
    shpFile = Path(opt.shapefile) if (len(opt.shapefile)!=0) else setting.shpFile
    cfgData, cfgProc = setting.cfgData, setting.cfgProc
    fnFinalPairs = setting.fnFinalPairs
    # minCoherence = setting.minCoherence
    ref_yx = setting.reference_yx
    '''
    try:
        exclude_txt = setting.exclude_date
    except AttributeError:
        exclude_txt = ''
    if exclude_txt == '':
        exclude_date = 'auto'
    else:
        f = open(exclude_txt)
        exclude_date = ','.join(f.read().splitlines())
        f.close()
        # print(exclude_date)
    '''
    try:
        refer_date = setting.reference_date
    except AttributeError:
        refer_date = 'auto'
    exclude_date='auto'
    # create dirs if they do not exist
    creatDir([clipPath, mpyPath, auxPath])

    # unzip the downloaded data
    if not opt.nounzip:
        print('\033[1;32;40mUnzip files... \033[0m')
        df = pd.read_csv(fnFinalPairs)
        masterList, slaveList = df['Reference'].values, df['Secondary'].values
        for i in trange(masterList.shape[0]):
            prefix = f'S1{masterList[i][2]}{slaveList[i][2]}'
            T1,T2= masterList[i][17:32], slaveList[i][17:32]
            strfmt = f'{prefix}_{T1}_{T2}_VV????_INT40_G_ueF_????.zip'               
            S1AAFiles = list(savepath.glob(strfmt))
            if len(S1AAFiles) == 0:
                print('Warning: cannot find ', strfmt)
            for currFile in S1AAFiles:
                with zipfile.ZipFile(currFile) as f:
                    f.extractall(unzipPath)
        print('\033[1;32;40mUnzip done!\033[0m')

    # clip images in unzipPath and save to clipPath
    if not opt.noclip:
        if all([minLat, maxLat, minLon, maxLon]):
            print('\033[1;32;40mClip images by userdifined mask....\033[0m')
            createUTMshp(minLat, maxLat, minLon, maxLon, shpFile)
            clipByMask(unzipPath, clipPath, shpFile)
            print('\033[1;32;40mClip done!\033[0m')
            
        else:
            print('\033[1;32;40mInvaild Lat/Lon range !\033[0m')            
        
    # Copy metadata files from unzipPath to clipPath
    copyMetadata(unzipPath, clipPath)
    # creatE CONFIG file
    # print(f'\033[1;32;40mCreate config file: {cfgData} \033[0m')
    # creatConfigLoaddata(clipPath, cfgData)
    print(f'\033[1;32;40mCreate config file: {cfgProc} \033[0m')
    creatConfigProcess(cfgProc, ref_yx, exclude_date, refer_date)

from osgeo import gdal
from pyproj import CRS,Transformer
import osgeo_utils.gdal_merge as gm
import argparse
import shutil
from pathlib import Path
import h5py
import load2hdf5
import osgeo_utils.gdal_calc as gc
def getProjBoundFromHDF5(filename):    
    # f = h5py.File("velocity.h5", "r") 
    f = h5py.File(filename, "r") 
    X_FIRST=float(f.attrs['X_FIRST'])
    Y_FIRST=float(f.attrs['Y_FIRST'])
    X_STEP=float(f.attrs['X_STEP'])
    Y_STEP=float(f.attrs['Y_STEP'])
    LENGTH=float(f.attrs['LENGTH'] )# RasterYSize
    WIDTH=float(f.attrs['WIDTH']) # RasterXSize
    EPSG_CODE=f.attrs['EPSG']
    trans=[X_FIRST+X_STEP*0.5,X_STEP,0,Y_FIRST+Y_STEP*0.5,0,Y_STEP]
    projSRS=CRS.from_epsg(EPSG_CODE).to_wkt()    
    minX,minY=getImageXY(trans,0,0)
    maxX,maxY=getImageXY(trans,LENGTH,WIDTH)
    if minX>maxX:
        minX,maxX=maxX,minX
    if minY>maxY:
        minY,maxY=maxY,minY
    projBound=(minX,minY,maxX,maxY)    
    return projSRS,trans,LENGTH,WIDTH,projBound

def ProjBound2GeoBound(projSRS,trans,RasterYSize,RasterXSize  ):
    # point=getImageXY(trans,LENGTH,WIDTH) # RasterYSize RasterXSize  
    
    dstSRS=CRS.from_epsg(4326)    
    srcSRS=CRS.from_wkt(projSRS)        
    ct=Transformer.from_crs(srcSRS, dstSRS, always_xy=True)
    point=getImageXY(trans,0,0)
    minlon,minlat=ct.transform(point[0],point[1])
    point=getImageXY(trans,RasterYSize,RasterXSize)
    maxlon,maxlat=ct.transform(point[0],point[1])
    if minlon>maxlon:
         minlon,maxlon=maxlon,minlon
    if minlat>maxlat:
        minlat,maxlat=maxlat,minlat
    return minlon,minlat,maxlon,maxlat

def getImageXY(trans,row,col):
    return trans[0]+col*trans[1]+row*trans[2],trans[3]+col*trans[4]+row*trans[5]

def isBoundOverlap(b1,b2):
    if b2[3]<b1[1] or b1[3]<b2[1] or b1[0]>b2[2] or b1[2]<b2[0]:
        return False
    else:
        return True
def clipByMask(files, h5Filename,outputfile):
    prefix=h5Filename.parent.stem
    finalfile=f'{prefix}.tif'
    h5ProjSRS,h5Trans,LENGTH,WIDTH,h5ProjBound=getProjBoundFromHDF5(h5Filename)
    h5GeoBound=ProjBound2GeoBound(h5ProjSRS,h5Trans,LENGTH,WIDTH)
    overlappedFiles=[]    
    for i in range(len(files)):
        infile = str(files[i])   
        outfile = f'{prefix}_{i}.tif'
        filehandle = gdal.Open(infile)
        imgTrans = filehandle.GetGeoTransform() # t1
        imgProjSRS = filehandle.GetProjection()   
        imgRows,imgCols= filehandle.RasterYSize,filehandle.RasterXSize
        imgGeoBound=ProjBound2GeoBound(imgProjSRS,imgTrans,imgRows,imgCols)
        if not isBoundOverlap(h5GeoBound,imgGeoBound):
            continue
        gdal.Warp(outfile,
                  infile,
                  format='GTiff',                  
                  outputBounds=h5ProjBound,
                  outputBoundsSRS=h5ProjSRS,
                  dstSRS=h5ProjSRS, 
                  xRes= 40,
                  yRes= 40, 
                  resampleAlg='mode',
                  cropToCutline=True,
                  dstNodata=0)  
        overlappedFiles.append(outfile)  
    print(f'Writing {outputfile}')
    if len(overlappedFiles)==1:
        # Path(overlappedFiles[0]).replace(outputfile)
        shutil.move(overlappedFiles[0],outputfile)
    else:     
        gm.main(['-q','-q','-o',outputfile,'-n', '0.0','-a_nodata','0.0','-pct']+overlappedFiles)
        
        for currFile in overlappedFiles:
            Path(currFile).unlink()
    return 
'''
parser = argparse.ArgumentParser(
description='Acquire some parameters for fusion restore')
parser.add_argument('-c', '--config', default="",help='path to config file (*.h5)')
parser.add_argument('-l', '--lulcpath', required=True, help='path to LULC files (*.tif)') # 
opt = parser.parse_args()


lulcFiles = list(Path(opt.lulcpath).glob('*0101.tif'))

h5Files=list(Path(opt.config).glob('CN_*/geometryGeo.h5'))

for currFile in h5Files:
    print('Processing',str(currFile),'...')
    clipByMask(lulcFiles, currFile)   

currFile=Path(opt.config)
print('Processing',str(currFile),'...')
lulcTiFF='H:\SAR\workplace_CN_\Mintpy\CN_XG_lulc.tif'
# clipByMask(lulcFiles, currFile,lulcTiFF)   
watermaskTiFF = 'H:\SAR\workplace_CN_\Mintpy\CN_XG.tif'

watermaskH5 = 'H:\SAR\workplace_CN_\waterMask.h5'
# gdal_calc.py -A input.tif --outfile=result.tif --calc="A*(A>0)" --NoDataValue=0
gc.main(['--quiet','-a',lulcTiFF, '--outfile',watermaskTiFF,'--calc', "a>1"])
load2hdf5.main([watermaskTiFF, '--dtype', 'byte', '--dname', 'mask', '-o', watermaskH5,'--force'])
'''
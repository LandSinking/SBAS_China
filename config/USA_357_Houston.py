from pathlib import Path

postfix = 'USA_357_Houston'  # Houston, USA
# select images accquired in [startYear,endYear)
# if we need years 2015 and 2016, then startYear=2015,endYear=2017
# set them to None to disable the yearFilter
startYear = 201406
endYear = 202307

# range of frame: [startFrame,endFrame)
# if we need frames 94,95,96, then startFrame=94,endFrame=97
# S1A_IW_SLC__1SDV_20230213T100447_20230213T100514_047216_05AA62_0F98
baseImage='S1A_IW_SLC__1SDV_20241022T122322_20241022T122351_056215_06E1C1_3243'
startFrame = 492
endFrame = 494

# range of latitude/ longtitude for the subset area
# set to None to disable it
minLat = 29.1038
maxLat = 30.1953
minLon = -96.1257
maxLon = -94.6618
# POLYGON((-96.1257 29.1038,-94.6618 29.1038,-94.6618 30.1953,-96.1257 30.1953,-96.1257 29.1038))
# reference_yx and reference_date has a large influence on the sbas results
reference_yx = '1416,2104' #-95.2741, 29.7017
reference_date = 'auto'

# account and password of ASF data center
# accounts of ASFUsr_search are only used for downloading succeed jobs, 
# accounts of ASFUsr_submit are used for submitting jobs and downloading succeed jobs


ASFUsr_search = []
ASFUsr_submit = ['username']
ASFPwd = 'password'

#===================== do not need modification=============================
cfgRoot = Path(__file__).parent  # files for config.py
auxRoot = cfgRoot / postfix  # files for mintpy processing
workplace = cfgRoot.parent / f'workplace_{postfix}'

if not auxRoot.exists():
    auxRoot.mkdir()

if not workplace.exists():
    workplace.mkdir()

fnInitPairs = cfgRoot / f'{postfix}_init_pairs.csv'
fnFinalPairs = auxRoot / f'{postfix}_final_pairs.csv'
figPairs = auxRoot / f'{postfix}_final_pairs.png'

# Max allowed length of jobName is 20 chars, otherwise it will caused an requests.exceptions.HTTPError
# ruler # '12345678901234567890'
jobName = f'WLD_{postfix}'
if len(jobName) > 20:
    print('\033[1;31;40mError: length of jobName must be less than 20! \033[0m')
    exit(1)

# path to save the downloaded data
savePath = cfgRoot.parent / 'S1AAdata' / postfix
print(savePath)
# path to store the unzippded data; SSD is highly recommended
unzipPath = workplace / 'S1AAunzip'

# path to store the clipped the data
clipPath = workplace / 'S1AAclip'

# workplace for mintPY
mpyPath = workplace / 'Mintpy'

# config files for mintPY SBASs

cfgData = auxRoot / f"{jobName}_data.cfg"  # abandoned in this version
cfgProc = auxRoot / f"{jobName}_proc.cfg"  # config file for data processing
shpFile = auxRoot / "AOI.shp"  # shapefile for subarea cutting

if not savePath.exists():
    savePath.mkdir()

if not unzipPath.exists():
    unzipPath.mkdir()

if not clipPath.exists():
    clipPath.mkdir()

if not mpyPath.exists():
    mpyPath.mkdir()

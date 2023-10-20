from pathlib import Path

postfix = 'CN_WH'  # Wuhan , china
# select images accquired in [startYear,endYear)
# if we need years 2015 and 2016, then startYear=2015,endYear=2017
# set them to None to disable the yearFilter
startYear = 201501
endYear = 202301

# range of frame: [startFrame,endFrame)


# All data are good,set them to None to disable the frameFilter
startFrame = None
endFrame = None

# range of latitude/ longtitude for the subset area
# set to None to disable it
minLat = 30.315
maxLat = 30.801
minLon = 114.0343
maxLon = 114.5987

# POLYGON((114.0343 30.315,114.5987 30.315,114.5987 30.801,114.0343 30.801,114.0343 30.315))


# reference_yx and reference_date has a large influence on the sbas results
reference_yx = '723, 689'
reference_date = 'auto'



# account and password of ASF data center
# For most cities, two accounts are needed, each submitting 250jobs
ASFUsr = 'SBAS_CN'
ASFPwd = 'XXXX'

#===================== do not need modification=============================
cfgRoot = Path(__file__).parent  # files for config.py
auxRoot = cfgRoot / postfix  # files for mintpy processing
workplace = cfgRoot.parent / f'workplace_{postfix}'

if not auxRoot.exists():
    auxRoot.mkdir()

if not workplace.exists():
    workplace.mkdir()

fnInitPairs = cfgRoot / f'{postfix}_Init_pairs.csv'
fnFinalPairs = auxRoot / f'{postfix}_final_pairs.csv'
figPairs = auxRoot / f'{postfix}_final_pairs.png'

# Max allowed length of jobName is 20 chars, otherwise it will caused an requests.exceptions.HTTPError
# ruler # '12345678901234567890'
jobName = f'SBAS_{postfix}'
if len(jobName) > 20:
    print('\033[1;31;40mError: length of jobName must be less than 20! \033[0m')
    exit(1)

# path to save the downloaded data
savePath = cfgRoot.parent / 'S1AAdata' / postfix

# path to store the unzippded data; SSD is highly recommended
unzipPath = workplace / 'S1AAunzip'

# path to store the clipped the data
clipPath = workplace / 'S1AAclip'

# workplace for mintPY
mpyPath = workplace / 'Mintpy'

# config files for mintPY SBAS
# minCoherence = 0.5  # Threshold for correlation-based timeseries approach
cfgData = auxRoot / f"{jobName}_data.cfg"  # config file for data loading
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

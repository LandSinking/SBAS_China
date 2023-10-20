import numpy as np
import pandas as pd
import argparse
import sys
import importlib
from pathlib import Path
from hyp3_sdk import HyP3, Batch
from tqdm import tqdm, trange

#==========================processing========================================
def getFiles(filePath, pattern='*'):
    allFiles = []
    files = filePath.glob(pattern)
    for currFile in files:
        if Path.is_file(currFile) or Path.is_dir(currFile):
            allFiles.append(currFile)
    return allFiles


#==========================processing========================================

# parsing
parser = argparse.ArgumentParser(description='Acquire some parameters for fusion restore')
parser.add_argument('-s', '--submit', action='store_true', help='jobs submit')
parser.add_argument('-p', '--path', type=str, default="",help='savepath')
# parser.add_argument('-d', '--download', action='store_true', help='jobs download')
parser.add_argument('-c', '--config', required=True, help='path to config file (*.py)')
opt = parser.parse_args()

configFile = Path(opt.config)
sys.path.append(str(configFile.parent))
setting = importlib.import_module(configFile.stem)
fnFinalPairs = setting.fnFinalPairs
unzipPath, jobName = setting.unzipPath, setting.jobName

if len(opt.path)==0:
    savepath=setting.savePath
else:
    savepath=Path(opt.path)
print('savepath:',savepath)
ASFUsr, ASFPwd = setting.ASFUsr, setting.ASFPwd
# exclude existing files from download list
if not fnFinalPairs.exists():
    print('\033[1;31;40mError: csvFile does not exist! \033[0m')
    exit(1)
df = pd.read_csv(fnFinalPairs)

masterList, slaveList = df['Reference'].values, df['Secondary'].values
idx = []

for i in range(masterList.shape[0]):
    prefix = f'S1{masterList[i][2]}{slaveList[i][2]}'
    T1 = masterList[i][17:32]
    T2 = slaveList[i][17:32]
    strfmt = f'{prefix}_{T1}_{T2}_VVP???_INT40_G_ueF_????*'
    existfiles = getFiles(savepath, strfmt)
    if len(existfiles) == 0:
        idx.append(i)
    else:
        print('existing file: ', [temp.name for temp in existfiles])
mDownList, sDownList = masterList[idx], slaveList[idx]
if mDownList.shape[0] < 1:
    print('No image pairs needed to submit')
    exit(1)

# mDownList, sDownList = df['Reference'].values, df['Secondary'].values
print(f'Will submit: {mDownList.shape[0]}/ {masterList.shape[0]} pairs, accouts: {ASFUsr} ')

if opt.submit:  # sumbit jobs to ASF
    insarJobs = Batch()
    print('\033[1;32;40mASF loading... \033[0m')

    hyp3 = HyP3(username=ASFUsr, password=ASFPwd)  # hyp3 = HyP3(prompt=True)
    print(f'\033[1;32;40msubmiting jobs... \033[0m')

    # The first pair should include dem and inc_map
    hyp3.submit_insar_job(mDownList[0],
                          sDownList[0],
                          name=jobName,
                          looks='10x2',
                          include_dem=True,
                          include_inc_map=True)

    # The other pairs exclude dem and inc_map to save storage
    for i in trange(1, mDownList.shape[0]):
        hyp3.submit_insar_job(mDownList[i],
                              sDownList[i],
                              name=jobName,
                              looks='10x2',
                              include_dem=False,
                              include_inc_map=False)
    print('\033[1;32;40mDone. \033[0m')
    # The process may takes 1~2 hours.
    # Monitoring jobs until they finish.
    # Monitor = hyp3.watch(insarJobs)
'''
if opt.download:  # download jobs
    print('download')
    insarJobs = hyp3.find_jobs(name=jobName)
    Monitor = hyp3.watch(insarJobs)
    # download the files for all successful jobs
    succeeded_jobs = Monitor.filter_jobs(succeeded=True, running=False, failed=False)
    S1AAFiles = succeeded_jobs.download_files(savepath)
'''
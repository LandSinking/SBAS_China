# last modified: 20240503
import numpy as np
import math
import time,random
import pandas as pd
import argparse
import sys
import re
import importlib
from pathlib import Path
from hyp3_sdk import HyP3, Batch
from tqdm import tqdm, trange
import matplotlib.pyplot as plt
import matplotlib.dates as mdt
from datetime import date
# parsing 
parser = argparse.ArgumentParser(description='Acquire some parameters for fusion restore')
parser.add_argument('-s', '--submit', action='store_true', default=False,help='jobs submit')
parser.add_argument('-p', '--path', type=str, default="",help='savepath')
parser.add_argument('-v', '--view', action='store_true', default=False,help='viewing submited jobs')
parser.add_argument('-d', '--download', action='store_true', default="",help='get download urls')
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
ASFUsr_submit,ASFUsr_search=setting.ASFUsr_submit,setting.ASFUsr_search
ASFPwd =  setting.ASFPwd
# exclude existing files from download list

if not fnFinalPairs.exists():
    print(f'\033[1;31;40mError: {fnFinalPairs} does not exist! \033[0m')
    exit(1)
df = pd.read_csv(fnFinalPairs)

existFilePrefixes = set([file.name[:36] for file in savepath.glob('S1??_*_*_VV????_INT*')])
masterList, slaveList = df['Reference'].values, df['Secondary'].values
idx = []

for i in range(masterList.shape[0]):    
    T1 = masterList[i][17:32]
    T2 = slaveList[i][17:32]
    currprefix = f'S1{masterList[i][2]}{slaveList[i][2]}_{T1}_{T2}'    
    if currprefix not in existFilePrefixes:
        idx.append(i)
    else:
        print(f'existing files: {currprefix}*')
mDownList, sDownList = masterList[idx], slaveList[idx]
if mDownList.shape[0] < 1:
    print('No image pairs needed to submit')
    exit(1)

# mDownList, sDownList = df['Reference'].values, df['Secondary'].values
print(f'inexist files: {mDownList.shape[0]}/ {masterList.shape[0]} pairs, accouts: {ASFUsr_submit},{ASFUsr_search} ')
if opt.view:  # view sumbited jobs 
    insarJobs = Batch()    
    downList = []
    for i in range(mDownList.shape[0]):        
        downList.append((mDownList[i],sDownList[i])) 
    succeededList=[]
    runningList=[]    
    ASFUsrList =ASFUsr_submit+ASFUsr_search
    print(ASFUsrList)
    for ASFUsr in ASFUsrList:
        print(f'\033[1;32;40mProcessing ASF account {ASFUsr}... \033[0m')
        hyp3 = HyP3(username=ASFUsr, password=ASFPwd)  # hyp3 = HyP3(prompt=True)    
        insarJobs = hyp3.find_jobs(name=jobName) 
        succeededJobs=insarJobs.filter_jobs(succeeded=True, running=False, failed=False,include_expired=False)
        for i in range(len(succeededJobs)):
            currjob=succeededJobs[i].to_dict(for_resubmit=True)
            succeededList.append((currjob['job_parameters']['granules'][0],
                                currjob['job_parameters']['granules'][1]))           
        runningJobs=insarJobs.filter_jobs(succeeded=False, running=True, failed=False,include_expired=False)
        for i in range(len(runningJobs)):
            currjob=runningJobs[i].to_dict(for_resubmit=True)
            runningList.append((currjob['job_parameters']['granules'][0],
                                currjob['job_parameters']['granules'][1]))
        time.sleep(random.randint(5,8))
        
    resubmitList=list(set(downList)-set(succeededList)-set(runningList))
    print(f"Jobs to be summited: {masterList.shape[0]}")
    print(f"Jobs to be downloaded: {mDownList.shape[0]}")
    print(f"Succeeded jobs: {len(set(succeededList)-set(runningList))}")
    print(f"Running jobs: {len(set(runningList))}")
    print(f"Jobs to be resummited after deduplication: {len(resubmitList)}")   

    
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.xaxis.set_major_formatter(mdt.DateFormatter('%Y-%m-%d'))
    ax.xaxis.set_minor_locator(mdt.MonthLocator())
    ax.tick_params(axis='both', direction='out', labelsize=10)

    succeededList=set(succeededList)-set(runningList)
    print(f'Drawing {len(succeededList)} pairs...')
    allPairs=set()
    MasterList=[]
    SlaveList=[]
    for currPair in succeededList:
        MasterList.append(currPair[0])
        SlaveList.append(currPair[1])
        allPairs.add(currPair[0])
        allPairs.add(currPair[1])
    allPairs=list(allPairs)
    dates = np.zeros(len(allPairs), dtype=int)
    
    for i, currFile in enumerate(allPairs):
        tempDate = date(int(currFile[17:21]), int(currFile[21:23]), int(currFile[23:25]))
        dates[i] = mdt.date2num(tempDate)
    baseline=np.array([random.randint(0,200) for i in range(len(allPairs))])
    for i in range(dates.shape[0]):
        ax.plot_date(dates[i], baseline[i], c='green')  # , picker=point_pickers
    for currPair in set(succeededList):        
        idx0=allPairs.index(currPair[0])
        idx1=allPairs.index(currPair[1])
        x0, y0 = dates[idx0], baseline[idx0]
        x1, y1 = dates[idx1], baseline[idx1]
        ax.plot_date((x0, x1), (y0, y1), 'deepskyblue', picker=True)
    fig.autofmt_xdate()
    plt.show()
    fig.savefig('fig.png', dpi=300, bbox_inches='tight')
  
if opt.submit:  # sumbit jobs to ASF    
    insarJobs = Batch()    
    downList = []
    for i in range(mDownList.shape[0]):        
        downList.append((mDownList[i],sDownList[i])) 
    succeededList=[]
    runningList=[]
    ASFUsrList =ASFUsr_submit+ASFUsr_search
    demFlag=True
    print(f'\033[1;32;40mCount submitted jobs... \033[0m')
    for ASFUsr in ASFUsrList:
        print(f'  loading ASF account {ASFUsr}...')
        hyp3 = HyP3(username=ASFUsr, password=ASFPwd)  # hyp3 = HyP3(prompt=True)    
        insarJobs = hyp3.find_jobs(name=jobName) 
        succeededJobs=insarJobs.filter_jobs(succeeded=True, running=False, failed=False,include_expired=False)
        
        for i in range(len(succeededJobs)):
            currjob=succeededJobs[i].to_dict(for_resubmit=True)
            succeededList.append((currjob['job_parameters']['granules'][0],
                                currjob['job_parameters']['granules'][1]))
            if currjob['job_parameters']['include_dem']==True:
                demFlag=False

        runningJobs=insarJobs.filter_jobs(succeeded=False, running=True, failed=False,include_expired=False)
        for i in range(len(runningJobs)):
            currjob=runningJobs[i].to_dict(for_resubmit=True)
            runningList.append((currjob['job_parameters']['granules'][0],
                                currjob['job_parameters']['granules'][1])) 
    submitList=list(set(downList)-set(succeededList)-set(runningList))    
    print(f'\033[1;32;40mSubmiting in total {len(submitList)} jobs... \033[0m')

    # NUM of pairs to be submitted in this loop
    numSubmit=math.ceil(len(submitList)/len(ASFUsr_submit))
    for iUsr in range(len(ASFUsr_submit)):
        posStart=iUsr*numSubmit
        posEnd=min((iUsr+1)*numSubmit,len(submitList))
        print(f'\033[1;32;40m\n  Submiting jobs {posStart} -- {posEnd} via {ASFUsrList[iUsr]}... \033[0m')
        hyp3 = HyP3(username=ASFUsrList[iUsr], password=ASFPwd)  # hyp3 = HyP3(prompt=True) 
        # The other pairs exclude dem and inc_map to save storage
        for i in trange(posStart, posEnd, desc="  1.Submit Jobs.....",colour='green'):
            if (demFlag==True) and (i==0):
                # The first pair should include dem and inc_map
                hyp3.submit_insar_job(submitList[0][0],
                                    submitList[0][1],
                                    name=jobName,
                                    looks='10x2',
                                    apply_water_mask=True,
                                    include_dem=demFlag,
                                    include_inc_map=demFlag,
                                    include_look_vectors=demFlag)
                demFlag=False
            else:
                hyp3.submit_insar_job(submitList[i][0],
                                    submitList[i][1],
                                    name=jobName,
                                    looks='10x2',
                                    apply_water_mask=True,
                                    include_dem=False,
                                    include_inc_map=False,
                                    include_look_vectors=False)  
       
        for i in trange(random.randint(200,300),desc="  2.Sleeping 3~5 min",colour='red'):
            time.sleep(1)        


if opt.download:
    ASFUsrList =ASFUsr_submit+ASFUsr_search    
    print(f'\033[1;32;40mASF account loading... \033[0m')
    download_urls=[]
    for ASFUsr in ASFUsrList:
        hyp3 = HyP3(username=ASFUsr, password=ASFPwd)
        insarJobs = hyp3.find_jobs(name=jobName) 
        succeededJobs=insarJobs.filter_jobs(succeeded=True, running=False, failed=False,include_expired=False)
        
        for iJob in succeededJobs.jobs:  
            if iJob.status_code=='SUCCEEDED':
                for file in iJob.files:
                    download_urls.append(file['url'])
    
    
    unique_download_urls=[]
    unique_prefixes=existFilePrefixes
    pattern = re.compile("S1[AB]{2}_20\d{6}T\d{6}_20\d{6}T\d{6}")
    for url in download_urls:
        match = re.search(pattern, url)
        currprefix= match.group() 
        if  currprefix not in unique_prefixes:
            unique_prefixes.add(currprefix)
            unique_download_urls.append(url)
    
    print(f"get {len(download_urls)} files in total, and {len(unique_download_urls)} files after deduplication.") 
    filename= jobName+"_urls.txt"
    with open(filename, "w") as file:
        for url in unique_download_urls:
            file.write(str(url) + "\n")
        file.close()




# SBAS_China: steps for MintPy time series analysis
# 

1. edit the ASFUsr and ASFPwd in config/CN_WH.py
2. run procMdfPairs.py to filter the image pairs and edit the SBAS network
<pre><code>python procMdfPairs.py -c ../config/CN_WH.py</code></pre>
3. run procHYP3.py to submit jobs to ASF
<pre><code>python procHYP3.py -c .../config/CN_WH.py</code></pre>
4. After the jobs are finished, download the displacement products and save them to folder "S1AAdata/CN_WH"
5. run procPrepData.py to unzip, clip and prepare the datasets
<pre><code>python procPrepData.py -c .../config/CN_WH.py</code></pre> 
6. run procSBAS.py to start the MintPy time series analysis
<pre><code>python procSBAS.py -c .../config/CN_WH.py</code></pre> 
7. the results file can be found in folder "./workplace_CN_WH/Mintpy"

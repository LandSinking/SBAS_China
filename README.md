# SBAS_China: steps for InSAR time series analysis
# 

1. edit the ASFUsr and ASFPwd in config/USA_357_Houston.py, and run procSearchPairs.py to geneate Sentinel-1 stack
<pre><code>python procSearchPairs.py -c ../config/USA_357_Houston.py</code></pre>
2. run procMdfPairs.py to filter the image pairs and edit the SBAS network via a simple GUI
<pre><code>python procMdfPairs.py -c ../config/USA_357_Houston.py</code></pre>
3. run procHYP3.py with "-s" option to submit jobs to ASF . Details for available options can be found in the source code.
<pre><code>python procHYP3.py -c ../config/USA_357_Houston.py -s</code></pre>
4. After the jobs are finished, run procHYP3.py with "-d" option to get the links for downloading the displacement products. 
<pre><code>python procHYP3.py -c ../config/USA_357_Houston.py -d</code></pre>
5. Download the displacement products to the folder "S1AAdata/USA_357_Houston", and then run procPrepData.py to unzip, clip and prepare the datasets
<pre><code>python procPrepData.py -c ../config/USA_357_Houston.py</code></pre> 
6. run procSBAS.py to start the MintPy time series analysis
<pre><code>python procSBAS.py -c ../config/USA_357_Houston.py</code></pre> 
7. Result files can be found in folder "./workplace_USA_357_Houston/Mintpy"

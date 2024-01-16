# written by A. Van Beusekom (2023)

## Visualize statistics per GRU
## Needs:
#    SUMMA output statistics

## Special note
# SUMMA simulations have been preprocessed into single value statistics per model element, using auxiliary scripts in ~/utils
# Run:
# python hist_per_GRU.py [stat]
# where stat is rmse or maxe or kgem

# modules
import os
import matplotlib
import numpy as np
import xarray as xr
from pathlib import Path
import matplotlib.pyplot as plt
import copy
import pandas as pd

viz_dir = Path('/home/avanb/scratch/statistics')
nbatch_hrus = 518 # number of HRUs per batch
num_bins = 1000
use_eff = False # use efficiency in wall clock time
do_rel = True # plot relative to the benchmark simulation

testing = False
do_hist = False # plot histogram instead of CDF
if testing: 
    stat = 'rmnz'
    viz_dir = Path('/Users/amedin/Research/USask/test_py/statistics')
    method_name=['be1','sundials_1en6'] #maybe make this an argument
    plt_name=['BE1','IDAe-6'] #maybe make this an argument
else:
    import sys
    # The first input argument specifies the run where the files are
    stat = sys.argv[1]
    #method_name=['be1','sundials_1en4','be4','be8','be16','be32','sundials_1en6'] #maybe make this an argument
    #plt_name=['BE1','IDAe-4','BE4','BE8','BE16','BE32','IDAe-6'] #maybe make this an argument
    method_name=['be1','be16','be32','sundials_1en6'] #maybe make this an argument
    plt_name=['BE1','BE16','BE32','SUNDIALS'] #maybe make this an argument
if stat == 'kgem': do_rel = False # don't plot relative to the benchmark simulation for KGE

# Define the power transformation function
def power_transform(x):
    return x ** 0.5  # Adjust the exponent as needed

# Simulation statistics file locations
use_vars = [1,2,4,5]
settings0= ['scalarSWE','scalarTotalSoilWat','scalarTotalET','scalarCanopyWat','averageRoutedRunoff','wallClockTime']
settings = [settings0[i] for i in use_vars]

viz_fil = method_name.copy()
eff_fil = method_name.copy()
for i, m in enumerate(method_name):
    viz_fil[i] = m + '_hrly_diff_stats_{}.nc'
    viz_fil[i] = viz_fil[i].format(','.join(settings0))
    eff_fil[i] = 'eff_' + m + '.txt'

# Specify variables of interest
plot_vars = settings.copy()
plt_titl = ['Snow Water Equivalent','Total soil water content','Total evapotranspiration', 'Total water on the vegetation canopy','Average routed runoff','Wall clock time']
leg_titl = ['$kg~m^{-2}$', '$kg~m^{-2}$','mm~y^{-1}$','$kg~m^{-2}$','$mm~y^{-1}$','$s$']
leg_titlm= ['$kg~m^{-2}$', '$kg~m^{-2}$','mm~h^{-1}$','$kg~m^{-2}$','$mm~h^{-1}$','$s$']
plt_titl = [f"({chr(97+n)}) {plt_titl[i]}" for n,i in enumerate(use_vars)]
leg_titl = [leg_titl[i] for i in use_vars]
leg_titlm= [leg_titlm[i] for i in use_vars]

if do_hist:
    fig_fil = 'Hrly_diff_hist_{}_{}_zoom_compressed.png'
    if do_rel: fig_fil = 'Hrly_diff_hist_{}_{}_zoom_rel_compressed.png'
else:
    fig_fil = 'Hrly_diff_cdf_{}_{}_zoom_compressed.png'
    if do_rel: fig_fil = 'Hrly_diff_cdf_{}_{}_zoom_rel_compressed.png'
fig_fil = fig_fil.format(','.join(settings),stat)

if stat == 'rmse': 
    maxes = [2,15,250,0.08,200,10e-3] 
    if do_rel: maxes = [0.6,0.02,0.6,0.3,0.6,10e-3]
if stat == 'rmnz': 
    maxes = [2,15,250,0.08,200,10e-3]
    if do_rel: maxes = [0.6,0.02,0.6,0.3,0.6,10e-3]
if stat == 'maxe': 
    maxes = [15,25,0.8,2,0.3,0.2]
    if do_rel: maxes = [0.6,0.02,0.6,0.3,0.6,0.2]
if stat == 'kgem': 
    maxes = [0.9,0.9,0.9,0.9,0.9,10e-3]
maxes = [maxes[i] for i in use_vars]

summa = {}
eff = {}
for i, m in enumerate(method_name):
    # Get the aggregated statistics of SUMMA simulations
    summa[m] = xr.open_dataset(viz_dir/viz_fil[i])
    if use_eff:
        # Read the data from the eff.txt file into a DataFrame
        eff[m] = pd.read_csv(viz_dir/eff_fil[i], sep=',', header=None, names=['CPU Efficiency', 'Array ID', 'Job Wall-clock time', 'Node Number'])
        # Extract only the values after the ':' character in the 'CPU Efficiency', 'Job Wall-clock time', and 'Node Number' columns
        eff[m]['CPU Efficiency'] = eff[m]['CPU Efficiency'].str.split(':').str[1].astype(float)
        eff[m]['Array ID'] = eff[m]['Array ID'].str.split(':').str[1].astype(int)   
        eff[m]['Job Wall-clock time'] = eff[m]['Job Wall-clock time'].str.split(':').str[1].astype(float)
        eff[m]['Node Number'] = eff[m]['Node Number'].str.split(':').str[1].astype(int)
    
##Figure

if 'compressed' in fig_fil:
    plt.rcParams.update({'font.size': 25})
else:
    plt.rcParams.update({'font.size': 100})

if 'compressed' in fig_fil:
    fig,axs = plt.subplots(3,2,figsize=(35,38))
else:
    fig,axs = plt.subplots(3,2,figsize=(140,160))
fig.subplots_adjust(hspace=0.24, wspace=0.24) # Adjust the bottom margin, vertical space, and horizontal space
#fig.suptitle('Histograms of Hourly Statistics for each GRU', fontsize=40,y=1.0)
    
def run_loop(i,var,mx):
    r = i//2
    c = i-r*2
    stat0 = stat
    if stat == 'rmse' or stat == 'kgem': 
        if var == 'wallClockTime': stat0 = 'mean'
        statr = 'mean_ben'
    if stat == 'rmnz':
        if var == 'wallClockTime': stat0 = 'mnnz'
        statr = 'mnnz_ben'
    if stat == 'maxe': 
        if var == 'wallClockTime': stat0 = 'amax'
        statr = 'amax_ben'
        
    if 'zoom' in fig_fil:
        mx = mx
        mn = mx
    else:
        mx = 0.0
        mn = 1.0
        if do_rel: s_rel = summa[method_name[0]][var].sel(stat=statr)
        for m in method_name:
            s = summa[m][var].sel(stat=stat0)
            if do_rel and var != 'wallClockTime': s = s/s_rel
            if stat == 'maxe': s = np.fabs(s) # make absolute value norm
            mx = max(s.max(),mx)
            if stat == 'kgem': mn = min(s.min(),mn)

    # Data
    if do_rel: s_rel = summa[method_name[0]][var].sel(stat=statr)
    for m in method_name:
        s = summa[m][var].sel(stat=stat0)
        if do_rel and var != 'wallClockTime': s = s/s_rel

        if var == 'wallClockTime' and use_eff:
            batch = np.floor(np.arange(len(s.indexes['hru'])) /nbatch_hrus)
            #basin_num = np.arange(len(s.indexes['hru'])) % nbatch_hrus #not currently using
            # Create a dictionary to store the values for each batch
            efficiency = {}
            node = {}
            # Iterate over the rows in the data DataFrame
            for index, row in eff[m].iterrows():
                # Extract the values from the row
                batch0 = int(row['Array ID'])
                eff0 = row['CPU Efficiency']
                node0 = row['Node Number']
                # Store the value for the current batch in the dictionary
                efficiency[batch0] = eff0  
                node[batch0] = node0
            # Select the values for the current batch using boolean indexing
            eff_batch = np.array([efficiency[b] for b in batch])
            #node_batch = np.array([node[b] for b in batch]) #not currently using
            # Multiply the s values by efficiency
            s = s*eff_batch

        if var == 'scalarTotalET' and not do_rel:
            if stat =='rmse' or stat =='rmnz' : s = s*31557600 # make annual total
            if stat =='maxe': s = s*3600 # make hourly max
        if var == 'averageRoutedRunoff' and not do_rel:
            if stat =='rmse' or stat =='rmnz' : s = s*31557600*1000 # make annual total
            if stat =='maxe': s = s*3600*1000 # make hourly max           
        if stat == 'maxe': s = np.fabs(s) # make absolute value norm
        range = (0,mx)
        if stat=='kgem' and var!='wallClockTime' : range = (mn,1)
        if do_hist: 
            np.fabs(s).plot.hist(ax=axs[r,c], bins=num_bins,histtype='step',zorder=0,label=m,linewidth=2.0,range=range)
        else: #cdf
            sorted_data = np.sort(np.fabs(s))
            valid_data = sorted_data[~np.isnan(sorted_data)]
            yvals = np.arange(len(valid_data)) / float(len(valid_data) - 1)
            axs[r,c].plot(valid_data, yvals, zorder=0, label=m, linewidth=2.0)
            axs[r,c].set_xlim(range)  # Replace xmin and xmax with the desired limits


    if stat0 == 'rmse': stat_word = 'RMSE'
    if stat0 == 'rmnz': stat_word = 'RMSE' # no 0s'
    if stat0 == 'maxe': stat_word = 'max abs error'
    if stat0 == 'kgem': stat_word = 'KGE"'
    if stat0 == 'mean': stat_word = 'mean'
    if stat0 == 'mnnz': stat_word = 'mean' # no 0s'
    if stat0 == 'amax': stat_word = 'max'
    
    if statr == 'mean_ben': statr_word = 'mean'
    if statr == 'mnnz_ben': statr_word = 'mean' # no 0s'
    if statr == 'amax_ben': statr_word = 'max'

    axs[r,c].legend(plt_name)
    axs[r,c].set_title(plt_titl[i])
    if stat == 'rmse' or stat == 'rmnz': axs[r,c].set_xlabel(stat_word + ' [{}]'.format(leg_titl[i]))
    if stat == 'maxe': axs[r,c].set_xlabel(stat_word + ' [{}]'.format(leg_titlm[i]))   
    if stat == 'kgem': axs[r,c].set_xlabel(stat_word)
    #if do_rel and var!='wallClockTime': axs[r,c].set_xlabel(stat_word + ' rel to bench ' + statr_word)
    if do_rel and var!='wallClockTime': axs[r,c].set_xlabel('relative '+ stat_word)

    if do_hist: 
        axs[r,c].set_ylabel('GRU count')
        if var != 'wallClockTime' and not testing: axs[r,c].set_ylim([0, 25000])
        #if var == 'wallClockTime': axs[r,c].set_yscale('log') #log y axis for wall clock time to exaggerate peaks

    else:
        axs[r,c].set_ylabel('cumulative distribution')
        axs[r,c].set_ylim([0.0, 1.0])
        axs[r,c].set_xscale('function', functions=(power_transform, np.power)) #log x axis
        if var=='scalarTotalSoilWat': # Rotate x-axis labels for axs[2, 1] subplot
            axs[r, c].tick_params(axis='x', rotation=45)

for i,(var,mx) in enumerate(zip(plot_vars,maxes)): 
    run_loop(i,var,mx)

# Save
plt.savefig(viz_dir/fig_fil, bbox_inches='tight', transparent=False)

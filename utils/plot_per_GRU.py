# written originally by W. Knoben, modified by A. Van Beusekom (2023)

## Visualize statistics per GRU
## Needs:
#    Catchment shapefile with GRU delineation
#    SUMMA output statistics

## Special note
# SUMMA simulations have been preprocessed into single value statistics per model element, using auxiliary scripts in ~/utils
# To improve visualization of large lakes, HydroLAKES lake delineations are plotted on top of the catchment GRUs and river segments.
# Dealing with HydroLAKES inputs is not considered within scope of the workflow and therefore requires some manual downloading and preprocessing of this data for those who wish to reproduce this step.
# The relevant code is easily disabled by switching the plot_lakes = True flag to False.

# Run:
# python plot_per_GRU.py


# modules
import os
import pyproj 
import fiona
import matplotlib
import numpy as np
import xarray as xr
import geopandas as gpd
from pathlib import Path
import matplotlib.pyplot as plt
import copy
import multiprocessing as mp


# Simulation statistics file locations
method_name = 'sundials_1en6'
stat = 'rmse' #max or rmse
settings= {'averageRoutedRunoff': stat, 'wallClockTime': stat, 'scalarTotalET': stat, 'scalarSWE': stat, 'scalarCanopyWat': stat, 'scalarTotalSoilWat': stat}
#viz_dir = Path('/home/avanb/projects/rpp-kshook/avanb/summaWorkflow_data/domain_NorthAmerica/statistics')
viz_dir = Path('/home/avanb/scratch/statistics')
viz_fil = method_name + '_hrly_diff_stats_{}_{}2.nc'
viz_fil = viz_fil.format(','.join(settings.keys()),','.join(settings.values()))

# Specify variables of interest
plot_vars = ['scalarSWE','scalarTotalSoilWat','scalarTotalET','scalarCanopyWat','averageRoutedRunoff','wallClockTime']
plt_titl = ['(a) Snow Water Equivalent','(b) Total soil water content','(c) Total evapotranspiration', '(d) Total water on the vegetation canopy','(e) Average routed runoff','(f) Wall clock time']
leg_titl = ['$kg~m^{-2}$', '$kg~m^{-2}$','$kg~m^{-2}~s^{-1}$','$kg~m^{-2}$','$m~s^{-1}$','$s$']
if stat=='rmse': maxes = [60,30,5e-6,0.2,1e-8,200]
if stat=='max' : maxes = []

fig_fil = method_name + '_hrly_diff_stats_{}_{}_compressed.png'
fig_fil = fig_fil.format(','.join(settings.keys()),','.join(settings.values()))

# Get the albers shapes
main = Path('/home/avanb/projects/rpp-kshook/wknoben/CWARHM_data/domain_NorthAmerica/shapefiles/albers_projection')

# Plot lakes?
plot_lakes = True
# lakes shapefile WHERE IS THIS
#lake_path = Path('C:/Globus endpoint/HydroLAKES/HydroLAKES_polys_v10_shp')
#lake_name = 'HydroLAKES_polys_v10_subset_NA.shp'

## Control file handling
# Store the name of the 'active' file in a variable
controlFile = 'plot_control_NorthAmerica.txt'

# Function to extract a given setting from the control file
def read_from_control( file, setting ):

    # Open controlFile and ...
    with open(file) as contents:
        for line in contents:

            # ... find the line with the requested setting
            if setting in line and not line.startswith('#'):
                break

    # Extract the setting's value
    substring = line.split('|',1)[1]      # Remove the setting's name (split into 2 based on '|', keep only 2nd part)
    substring = substring.split('#',1)[0] # Remove comments, does nothing if no '#' is found
    substring = substring.strip()         # Remove leading and trailing whitespace, tabs, newlines

    # Return this value
    return substring

# Function to specify a default path
def make_default_path(suffix):

    # Get the root path
    rootPath = Path( read_from_control(controlFile,'root_path') )

    # Get the domain folder
    domainName = read_from_control(controlFile,'domain_name')
    domainFolder = 'domain_' + domainName

    # Specify the forcing path
    defaultPath = rootPath / domainFolder / suffix

    return defaultPath


## Catchment shapefile location and variable names
# HM catchment shapefile path & name
hm_catchment_path = read_from_control(controlFile,'catchment_shp_path')
hm_catchment_name = read_from_control(controlFile,'catchment_shp_name')
# Specify default path if needed
if hm_catchment_path == 'default':
    hm_catchment_path = make_default_path('shapefiles/catchment') # outputs a Path()
else:
    hm_catchment_path = Path(hm_catchment_path) # make sure a user-specified path is a Path()

# Find the GRU and HRU identifiers
hm_hruid = read_from_control(controlFile,'catchment_shp_hruid')


## River network shapefile location and variable names
# Plot rivers?
plot_rivers = False
# River network path & name
river_network_path = read_from_control(controlFile,'river_network_shp_path')
river_network_name = read_from_control(controlFile,'river_network_shp_name')
# Specify default path if needed
if river_network_path == 'default':
    river_network_path = make_default_path('shapefiles/river_network') # outputs a Path()
else:
    river_network_path = Path(river_network_path) # make sure a user-specified path is a Path()

# Find the segment ID
seg_id = read_from_control(controlFile,'river_network_shp_segid')


## Load all shapefiles and project to Albers Conformal Conic and reproject
# Set the target CRS
acc = 'ESRI:102008'

# catchment shapefile, first 2 lines throw error so cutting them
#bas = gpd.read_file(hm_catchment_path/hm_catchment_name)
#bas_albers = bas.to_crs(acc)
bas_albers = gpd.read_file(main/'basin.shp')

# river network shapefile, first 2 lines throw error so cutting them
if plot_rivers:
	#riv = gpd.read_file(river_network_path/river_network_name)
	#riv_albers = riv.to_crs(acc)
	riv_albers = gpd.read_file(main/'river.shp')

# lakes shapefile, first 2 lines throw error so cutting them
if plot_lakes:
	#lakes = gpd.read_file(lake_path/lake_name)
	#lak_albers = lakes.to_crs(acc)
	lak_albers = gpd.read_file(main/'lakes.shp')



## Pre-processing, map SUMMA sims to catchment shapes
# Get the aggregated statistics of SUMMA simulations
summa = xr.open_dataset(viz_dir/viz_fil)

# Match the accummulated values to the correct HRU IDs in the shapefile
hru_ids_shp = bas_albers[hm_hruid].astype(int) # hru order in shapefile
for plot_var in plot_vars:
    bas_albers[plot_var] = summa[plot_var].sel(hru=hru_ids_shp.values)

# Select lakes of a certain size for plotting
if plot_lakes:
    minSize = 1000 # km2
    in_domain = (lak_albers['Country'] == 'Canada') | \
                (lak_albers['Country'] == 'United States of America') | \
                (lak_albers['Country'] == 'Mexico')
    out_domain = (lak_albers['Pour_long'] > -80) & (lak_albers['Pour_lat'] > 65) # Exclude Baffin Island
    large_lakes_albers = lak_albers.loc[(lak_albers['Lake_area'] > minSize) & in_domain & (~out_domain) ]
# Set the lake color
if plot_lakes:
    lake_col = (8/255,81/255,156/255)

##Figure

# Set the font size: we need this to be huge so we can also make our plotting area huge, to avoid a gnarly plotting bug
if 'compressed' in fig_fil:
    plt.rcParams.update({'font.size': 25})
else:
    plt.rcParams.update({'font.size': 100})

# Flip the evaporation values so that they become positive, not if plotting diffs
#bas_albers['plot_ET'] = bas_albers['scalarTotalET'] * -1
#bas_albers['plot_ET'] = bas_albers['plot_ET'].where(bas_albers['scalarTotalET'] != -9999, np.nan)

if 'compressed' in fig_fil:
    fig,axs = plt.subplots(3,2,figsize=(35,33))
else:
    fig,axs = plt.subplots(3,2,figsize=(140,133))

# colorbar axes
f_x_mat = [0.473,0.97,0.473,0.97,0.473,0.97]
f_y_mat = [0.69,0.69,0.36,0.36,0.03,0.03]

plt.tight_layout()

my_cmap = copy.copy(matplotlib.cm.get_cmap('inferno_r')) # copy the default cmap
#my_cmap.set_bad(my_cmap.colors[0])

if stat == 'rmse':
    stat_word = ' Hourly RMSE'
if stat == 'max':
    stat_word = ' Hourly max abs error'
    
def run_loop(i,var,the_max,f_x,f_y):
    #vmin = (bas_albers[var].where(bas_albers[var]>0)).min()
    #a = bas_albers[var].where(bas_albers[var]>0)
    #bas_albers[var] = a.fillna(vmin)
    vmin,vmax = bas_albers[var].min(), bas_albers[var].max()
    vmin,vmax = 0, the_max
    norm=matplotlib.colors.Powernorm(vmin=vmin,vmax=vmax,gamma=0.5)
    
    # Data
    sm = bas_albers.plot(ax=axs[i], column=var, edgecolor='none', legend=False, cmap=my_cmap, norm=norm,zorder=0)
    
    # Custom colorbar
    cax = fig.add_axes([f_x,f_y,0.02,0.3])
    cbr = fig.colorbar(sm, cax=cax, extend='max')
    cbr.ax.set_title('[{}]'.format(leg_titl[i]))

    axs[i].set_title(plt_titl[i] + stat_word)
    axs[i].axis('off')
    
    # lakes
    if plot_lakes: large_lakes_albers.plot(ax=axs[i], color=lake_col, zorder=1)


# -- start parallel processing
ncpus = int(os.environ.get('SLURM_CPUS_PER_TASK',default=1))
if __name__ == "__main__":
    pool = mp.Pool(processes=ncpus)
    results = [pool.apply_async(run_loop, args=(i,var,the_max,f_x,f_y)) for i,(var,the_max,f_x,f_y) in enumerate(zip(plot_vars,maxes,f_x_mat,f_y_mat))]
    dojob = [p.get() for p in results]
    pool.close()
# -- end parallel processing


# Save
plt.savefig(viz_dir/fig_fil, bbox_inches='tight', transparent=True)

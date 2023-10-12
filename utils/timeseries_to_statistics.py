# SUMMA can produce split-domain output files if the model is used with the -g <start> <num> command line option.
'''Loads timeseries of simulated variables and computes a variety of statistics.'''

# This script analyzes the resulting files and summarizes the timeseries of a (set of) variable(s) into a statistical value.
# Currently implemented are finding the maximum and mean value across the entire time series.
# Outputs are stored in a single file that covers the full spatial extent of the domain.
# written originally by W. Knoben, modified by A. Van Beusekom (2023)
#   Best to comment out parallel processing lines and run that way on Graham or for full dataset

# Uses modified KGEm calculation avoids the amplified values when mean is small
#  and avoids the KGE value dependence  on the units of measurement (as discussed by Santos et al. 2018; Clark et al. 2021).
# The KGEm values range from -∞ to 1, with 1 being a perfect match with the benchmark results.
# Similar to Beck et al.(2020), we scaled KGEm values to avoid the heavy influence of large negative values.
# This results in KGE values that range between -1 and 1, with lower KGE values indicating larger differences from bench.

# Run:
# python timeseries_to_statistics.py sundials_1en6

import os
import glob
import xarray as xr
from pathlib import Path
import numpy as np

import warnings
warnings.simplefilter("ignore") #deal with correlation warnings from variance 0 in kgem, both have no snow

# Settings
bench_name  = 'sundials_1en8'

not_parallel = False # should usually be false, runs faster
testing = False

if testing: 
    top_fold    = '/Users/amedin/Research/USask/test_py/'
    method_name='be1'
    not_parallel = True
else:
    import sys
    # The first input argument specifies the run where the files are
    method_name = sys.argv[1] # sys.argv values are strings by default so this is fine (sundials_1en6 or be1)
    top_fold    = '/home/avanb/scratch/'

des_dir =  top_fold + 'statistics_temp'
fnl_dir =  top_fold + 'statistics'
src_dir =  top_fold + 'summa-' + method_name
ben_dir =  top_fold + 'summa-' + bench_name
src_pat = 'run1_G*_timestep.nc'
des_fil = method_name + '_hrly_diff_stats_{}_{}.nc'
settings= ['scalarSWE','scalarTotalSoilWat','scalarTotalET','scalarCanopyWat','averageRoutedRunoff','wallClockTime']

viz_fil = method_name + '_hrly_diff_stats_{}.nc'
viz_fil = viz_fil.format(','.join(settings))

# Make sure we're dealing with the right kind of inputs
src_dir = Path(src_dir)
fnl_dir = Path(fnl_dir)
ben_dir = Path(ben_dir)
des_dir = Path(des_dir)

# Ensure the output path exists
des_dir.mkdir(parents=True, exist_ok=True)

# Construct the path to the processed_files.txt file
processed_files_path = os.path.join(des_dir, 'processed_files.txt')

# Get the names of all inputs, assuming folders have same splits of domains and same file names
src_files = glob.glob(str( src_dir / src_pat ))
src_files.sort()
ben_files = glob.glob(str( ben_dir / src_pat ))
ben_files.sort()

# Load the list of files that have already been processed
if os.path.exists(processed_files_path):
    with open(processed_files_path, 'r') as f:
        processed_files = f.read().splitlines()
else:
    processed_files = []


# Filter out the files that have already been processed
src_files = [f for f in src_files if f not in processed_files]
ben_files = [f for f in ben_files if f not in processed_files]

# definitions for KGE computation
def covariance(x,y,dims=None):
    return xr.dot(x-x.mean(dims), y-y.mean(dims), dims=dims) / x.count(dims)

def correlation(x,y,dims=None):
    return (covariance(x,y,dims)) / (x.std(dims) * y.std(dims))

assert len(ben_files) == len(src_files), \
    'Found {} files but need {}!'.format(len(src_files), len(ben_files))

# -- test for corruption
#for (file, bench) in zip(src_files,ben_files):
#    # open file
#    try:
#        with xr.open_dataset(file), xr.open_dataset(bench) as ds:
#            # Do nothing if the file is successfully opened
#            pass
#    except:
#        # Log the file name or take other appropriate action if the file is corrupted
#        print('Error opening file:', file, bench)

# -- functions
def run_loop(file,bench,processed_files_path):

    # extract the subset IDs
    subset = file.split('/')[-1].split('_')[1]

    # acquire the lock before opening the file
    if not_parallel:
        dat, ben = xr.open_dataset(file), xr.open_dataset(bench)
    else:
        import multiprocessing as mp
        lock = mp.Lock()
        with lock:
            dat, ben = xr.open_dataset(file), xr.open_dataset(bench)
         
    # sometimes gives -9999 the whole run (non-compute), make these nan and plot as lowest value 0 in geographic
    dat = dat.where(dat!=-9999)
    ben = ben.where(ben!=-9999)
    # some weird negative values in runoff if not routed
    dat['averageRoutedRunoff'] = dat['averageRoutedRunoff'].where(dat['averageRoutedRunoff']>=0)
    ben['averageRoutedRunoff'] = ben['averageRoutedRunoff'].where(ben['averageRoutedRunoff']>=0) 
    
    # get rid of gru dimension, assuming hru and gru are one to one (everything now as hruId)
    dat = dat.drop_vars(['hruId','gruId'])
    m = dat.drop_dims('hru')
    m = m.rename({'gru': 'hru'})
    dat = dat.drop_dims('gru')
    dat = xr.merge([dat,m])  
    #dat = dat.where(dat.time!=dat.time[0],drop=True) #drop first timestep, weird
    dat = dat.isel(time=slice(24, None)) #drop first day, weird
    
    ben = ben.drop_vars(['hruId','gruId'])
    m = ben.drop_dims('hru')
    m = m.rename({'gru': 'hru'})
    ben = ben.drop_dims('gru')
    ben = xr.merge([ben,m])  
    #ben = ben.where(ben.time!=ben.time[0],drop=True) drop first timestep, weird
    ben = ben.isel(time=slice(24, None)) #drop first day, weird
    
    diff = dat - ben
    the_hru = np.array(ben['hru'])

    for var in settings:
        mean = dat[var].mean(dim='time')
        mean = mean.expand_dims("stat").assign_coords(stat=("stat",["mean"]))

        datnz = dat[var].where(np.logical_and(ben[var] != 0,dat[var] != 0))  # don't include both 0
        mnnz = datnz.mean(dim='time')
        mnnz = mnnz.expand_dims("stat").assign_coords(stat=("stat",["mnnz"]))

        mean_ben = ben[var].mean(dim='time')
        mean_ben = mean_ben.expand_dims("stat").assign_coords(stat=("stat",["mean_ben"]))

        datnz = ben[var].where(np.logical_and(ben[var] != 0,dat[var] != 0))  # don't include both 0
        mnnz_ben = datnz.mean(dim='time')
        mnnz_ben = mnnz_ben.expand_dims("stat").assign_coords(stat=("stat",["mnnz_ben"]))
        
        na_mx = np.fabs(dat[var]).max()+1
        amx = np.fabs(dat[var].fillna(na_mx)).argmax(dim=['time'])
        amax = dat[var].isel(amx).drop_vars('time')
        amax = amax.expand_dims("stat").assign_coords(stat=("stat",["amax"]))

        na_mx = np.fabs(ben[var]).max()+1
        amx = np.fabs(ben[var].fillna(na_mx)).argmax(dim=['time'])
        amax_ben = ben[var].isel(amx).drop_vars('time')
        amax_ben = amax_ben.expand_dims("stat").assign_coords(stat=("stat",["amax_ben"]))
        
        rmse = (np.square(diff[var]).mean(dim='time'))**(1/2) #RMSE SHOULD THIS BE NORMALIZED? colorbar will normalize
        rmse = rmse.expand_dims("stat").assign_coords(stat=("stat",["rmse"]))

        diffnz = diff[var].where(np.logical_and(ben[var] != 0,dat[var] != 0))  # don't include both 0
        rmnz = (np.square(diffnz).mean(dim='time'))**(1/2)
        rmnz = rmnz.expand_dims("stat").assign_coords(stat=("stat",["rmnz"]))

        na_mx = np.fabs(diff[var]).max()+1
        amx = np.fabs(diff[var].fillna(na_mx)).argmax(dim=['time'])
        maxe = diff[var].isel(amx).drop_vars('time')
        maxe = maxe.expand_dims("stat").assign_coords(stat=("stat",["maxe"]))

        r = correlation(dat[var],ben[var],dims='time')
        kgem = 1 - np.sqrt( np.square(r-1)
               + np.square( dat[var].std(dim='time')/ben[var].std(dim='time') - 1)
               + np.square( (dat[var].mean(dim='time')-ben[var].mean(dim='time'))/ben[var].std(dim='time') ) )

        #if constant and identical, want this as 1.0 -- correlation with a constant = 0 and std dev = 0\n",
        for h in the_hru:
            ss = dat[var].sel(hru=h)
            tt = ben[var].sel(hru=h)
            kgem.loc[h] =kgem.sel(hru=h).where(np.allclose(ss,tt, atol = 1e-10)==False, other=1.0)
        kgem = kgem/(2.0-kgem)
        kgem = kgem.expand_dims("stat").assign_coords(stat=("stat",["kgem"]))

        new = xr.merge([mean,mnnz,amax, mean_ben,mnnz_ben,amax_ben, rmse,rmnz, maxe, kgem])
        new.to_netcdf(des_dir / des_fil.format(var,subset))

   # write the name of the processed file to the file list, acquire the lock before opening the file
    if not_parallel:
        with open(processed_files_path, 'a') as filew:
            filew.write(file + '\n')
            filew.write(bench + '\n')
    else:
        import multiprocessing as mp
        lock = mp.Lock()
        with lock:
            with open(processed_files_path, 'a') as filew:
                filew.write(file + '\n')
                filew.write(bench + '\n')
    filew.close()  # close the file after writing to it

    return #nothing

def merge_subsets_into_one(src,pattern,des,name):

    '''Merges all files in {src} that match {pattern} into one file stored in /{des}/{name.nc}'''

    # this runs out of memory sometimes
    # Find all files
    #src_files = glob.glob(str( src / pattern ))
    # Merge into one
    #out = xr.merge([xr.open_dataset(file) for file in src_files])

    out = xr.open_mfdataset(str( src / pattern ))

    # save to file
    out.to_netcdf(des / name)

    return #nothing
# -- end functions


if not_parallel:
    # -- no parallel processing
    for (file, bench) in zip(src_files,ben_files):
        run_loop(file,bench,processed_files_path)
    # -- end no parallel processing

else:
    # -- start parallel processing
    ncpus = int(os.environ.get('SLURM_CPUS_PER_TASK',default=1))
    if __name__ == "__main__":
        import multiprocessing as mp
        pool = mp.Pool(processes=ncpus)
        with open(processed_files_path, 'a') as f:
            results = [pool.apply_async(run_loop, args=(file,bench,processed_files_path)) for (file, bench) in zip(src_files, ben_files)]
            for r in results:
                try:
                    r.get()
                except Exception as e:
                    print(f"Error processing file: {e}")
                    raise e
        pool.close()
    # -- end parallel processing


# merge the individual files into one for further vizualization
merge_subsets_into_one(des_dir,des_fil.replace('{}','*'),fnl_dir,viz_fil)

# remove the individual files for cleanliness
for file in glob.glob(str(des_dir / des_fil.replace('{}','*'))):
    os.remove(file)


#!/usr/bin/python3

# requirements
import csv
import pdb
import sys
import math
import getopt
import logging
import numpy as np
from netCDF4 import Dataset
from netCDF4 import date2num
from datetime import datetime

# local requirements
from lib.utils import *
from lib.seaoverland import *


# main
if __name__ == "__main__":

    #############################################################
    #
    # Configure a logger
    #
    #############################################################

    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger('MDK2_extract')
    logger.setLevel(logging.DEBUG)


    #############################################################
    #
    # read input data
    #
    #############################################################
    
    windFolder = currFolder = outFolder = dates = None
    
    try:
        options, rem = getopt.getopt(sys.argv[1:], 'd:o:w:u:c:h', ['dates=','windFolder=', 'currFolder=', 'outWindFolder=', 'outCurrFolder=', 'help'])
        for opt, arg in options:
            if opt in ('-d', '--dates'):
                dates = arg.split(",")
            elif opt in ('-w', '--windFolder'):
                windFolder = arg
            elif opt in ('-c', '--currFolder'):                
                currFolder = arg
            elif opt in ('-o', '--outWindFolder'):
                outWindFolder = arg
            elif opt in ('-u', '--outCurrFolder'):
                outCurrFolder = arg
            elif opt in ('-h', '--help'):
                printHelp(logger)
                sys.exit(0)
    
    except getopt.GetoptError:
        logger.error("Wrong arguments!")
        printHelp(logger)
        sys.exit(1)

    if (not dates) or (not windFolder) or (not currFolder) or (not outWindFolder) or (not outCurrFolder):
        logger.error("Wrong number of arguments!")
        printHelp(logger)
        sys.exit(1)    
    

    #############################################################
    #
    # read medslik.tmp
    #
    #############################################################
    
    mtmp = open("medslik.tmp","r")
    regn, icurrents, iwind = mtmp.readline().split()
    alon1, alon2 = mtmp.readline().split()[0:2]
    alat1, alat2 = mtmp.readline().split()[0:2]
    alon1 = float(alon1)
    alon2 = float(alon2)
    alat1 = float(alat1)
    alat2 = float(alat2)
    logger.info("Min latitude: %s" % alat1)
    logger.info("Max latitude: %s" % alat2)
    logger.info("Min longitude: %s" % alon1)
    logger.info("Max longitude: %s" % alon2)
    mtmp.close()
    
        
    #############################################################
    #
    # processing currents
    #
    #############################################################

    latitudes = None
    longitudes = None
    
    firstRound = True
    for date in dates:
        
        # debug info
        logger.info(" Parsing current files for date %s" % date)

        # build the file names
        inputFiles = []

        # generate list of files
        tFile = currFolder + "/" + date + "_T.nc"
        uFile = currFolder + "/" + date + "_U.nc"
        vFile = currFolder + "/" + date + "_V.nc"

        # open files
        tDataset = Dataset(tFile)
        uDataset = Dataset(uFile)
        vDataset = Dataset(vFile)

        # set variable names
        timevar = "time_counter"
        latvar = "nav_lat"
        lonvar = "nav_lon"
        tvar = "votemper"
        uvar = "vozocrtx"
        vvar = "vomecrty"

        # determine the number of timesteps
        timesteps = len(tDataset.variables[timevar])

        # if first round, then read lat and lon
        if firstRound:
            firstRound = False
            latitudes = tDataset.variables[latvar][:]
            longitudes = tDataset.variables[lonvar][:]

        # determine the window on which to crop data
        xwindow = np.logical_and(longitudes>=alon1, longitudes<=alon2)
        ywindow = np.logical_and(latitudes>=alat1, latitudes<=alat2)

        # crop data
        cropped_lon = longitudes[xwindow]
        cropped_lat = latitudes[ywindow]        
        cropped_t = tDataset.variables["votemper"][:,:,ywindow,xwindow]
        cropped_u = uDataset.variables["vozocrtx"][:,:,ywindow,xwindow]
        cropped_v = vDataset.variables["vomecrty"][:,:,ywindow,xwindow]

        # replace nan with 9999
        whereNaN = np.isnan(cropped_t)
        cropped_t[whereNaN] = 9999.
        whereNaN = np.isnan(cropped_u)
        cropped_u[whereNaN] = 9999.
        whereNaN = np.isnan(cropped_v)
        cropped_v[whereNaN] = 9999.
        
        # create .rel files (one for every timestep)
        for t in range(timesteps):

            # invoke seaoverland on u surface
            u_srf = cropped_u[t,0,:,:]
            seaoverland(u_srf, 2)
            cropped_u[t,0,:,:] = u_srf

            # invoke seaoverland on v surface
            v_srf = cropped_v[t,0,:,:]
            seaoverland(v_srf, 2)
            cropped_v[t,0,:,:] = v_srf
            
            # determine the date and time
            curr_time = "%2.0f:00" % t
            curr_date = "%s/%s/%s" % (date[0:2], date[2:4], date[4:6])
            
            # build the file name
            relFile = "%s/relo%s%s.rel" % (outCurrFolder, date, str(t).zfill(2))
            rf = open(relFile, "w")
            
            # generate a rel file
            logger.info(" Generating file %s" % relFile)
            
            # write heading
            rf.write("MERCATOR model 9 km forecast data for %s %s\n" % (curr_date, curr_time))
            rf.write("Subregion of the Global Ocean:\n")
            rf.write("%f  %f  %f  %f  %s  %s  Geog. limits\n" % (cropped_lon.min(), cropped_lon.max(),
                                                                 cropped_lat.min(), cropped_lat.max(),
                                                                 len(cropped_lon), len(cropped_lat)))
            rf.write("  %s\t0.0\n" % cropped_t[t,0,:,:].count())
            rf.write(f'    {"lat": <10} {"lon": <10} {"SST": <10} {"u_srf": <10} {"v_srf": <10} {"u_10m": <10} ')        
            rf.write(f'{"v_10m": <10} {"u_30m": <10} {"v_30m": <10} {"u_120m": <10} {"v_120m": <10}\n')
            
            # write the file content
            for ind_lon in range(len(cropped_lon)):
                for ind_lat in range(len(cropped_lat)):

                    # read latitude and longitude
                    lat = cropped_lat.data[ind_lat]
                    lon = cropped_lon.data[ind_lon]

                    # read sea surface temperature
                    sst = cropped_t[t,0,ind_lat,ind_lon]

                    # read u and v at 0, 10, 30 and 120m
                    u = cropped_u[t,:,ind_lat,ind_lon]
                    v = cropped_v[t,:,ind_lat,ind_lon]

                    # print only lines where not all the values are masked
                    # since these values represent the land
                    if not((u.count() == 0) and (v.count() == 0)):
                        rf.write(f'    {lat: <10.4f} {lon: <10.4f} {sst: <10.4f} {u.data[0]: <10.4f} {v.data[0]: <10.4f} {u.data[1]: <10.4f} ')
                        rf.write(f'{v.data[1]: <10.4f} {u.data[2]: <10.4f} {v.data[2]: <10.4f} {u.data[3]: <10.4f} {v.data[3]: <10.4f}\n')

            # close file
            rf.close()
                        
        # print an empty line to have a better output...
        logger.info(" ")

        
    #############################################################
    #
    # processing winds
    #
    #############################################################
    
    latitudes = None
    longitudes = None
    timesteps = None

    # set variable names
    timevar = "time"
    latvar = "lat"
    lonvar = "lon"
    
    firstRound = True
    for date in dates:
        
        # debug info
        logger.info(" Parsing winds files for date %s" % date)

        # build the filename
        inputFile = windFolder + "/" + "20" + date + ".nc"
        
        # debug info        
        logger.info(" Processing winds file %s" % inputFile)        
        
        # open wind file
        wDataset = Dataset(inputFile)
        
        # if first round, then read lat and lon
        if firstRound:
            firstRound = False

            # determine latitudes and longitudes
            latitudes = wDataset.variables[latvar][:]
            longitudes = wDataset.variables[lonvar][:]

            # determine the number of timesteps
            timesteps = len(wDataset.variables[timevar])

        # determine the window on which to crop data
        xwindow = np.logical_and(longitudes>=alon1, longitudes<=alon2)
        ywindow = np.logical_and(latitudes>=alat1, latitudes<=alat2)        

        # crop data
        cropped_lon = longitudes[xwindow]
        cropped_lat = latitudes[ywindow]
        cropped_u = wDataset.variables["U10M"][:,ywindow,xwindow]
        cropped_v = wDataset.variables["V10M"][:,ywindow,xwindow]

        # replace nan with 9999
        whereNaN = np.isnan(cropped_u)
        cropped_u[whereNaN] = 9999.
        whereNaN = np.isnan(cropped_v)
        cropped_v[whereNaN] = 9999.

        # apply seaoverland
        for t in range(timesteps):

            # sea overland on u
            u_so = cropped_u[t,:,:]
            seaoverland(u_so, 1)
            cropped_u[t,:,:] = u_so

            # sea overland on v
            v_so = cropped_v[t,:,:]
            seaoverland(v_so, 1)
            cropped_v[t,:,:] = v_so
        
        # create .sk1 files (one for date)
        skFile = "%s/sk1_%s.sk1" % (outWindFolder, date)
        sf = open(skFile, "w")

        # write headers
        curr_date = "%s/%s/%s" % (date[0:2], date[2:4], date[4:6])
        sf.write("SKIRON forecast data for %s\n" % curr_date)
        sf.write("Subregion of the Global Ocean with limits:\n")
        sf.write("%f  %f  %f  %f  %s  %s  Geog. limits\n" % (cropped_lon.min(), cropped_lon.max(),
                                                             cropped_lat.min(), cropped_lat.max(),
                                                             len(cropped_lon), len(cropped_lat)))
        sf.write("  %s\t0.0\n" % cropped_u[0,:,:].count())
        
        sf.write(f'    {"lat": <7} {"lon": <7} ')
        for t in range(timesteps):
            sf.write(f'{"u%s": <7} {"v%s": <7} ' % (str(t).zfill(2), str(t).zfill(2)))
        sf.write("\n")

        # write file content
        for ind_lon in range(len(cropped_lon)):
            for ind_lat in range(len(cropped_lat)):

                # get lat and lon
                lat = cropped_lat.data[ind_lat]
                lon = cropped_lon.data[ind_lon]
                
                # print only lines where not all the values are masked
                # since these values represent the land
                if not(cropped_u[:,ind_lat,ind_lon].count() and cropped_v[:,ind_lat,ind_lon].count()):
                    sf.write(f'{lat: <7} {lon: <7} ')
                    for t in range(timesteps):
                        sf.write(f'{wDataset.variables["U10M"][t,ind_lat,ind_lon]: <10.4f} {wDataset.variables["V10M"][t,ind_lat,ind_lon]: <10.4f} ')
                    sf.write("\n")
                
        # close wind files
        wDataset.close()
        sf.close()
        
        # print an empty line to have a better output...
        logger.info(" ")

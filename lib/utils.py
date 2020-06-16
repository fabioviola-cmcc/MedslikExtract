#!/usr/bin/python

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


def printHelp(logger):

    logger.info("")
    logger.info("   === Medslik extract.py ===")
    logger.info("")
    logger.info("   You must invoke the extract with the mandatory arguments:")
    logger.info("   --dates=")
    logger.info("   --windFolder=")
    logger.info("   --currFolder=")
    logger.info("   --outFolder=")
    logger.info("")
    logger.info("   Example:")
    logger.info("   $ python3 extract.py --dates=20201005,20201006,20201007 --windFolder=input/Sk1 --currFolder=input/H3k --outFolder=output")
    logger.info("")

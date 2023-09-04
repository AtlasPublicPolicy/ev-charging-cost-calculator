'''
Main file for the Calculator. This file is the entry point for the program but 
all it does is call the mainMenu function from the interface file. This file
is only here to give the program a main file to run from in a terminal

Built by Atlas Public Policy in Washington, DC
2023

Principal author: James Di Filippo

'''

import lib.interfaceFunctions as itf
import sys
import logging
import traceback
import time

# start logfile
try:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    logging.basicConfig(filename=f'logs/log{timestamp}.txt',
                     level=logging.DEBUG,
                     filemode='w',
                     format='%(asctime)s %(levelname)s %(message)s',
                     datefmt='%m/%d/%Y %I:%M:%S %p')
except Exception as e:
    print('could not create log file\n'
          f'(because {e})')
    input('press enter to exit')
    sys.exit()

# log uncaught exceptions and inform user of crash
def log_exceptions(type, value, tb):
    for line in traceback.TracebackException(type, value, tb).format(chain=True):
        logging.exception(line)
    logging.exception(value)

    # prompt user that an error has occurred and to check the log file
    print('***A fatal error has occured***\n' 
          'Please check the log file for details.')
    input('Press enter to exit.')
    # call default excepthook
    sys.__excepthook__(type, value, tb)

sys.excepthook = log_exceptions


# run the main menu

itf.mainMenu()
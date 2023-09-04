'''
this file sets up the directory and installs the required packages for the rate
calculator. It should only need to be run once.

Built by Atlas Public Policy in Washington, DC
2023
'''

import sys
import subprocess
import os  

libraries = [ 
    'pandas', 
    'numpy', 
    'pick', 
    'alive_progress',
    'openpyxl',
    'xlsxwriter'
 ]

try:
    for lib in libraries:
        subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
except Exception as e:
    print('could not install libraries\n'
          f'(because {e})')
    input('press enter to exit')

print('libraries installed')

# create directory structure

file_structure = [
'results',
'cached_data',
'logs'
 ]

try:
    for dirs in file_structure: os.mkdir(dirs)
except Exception as e:
    print('could not create project directory\n'
          f'(because {e})')
    print('please create the following folders in the software directory manually:\n'
          f'{file_structure}')
    input('press enter to exit')
    sys.exit()

print('directory structure created')

# end of file message
input('setup complete...press enter to exit')
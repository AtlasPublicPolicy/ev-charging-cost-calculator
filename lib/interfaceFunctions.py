'''
interfaceFunctions.py is a module of the rate calculator tool. It contains
functions that are used to create the user interface for the tool.

functions are organized into:
    - menus
    - user inputs

Built by Atlas Public Policy in Washington, DC
2023
'''


# external dependencies
from pick import pick
import string
import time
import os
import re
import logging

# internal dependencies
import lib.calculatorFunctions as calc
import lib.inputFunctions as imp 
import lib.outputFunctions as out

######################### MENUS ###############################################3

def mainMenu():
    '''
    main menu for the rate calculator tool. Uses pick to create a menu for 
    the user to select from nd calls the appropriate function based on the
    user's selection

    Main Menu Options are:
        RUN RATE CALCULATOR
        REFRESH CACHE
        OPEN INPUT WORKBOOK
        EXIT

    possible future improvements:
        - add a help option that opens the readme file
        - create a dictionary of messages for interfaceFunctions
          so that the menu code can be more easily read and text can 
          be more easily updated
        - refactor if/elif statements into a case statement

    '''
    

    message = ''' 
    Welcome to Atlas Public Policy's Rate Calculator tool. 

    This tool is free, open source and is offered without warranty. Please
    see the README.md file for more information about the tool.
    
    Before you begin:
      1. fill in the inputs in the rate_inputs workbook
      2. ensure you have an internet connection before refreshing the cache

    The tool requires a prebuilt cache of rate data from the openEI rate database.
    If you have not built the cache, the tool will automatically build it for you. 
    If you want to refresh the cache with the latest data from openEI, select the
    refresh cache option
    '''
    # main menu loop that will continue to run until the user selects exit
    while True:

        # top level menu
        xInput, i = pick(
            ['RUN RATE CALCULATOR', 
             'REFRESH CACHE',
             'OPEN INPUT WORKBOOK', 
             'EXIT'],

        message,
        indicator='>> '
        )

        # this could probably be a case statement
        # if the user selects run rate calculator, call the calcMenu function
        # to launch the calcMenu submenu.
        if xInput == 'RUN RATE CALCULATOR':
            calcMenu()

        # if the user selects refresh cache, call the buildCache function
        elif xInput == 'REFRESH CACHE':
            imp.buildCache()
            logging.info('cache built without error')
            input('press enter to return to menu')

        # if the user selects open input workbook, call the openExcelFile
        # function to open the input workbook in excel on the user's machine
        elif xInput == 'OPEN INPUT WORKBOOK':
            filepath = selectFile('user_input/')
            out.openExcelFile(f'user_input/{filepath}')
            logging.info(f'opened {filepath} without error')
            input('press enter to return to menu')

        # if the user selects exit, exit the program
        elif xInput == 'EXIT':
            print('Exiting program...')
            logging.info('user exited script without error')
            time.sleep(2)
            raise SystemExit
# -----------------------------------------------------------------------------


def calcMenu():
    '''
    Submenu for the rate calculator tool. Uses pick to create a menu for
    the user to select / input objects (prefixed with x) are passed to the
    calculator function.

    future updates:
        - pull messages into a dictionary
    '''
    # calc menu loop that will continue to run until the user selects exit
    while True:
    
    # user select input file from the input directory.
        message = '''
    Do you wish to use the default input file (rate_calculator_input_file.xlsx) 
    or select a different file from the user_input directory?
        '''
        iInputFile, i = pick(
            ['Default', 'Select'],
            message,
            indicator = '>> '
        )

        if iInputFile == 'Default':
            iInputFile = 'user_input/rate_calculator_input_file.xlsx'

        elif iInputFile == 'Select':
            iInputFile = selectFile('user_input/')
            print(f'You selected {iInputFile}')
            iInputFile = 'user_input/' + iInputFile


    # filter options for the rate calculator, the filter options restrict the
    # set of rates that are used in the calculator.
   
        message = '''
    You may select from the following rate sets or subsets to calculate costs 
    Filtered rates are current and easily identified specialty rates have been
    removed through keyword detection.

    Choose 'All rates in URDB if you wish to get all rates (including historical)    
        '''
        iFilter, i = pick(
            ['All Filtered Rates',
            'Filtered Residential Rates',
            'Filtered Commercial Rates',
            'Filtered Industrial Rates',
            'All Rates in URDB'],
            message,
            indicator='>> '
            )
    

    # user input for the number of days per week that user vehicles will charge
    # this input is used to determine the overall charging use of the vehicle(s)
        message = '''
    How many days a week will vehicles charge? The number of days per week will 
    determine overall charing use.
        '''
        iDayString, iDays = pick(
            ['1 day','2 days','3 days','4 days','5 days','6 days','7 days'],
            message,
            indicator='>> '
        )
        iDays =+ 1

    # user input for the power and charging curve to use in the calculator.
    # if the user selects single, the single power and charging curve will be 
    # read in from the input file. If the user selects monthly, the monthly
    # power and charging curve will be read in from the input file.

        message = '''
    Would you like to use the single power and charging curve or the monthly
    power and charging curve? If you have not filled out the input file for your
    selection you will get an error.
        '''
        iCurve, i = pick(
            ['Single', 'Monthly'],
            message,
            indicator = '>> '
        )

    # user input for the output file name. If the user selects default, the
    # output file will be named output.xlsx. If the user selects custom, the
    # user will be prompted to enter a custom file name using getValidFilename
        message = '''
    Do you want to use the default output file name (rate_calculator_output.xlsx)? 
    or create a custom filename to save results to? Alternatively, you can use the
    input filename that will save with a '_output' suffix.

    NOTE: The output file will be overwritten if it already exists.
        '''
        iOutFile, i = pick(
            ['Default', 'Custom', 'Use Input Filename'],
            message,
            indicator = '>> '
        )
    
        if iOutFile == 'Custom':
            message = '''
            
    Please enter the name of the output file you would like to use. Use unique
    names for each run of the calculator to avoid overwriting previous results.

     * Do not include a file extension. 
     * Valid characters are letters, numbers,spaces, underscores and dashes.
     * Non-valid characters will be removed from the filename automatically
                  '''
            iOutFile = getValidFilename()

        elif iOutFile == 'Use Input Filename':
            iOutFile = iInputFile[11:-5] + '_output'

        elif iOutFile == 'Default':
            iOutFile = 'rate_calculator_output'
    
    # confirm the user's selections before running the calculator
        message = ('you have selected:\n'
                   f' 1.  Input file: {iInputFile[11:-5]}\n' 
                   f' 2.  {iFilter}\n'
                   f' 3.  {iDayString} per week\n'
                   f' 4.  {iCurve} input file\n'
                   f' 5.  Output file: {iOutFile} \n\n'
                  'Is this correct? Selecting yes will kick off rate calculator.\n'
                  'Selecting no will let you reselect options. Exiting will return\n'
                  'you to the main menu.'
                  )

        xChoice, i = pick(
        ['Yes', 'No', 'Exit'],
        message,
        indicator = '>> '
        )

        # if user confirms selections, run the calculator 
        if xChoice == 'Yes':
            print('running calculator...\n')
            calc.calcRun(iInputFile, iFilter, iDays, iCurve, iOutFile)
            input('operation complete, press enter to return to main menu') 
            mainMenu()
        
        # if user selects no, return to the top of the calcMenu loop
        elif xChoice == 'No':
            print('re-selecting options...')
            continue

        # if user selects exit,
        elif xChoice == 'Exit':
            exitOrMain('leaving rate calculator...')
    

############################# USER PROMPTS #####################################

def exitOrMain(passedMessage):
    '''
    Asks the user if they want to exit the program or return to the main menu.
    '''
    message = (f'{passedMessage}\n'
              'Do you want to exit or return to the main menu?')
    xExit, i = pick(['MAIN MENU', 'EXIT'], 
                    message,
                    indicator='>> ')
    if xExit == 'EXIT':
        print('Exiting program...')
        time.sleep(2)
        raise SystemExit
    elif xExit == 'MAIN MENU':
        mainMenu()
# ------------------------------------------------------------------------------
def selectFile(dir):
    '''
    provide a list of files in the directory and ask the user to select one

    to do:
        - read in and verify the file here instead of in the calc module
    '''
    
    title = '''
    Select an input file from the user_input directory below. Selected file must
    be a filled copy of the rate_calculator_input_file.xlsx file otherwise you
    will get an error.
    
    If your file does not appear in this list, click exit return to the main menu. 
    verify that your file is in the correct directory and has the proper extension
    (xlsx) and try again.
    '''

    # get a list of files in the directory
    options = os.listdir(dir)
    # remove any files that are not xlsx files
    options = [x for x in options if x.endswith('.xlsx')]

    options.append('Exit')
    option, index = pick(options, title)
    if option == 'Exit':
        exitOrMain('leaving file selection...')
    return option

# ------------------------------------------------------------------------------
def askOpenFile(filepath):
    '''
    Asks the user if they want to open the file that was just created.
    runs openExcelFile if the user selects yes.
    '''
    message = (f'Results saved in {filepath}.xlsx\n'
                'do you want to open the file?')
    xOpen, i = pick(['YES', 'NO'], 
                    message,
                      indicator='>> ')
    
    if xOpen == 'YES':
        out.openExcelFile(f'results/{filepath}.xlsx')

# ------------------------------------------------------------------------------
def getValidFilename():
    '''
    Input function for user text input
    excludes invalid characters from filenames
    '''
    while True:
        filename = input('key in filename and press enter: ')
        if filename != '':
            valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
            filename = ''.join(c for c in filename if c in valid_chars)
            # remove xlsx, xls, and csv file extensions if they are included using regex
            filename = re.sub(r'\.xlsx$|\.xls$|\.csv$', '', filename)
            return filename
        else:
            print('please enter a filename')
            continue

'''
imputFunctions.py is a module of the rate calculator tool. It contains
functions that are used to import and process input data used by the tool.

functions are split into:
    - user input functions:
    - rate filtering functions
    - rate processing functions
    - cache building functions
    - validation functions

Built by Atlas Public Policy in Washington, DC
2023
'''

# external dependencies
from alive_progress import alive_it
import pandas as pd
from pick import pick
import time
import urllib.request
import gzip
import json
import pickle
import os
import logging

# internal dependencies
import lib.interfaceFunctions as itf

####################### USER INPUT AND VALIDATION ##############################

def getUserFile(inputfile, sheet):
    '''
    import user input file from the user_input folder based on
    sheet argument. If the file is not found,
    the user is given the option to try again or exit to the main menu. If the
    user selects try again, the function will loop until the file is found,
    the user selects exit, or the user exceeds 5 tries.
    '''
    
    check = ''

    for i in range(5):
        if check == 'Exit':
            print('User terminated session. Exiting calculator...')
            itf.exitOrMain()
        
        try:
            # read the user input file
            userinputs = readFile(inputfile, sheet)
            return userinputs
        
        except FileNotFoundError:
            print('file not found')
            message = ('Error: could not find rate_calculator_input_files.xlsx '
                       'in the input folder. Please ensure the file is in the '
                       'directory and try again.')
            check, i = pick(['Try Again', 'Exit'], message, indicator='>> ')

        except PermissionError:
            message = ('file is open in another program (likely excel). Please' 
                       'close the file and try again.')
            check, i = pick(['Try Again', 'Exit'], message, indicator='>> ')

        except Exception as e:
            print('Error: ', e)
            input('press any key to exit')
            itf.exitOrMain()
            
    input('number of tries exceeded...press any key')
    itf.exitOrMain()

# ---------------------------------------------------------------------------- #

def readFile(inputfile, sheet):
    '''
    read the user input file from the user_input folder. 
    ignores first line if sheet is 'Monthly'
    '''

    if sheet == 'Monthly':
        userinputs = pd.read_excel(inputfile, 
                               sheet_name = sheet, 
                               header = 1)
        
    elif sheet == 'Single':
        userinputs = pd.read_excel(inputfile, sheet_name=sheet)
    
    return userinputs 

def validateInput(energy, power):
    '''
    validate the user input file (all fields have values). If the file is 
    valid, continue to the next step. If the file is invalid, inform user 
    and return to the main menu.
    '''

    # if there are any nan values in the input, raise an error
    if (any([any([pd.isna(i) for i in j]) for j in energy]) 
        or any([any([pd.isna(i) for i in j]) for j in power])):
        print('Error: energy input file contains empty cells. Please '
              'ensure all cells in rate_calculator_input_file are' 
              'filled in and try again.')
        input('press any key to return to main menu')
        itf.mainMenu()
    
    # if there are any negative values in the input, raise an error
    if (any([any([i < 0 for i in j]) for j in energy])
        or any([any([i < 0 for i in j]) for j in power])):
        print('Error: energy input file contains negative values. Please '
              'ensure all cells in rate_calculator_input_file are' 
              'positive and try again.')
        input('press any key to return to main menu')
        itf.mainMenu()

    print('\nuser input file validated successfully')

# ---------------------------------------------------------------------------- #            
def parseUserInputs(inputfile, type):
    '''
    Parent function for parsing user inputs. Takes a type argument (monthly or 
    single) and returns a list of energy and power values. If the user input
    file is not found, the validation function will return an error and the
    user will be returned to the main menu.
    '''
    
    # get user input file from user_input folder, if it doesnt exist, warn user
    user_input = getUserFile(inputfile, type)
    
    # parse user input file into energy and power lists
    # single rate inputs are repeated for each month
    try:
        if type == 'Single':
            energy = user_input['Average Energy (kWh)'].tolist()
            energy = [energy for i in range(12)]
            power = user_input['Peak Power (kW)'].tolist()
            power = [power for i in range(12)]

    # monthly rate inputs are parsed into lists
        elif type == 'Monthly':
            energy = user_input.iloc[0:24,1:13]
            energy = energy.values.tolist()
            power = user_input.iloc[27:52,1:13]
            power = power.values.tolist()
        # take 24 x 12 list and convert to 12 x 24 list
            energy = [[energy[j][i] for j in range(len(energy))]
                    for i in range(len(energy[0]))]
            power = [[power[j][i] for j in range(len(power))]
                    for i in range(len(power[0]))]
    
    except:
        print('Error: could not parse user input file. Please ensure the '
              'file is correctly formatted and try again.')
        input('press any key to return to main menu')
        itf.mainMenu()

    # validate the user input file (all fields have values). If the file is
    # invalid, inform user and return to the main menu.
    validateInput(energy, power)

    return energy, power

################### Rate Filtering Function ###################################

def rateFilter(rates):
    '''
    method for building cached rate filter
    just a long set of negative filters for:
        - old rates
        - lighting rates
        - specialty rates not used for EV charging (found by keyword) 

    takes the rates dataframe as an argument and returns a dataframe 
    is used for filtering rates

    feature improvement:
        - refactor code to use an external list of keyword filters that
          can be easily updated or user-specified
    '''

    # -------- remove old rates ------------------------------------------------
    # many of the rates in the openei database are old and no longer in use or
    # have been replaced by newer versions. This section removes rates that have
    # ended before the current year or have no end date. Users can select the
    # unfiltered rates for historical analysis.

    # convert enddate to datetime
    rates['enddate'] = pd.to_datetime(rates['enddate'])
    # current year
    current = pd.to_datetime('today')
    # remove rates that ended before current year or have no end date
    rates = rates[(rates['enddate'] >= current) | (rates['enddate'].isnull())]

    print(f'{len(rates)} current rates.')

    # -------- remove lighting rates ----------------------------------------------
    # lighting rates are unlikely to be used for EV charging
    rates = rates[rates['sector'] != 'Lighting']
    print(f'{len(rates)} commercial, residential, & industrial rates.')

    # -------- keyword filtering --------------------------------------------------
    # many specialty rates are not applicable to EV charging. This section removes
    # rates that are unlikely to be used for EV charging through keyword filtering. 

    # list of keywords to filter out
    keywords = ['agriculture',
                 'water heat',
                 'space heat',
                 'space cool',
                 'unmetered',
                 'irrigation',
                 'pumping']
    
    # remove rates with keywords in the name field
    for i in keywords:
        rates = rates[~rates['name'].str.contains(i, case=False, na=False)]

    print(f'{len(rates)} keyword filtered rates.')

    # -------- create rate set ---------------------------------------------------
    # output dataframe with only rate label and sector
    # the label field is used to subset the full rate database
    # the sector field is used to subset further filter rates by sector
    filtered = rates[['label', 'sector']]
    filtered.to_pickle('cached_data/filtered.pkl')

#################### Rate Data Preprocessing Functions #########################

def unNestList (list):
    '''
    helper function to unnest a list of lists
    '''
    try:
        return [item for sublist in list for item in sublist]
    except:
        return list
# ------------------------------------------------------------------------------

def getMax (strux, tiernm):
    '''
    function to get max values from the json extract
    called by getStrux function
    '''
    # if max is not in the json extract return None (no tiers)
    try: 
        strux[0][tiernm][0]['max'] # throws error because next wont ¯\_(ツ)_/¯
        return [[i[tiernm][x]['max'] for x in range(len(i[tiernm])-1)]
                 for i in strux]
    except:
        return None
# ------------------------------------------------------------------------------

def getRate (strux, tiernm):
    '''
    function to get rate values from the json extract
    called by getStrux function
    '''

    # if adj is in the json extract, add it to the rate
    try:
        return [[(x['rate'] + x['adj'])
                    for x in i[tiernm]]
                    for i in strux]
    
    # otherwise, just return the rate by itself
    except KeyError:
        try: 
            return [[x['rate']
                     for x in i[tiernm]]
                     for i in strux]
        
    # if neither rate or adj are in the json extract, return None
        except KeyError:
            return None
# ------------------------------------------------------------------------------

def getStrux (rData, type):
    '''
    function to get strux values from the json extract based on type
     * valid type values are 'energyRate', 'demandRate', and 'flatDemand'
     * called by rateProcess function
     * returns max and rate values in a tuple
    '''

    # create strux and tier names based on type
    struxnm = f'{type}Strux'
    tiernm = f'{type}Tiers'
    
    # if struxnm is not in the json extract, return 2x none tuple
    # (indicates no rates of that type)
    try: 
        strux = rData[struxnm]
    except KeyError:
        return None, None
    
    # otherwise, return max and rate values in a tuple
    return (getMax(strux, tiernm),
            getRate(strux, tiernm))
# ------------------------------------------------------------------------------

def getSchedule (rdata, type):
    '''
    function to get schedule values from the json extract based on type
     * valid type values are 'energy' and 'demand'
     * called by rateProcess function
    '''

    # if schedule is not in the json extract, return 2x none tuple
    # (indicates no schedule of that type)
    # otherwise, return weekday and weekend schedules (24x12x arrays) in a tuple
    try:
        return (rdata[f'{type}WeekdaySched'],
                rdata[f'{type}WeekendSched'])
    except KeyError:
        return None, None
# ------------------------------------------------------------------------------
    
def mapSchedule (sched, value):
    '''
    function to map rate values to schedule periods for TOU rates
     * valid type values are 'energy' and 'demand'
     * valid sched inputs are 24x12 arrays of periods
     * called by rateProcess function
    '''

    # if sched is None, return None, otherwise map values to schedule and return
    # a 24x12 array (24 hours and 12 months) 
    try:
        return [[value[i] for i in x] for x in sched]
    except TypeError:
        return None
    
    # if there is an IndexError, the schedule in the data is invalid
    # (i.e. there are more periods in the schedule than there are values)
    except IndexError:
        return 'schedule invalid'
# ------------------------------------------------------------------------------

def createMonScedule (sched):
    '''
    URDB represents Tiered rate schedules with a 24x12 array of periods
    however, because the calculator doesnt support tiered rates with TOU 
    periods we only need to know which period each month is in
     * this function takes in a 24x12 array and returns a 12x list of periods
     * if there are any TOU periods, it returns 'schedule invalid'
     * called by rateProcess function 
    '''

    # test if all values are same in nested lists in sched (supported rate)
    if all([all([x == i[0] for x in i]) for i in sched]): # maybe get rid of the list comprehension inside the all function
            return [i[0] for i in sched]
    
    # otherwise, return 'schedule invalid' (unsupported rate)
    else:
        return 'schedule invalid'
# ------------------------------------------------------------------------------

def mapMonSchedule (sched, value):
    '''
    function to map rate values to monthly schedule periods for TOU rates
     * valid type values are 'energy' and 'demand'
     * valid sched inputs are 12x lists of periods
     * called by rateProcess function
     '''

    # if sched is None, return None, otherwise map values to schedule and return
    try:
        return [value[i] for i in sched]
    except TypeError:
        return None
    # if there is an IndexError, the schedule in the URDB contains more periods
    # than there are values to map to them.
    except IndexError:
        return 'schedule invalid'

# -------------------------- Main Function -------------------------------------

def rateProcess (rateData):
    '''
    main process for creating rate data dictionary

    takes in rateData dictionary entries read from json file and returns a 
    dictionary of analysis-ready rate data using the following functions:
        getStrux
        getSchedule
        mapSchedule
        createMonSchedule
        mapMonSchedule

    outputs dictionary with either data or none for each key. Whether or not
    there is data for each key will control flow of the calculator.

    to do - refactor to into separate functions for each rate type and a main 
            function that calls them. This will make it easier to maintain.
    '''

    # logic to determine which  rate type is present. outputs are captured in
    # lists of four values which will be mapped to the dictionary keys

    #----------------------------- energy rates -------------------------------#
    # energy strux fucntion runs
    maxNRG, rateNRG = getStrux(rateData, 'energyRate')
    # energy schedule function runs
    wkdNRG, wkeNRG = getSchedule(rateData, 'energy')

    # if maxNRG is None but rateNRG is not None, it is a TOU or flat rate
    if maxNRG is None and rateNRG is not None:
    # no tiers so unnest NRG rate list
        rateNRG = unNestList(rateNRG)
        nrg = [False, False,
               mapSchedule(wkdNRG, rateNRG),
               mapSchedule(wkeNRG, rateNRG)]
    
    # if maxNRG is not None and rateNRG is not none it is a tiered rate
    elif maxNRG is not None and rateNRG is not None:
        sched = createMonScedule(wkdNRG)
        # sched unsupported if not all values are same in nested lists (i.e. TOU)
        if sched != 'schedule invalid':
            nrg = [
                mapMonSchedule(sched, maxNRG),
                mapMonSchedule(sched, rateNRG), 
                False, False]
        else:
            nrg = ['unsupported', 'unsupported', 'unsupported', 'unsupported']
               
    elif maxNRG is None and rateNRG is None:
        nrg = [False, False, False, False]   

    elif maxNRG is not None and rateNRG is None:
        nrg = ['unsupported', 'unsupported', 'unsupported', 'unsupported'] 

    #-------------------------- TOU demand rates ------------------------------#

    maxDemandTou, rateDemandTOU = getStrux(rateData, 'demandRate')
    # tou schedule function runs
    wkdDemandTOU, wkeDemandTOU = getSchedule(rateData, 'demand')

    # logic for assigning TOU demand depending on whether or not there is data
    if maxDemandTou is None and rateDemandTOU is None:
        touDemand = [False, False]
    
    elif rateDemandTOU is not None and maxDemandTou is None:
        rateDemandTOU = unNestList(rateDemandTOU)
        touDemand = [
            mapSchedule(wkdDemandTOU, rateDemandTOU),
            mapSchedule(wkeDemandTOU, rateDemandTOU)]
        
    elif maxDemandTou is not None: # tiers unsupported
        touDemand = ['unsupported', 'unsupported']        
    
    # ------------------------- flat demand rates -----------------------------#
 
    # flat demand strux
    maxDemandFlat, rateDemandFlat = getStrux(rateData, 'flatDemand')

    # is there a flat demand schedule?
    try:
        monSched = rateData['flatDemandMonths']
    except:
        monSched = None
        
    # logic for assigning flat demand depending on whether or not there is data
    if rateDemandFlat is None and maxDemandFlat is None:
        flatDemand = [False, False]
    
    elif (rateDemandFlat is not None
           and maxDemandFlat is None
           and monSched is not None):
        
        flatDemand = [
            mapMonSchedule(monSched, rateDemandFlat),
            False
        ]

    elif (maxDemandFlat is not None 
          and rateDemandFlat is not None
          and monSched is not None):
        
        flatDemand = [
            mapMonSchedule(monSched, rateDemandFlat),
            mapMonSchedule(monSched, maxDemandFlat)
        ]

    elif (maxDemandFlat is not None, rateDemandFlat is None):
        flatDemand = ['unsupported', 'unsupported']
    
    elif (monSched is None):
        flatDemand = ['unsupported', 'unsupported']

    cats = ['nrgTierMax', 'nrgTierRates', 'nrgTOUWkdRates', 'nrgTOUWkeRates',
            'demandTOUwkdRates', 'demandTOUwkeRates', 'demandFlatRates',
            'demandFlatMax']

    # append nrg, touDemand, and flatDemand to a single list
    allout = nrg + touDemand + flatDemand
    # stich together all the lists into a single list
    outDict = {k:v for k,v in zip(cats, allout)}
    
    outDict['id'] = rateData['_id']['$oid']
    # rate details if present
    details = ['rateName', 'utilityName', 'eiaId', 'sector',
                'fixedChargeFirstMeter', 'sourceReference',
                'description', 'demandMax', 'demandMin']
    for i in details:
        try:
            outDict[i] = rateData[i]
        except:
            outDict[i] = False
        
    return outDict


################## Cache Building Functions ####################################

def getRateJson ():
    '''
    function to download the URDB json file and return it as a dictionary 
    where the key is the rate id
    
    to do -
        - move error messages to a separate function so they dont clutter 
          the code
    '''

    url = 'https://openei.org/apps/USURDB/download/usurdb.json.gz'
    # download .gz file

    # big error message to catch user attention if problem getting file
    try: 
        urllib.request.urlretrieve(url, 'cached_data/urdb_data.json.gz')
    except Exception as e:
        if '404' in str(e):
            message = '''
    #####################################################################
    #        !!!!!FATAL ERROR: FILE COULD NOT BE DOWNLOADED!!!!!        #
    #                                                                   #
    #                   * File not found on openEI *                    #
    #         *Check openei.org/apps/USURDB/download/usurdb.json.gz *   #
    #                                                                   #
    #                   Script will close in 10 seconds                 #
    #                                                                   #
    #####################################################################
           
           '''
            print(message)
            logging.error(f'error downloading file: {e}')
            time.sleep(10)
            raise SystemExit

        else:    
            message = '''
    #####################################################################
    #        !!!!!FATAL ERROR: FILE COULD NOT BE DOWNLOADED!!!!!        #
    #                                                                   #
    #                   * Check internet connection*                    #
    #                                                                   #
    #                   Script will close in 10 seconds                 #
    #                                                                   #
    #####################################################################
           
           '''
            print(message)
            logging.error(f'error downloading file: {e}')
            time.sleep(10)
            raise SystemExit

    with gzip.open('cached_data/urdb_data.json.gz', 'rb') as f:

        data = json.load(f)
    
    # JSON file parses to a list of dictionaries but we want a dictionary 
    # of rate data where key is the rate id so we convert it using dict 
    # comprehension
    dataDict = {i['_id']['$oid']: i for i in data}

    # return dictionary
    return dataDict

# ---------------------------------------------------------------------------- #
def getRateCsv ():
    '''
    function to download the URDB csv file and return it as a dataframe
    '''

    # import csv from openei
    url = 'https://openei.org/apps/USURDB/download/usurdb.csv.gz'
    try:
        rates = pd.read_csv(url, compression='gzip', low_memory=False)
        rateFilter(rates)
    except Exception as e:
  
        if '404' in str(e):
            message = '''
    #####################################################################
    #        !!!!!FATAL ERROR: FILE COULD NOT BE DOWNLOADED!!!!!        #
    #                                                                   #
    #                   * File not found on openEI *                    #
    #         *Check openei.org/apps/USURDB/download/usurdb.json.gz *   #
    #                                                                   #
    #                   Script will close in 10 seconds                 #
    #                                                                   #
    #####################################################################
           
           '''
            print(message)
            logging.error(f'error downloading file: {e}')
            time.sleep(10)
            raise SystemExit
        else:    
            message = '''
    #####################################################################
    #        !!!!!FATAL ERROR: FILE COULD NOT BE DOWNLOADED!!!!!        #
    #                                                                   #
    #                   * Check internet connection*                    #
    #                                                                   #
    #                   Script will close in 10 seconds                 #
    #                                                                   #
    #####################################################################
           '''

            print(message)
            logging.error(f'error downloading file: {e}')
            time.sleep(10)
            raise SystemExit

    # test that the csv format has not changed
    if 'label' not in rates.columns or 'sector' not in rates.columns:
        print('Error: openei csv format has changed.')
        input('script cannot function with new format. exiting.') 
        return
# ---------------------------------------------------------------------------- #

def buildCache ():
    '''
    Parent function to build the rate cache. This function calls the other
    functions in this module to build the rate cache. This function is called
    by the checkCache function or from the mainMenu if the user chooses to 
    rebuild the cache.

    '''
    print('Building rate cache...this action takes about a minute depending'
          'on internet connection\n')

    # download data
    print('downlading data to build rate cache...')

    actions = [getRateCsv, getRateJson]

    iter = alive_it(actions, title='Downloading data')
    
    for i in iter:
        rates = i()          
    print('data download complete\n')

    # process URDB JSON file ---------------------------------------------------
    # dict comprehension to process rates in parallel
    iter = alive_it(rates.items(), title='Processing rates')
    ratesProcessed = {k: rateProcess(v) for k, v in iter}
   
    print('rate processing complete. Saving to file...')
    # save processed rates to file pickle file
    with open('cached_data/ratesProcessed.pickle', 'wb') as f:
        pickle.dump(ratesProcessed, f)

    print('cache built\n')

# ---------------------------------------------------------------------------- #
def loadCache():
    '''
    function to load in cached data. loop construct used to 
    show progress bar while loading data
    '''
    files = [r'cached_data/filtered.pkl',
             r'cached_data/ratesProcessed.pickle']

    iter = alive_it(files, title='Loading cache')
    
    out = []

    for i in iter:
        with open(i, 'rb') as f:
            out.append(pickle.load(f))
    rateFiltered, ratesProcessed = out[0], out[1]
    return rateFiltered, ratesProcessed

# ------------------------------------------------------------------------------
def checkCache():
    '''
    function to check for and load the rate cache. This function is called
    in the calcSetup function. If the cache is not found, the buildCache
    function is called to build the cache.

    '''

    print('checking for and loading cached data...')

    if (os.path.exists('cached_data/filtered.pkl') and
        os.path.exists('cached_data/ratesProcessed.pickle')):
        print('using prebuilt cache')
        rateFiltered, ratesProcessed = loadCache()
        
    else:
        print('no cache found. building cache...')
        buildCache()
        print('cache built...loading data')
        rateFiltered, ratesProcessed = loadCache()
  
    return rateFiltered, ratesProcessed

################## Rate Validation Function ####################################

def validRates(rate):
    '''
    in some cases tier rates are not in sequence. This causes a bug 
    in the calculate function for tiered rates that returns negative values
    This function checks for that and returns a boolean indicator that triggers
    a unsupported rate output. 
    '''
    
    # tier values are in sequence    
    if (rate['nrgTierMax'] is not False and
        rate['nrgTierMax'] != sorted(rate['nrgTierMax'])):
        tierValid = False
    
    else:
        tierValid = True
    
    if (rate['demandFlatRates'] is not False and
        rate['demandFlatRates'] != sorted(rate['demandFlatRates'])):
        flatValid = False

    else:
        flatValid = True

    if tierValid is False or flatValid is False:
        return False
    else:
        return True

################## Rate Selection Functions ####################################
def filterRates(filtertype, rateFiltered, rates):
    ''''
    'All Filtered Rates'
    'Filtered Residential Rates',
    'Filtered Commercial Rates',
    'Filtered Industrial Rates',
    'All Rates in URDB'
    '''

    if filtertype == 'All Filtered Rates':
        filterset = rateFiltered['label'].tolist()
        # rates in dictionary rates where key is in filterset
        rates = {key: rates[key] for key in filterset}
    elif filtertype == 'Filtered Residential Rates':
        filterset = (rateFiltered[
            rateFiltered['sector'] == 'Residential']['label']
            .tolist())
        rates = {key: rates[key] for key in filterset}
    elif filtertype == 'Filtered Commercial Rates':
        filterset = (rateFiltered[
            rateFiltered['sector'] == 'Commercial']['label']
            .tolist())
        rates = {key: rates[key] for key in filterset}
    elif filtertype == 'Filtered Industrial Rates': 
        filterset = (rateFiltered[
            rateFiltered['sector'] == 'Industrial']['label']
            .tolist())
        rates = {key: rates[key] for key in filterset}
    else:
        pass

    return rates

# ----------------------------------------------------------------    

'''
This file contains all of the functions used to setup and run the rate calculator.
The functions are defined in Calculator Functions section and are called 
in the parent runCalc function

See the documentation for the core calculator function methods
in calculatorDocs.ipynb

Built by Atlas Public Policy in Washington, DC
2023
'''

# external dependencies
from alive_progress import alive_it
import numpy as np
import logging

# internal dependencies
import lib.inputFunctions as imp
import lib.outputFunctions as out
import lib.interfaceFunctions as itf


#################### Preparation Functions #####################################

def daysMonth(chargeDays):
    """ 
    Returns a nested list of weekdays/weekends in each month for a given 
    number of charge days (rounded to 2 sig digits)

    # there are only 7 possible outputs (14 lists) from this so this may change to a
    # hardcoded lookup table in the future
    """
    if chargeDays > 7:
        raise ValueError('Charge days cannot be greater than 7')

    days = [31,28,31,30,31,30,31,31,30,31,30,31]
    weekdays = 5 if chargeDays > 5 else chargeDays - 1
    weekends = 2 if chargeDays > 6 else 1

    return [[np.round(days[i] * weekdays / 7, 2) for i in range(12)], # refactor
            [np.round(days[i] * weekends / 7, 2) for i in range(12)]]

# -----------------------------------------------------------------------------

def nrgUse(nrg, daysMonth):
    """
    returns a list of monthly energy use in kWh based on a energy use input and 
    daysMonth list. Is both an input to the calculator and an output of the 
    tool, and is used to calculate the average cost / kWh.
    """
    use = [sum(i) for i in nrg]

    # add daysMonth[0] (weekday) and daysMonth[1] (weekend) to get total days
    # in month
    nDays = np.nansum(daysMonth, axis=0).tolist()

    # pairwise multiply nrgUse and nDays to get total monthly energy use 
    # for each month
    return [use[x] * nDays[x] for x in range(12)]


# -----------------------------------------------------------------------------

def getMaxPower(power):
    # was more complicated but is now a single line function
        return [np.max(power) for i in range(12)]

def getMinPower(power):
    # was more complicated but is now a single line function
    return [np.min(power) for i in range(12)]

# -----------------------------------------------------------------------------

#################### Core Calculation Functions ###############################

def tierCalc(unit, costTier, maxVal):
    """
    Calculates cost for a given tier structure AND 
    energy/power use. 

    this function is used in the nrgTierCalc function below to calculate cost of 
    tiered energy rates and is also used for tiered flat demand charges.

    unit: energy or power use
    costTier: tiered rate structure
    maxVal: max value for each tier

    output: list of cost for each month
    """

    # generate containers
    unitVal = unit
    cost = 0

    # loop through costTier to calculate cost
    for i in range(len(costTier)):

        # define upper and lower values
        lower = 0 if i == 0 else maxVal[i-1]
        upper = maxVal[i] if i < len(maxVal) else unit + 1
        
        # if eng is within tier margin calculate cost on unitVal and tier
        # and break loop
        if unit > lower and unit <= upper:
            cost += (unitVal * costTier[i])
            break
        
        # otherwise add in full tier cost and subtract amount of energy
        # accounted for from unitVal and continue loop
        elif unit > upper:
            band = upper - lower
            cost += (band * costTier[i])
            unitVal -= band

    return cost
# -----------------------------------------------------------------------------

def nrgTierCalc(nrg, tierRate, tierMax):
    """
    simple list comprehension to calculate energy cost for each month based
    on tiered rate structure and energy use using the tierCalc function
    """
    return [tierCalc(nrg[i], tierRate[i], tierMax[i]) for i in range(12)]

# -----------------------------------------------------------------------------

def nrgTOUCalc(nrg, touWeekday, touWeekend, daysInMonth):
    """
    Calculates energy cost for a given TOU structure using a
    monthly energy use input.

    expects input of 12 x 2 x 24 array for touSchedule and 12 x 24 array for nrg
    """

    touSchedule = [touWeekday, touWeekend] # make array

    # set of array calculations to calculate energy cost
    costArr = np.multiply(nrg, touSchedule)
    costArr = np.nansum(costArr, axis=2)

    # multiply by days in month (weekend and weekday)
    costArr = np.multiply(costArr, daysInMonth)

    # add weekend and weekday costs
    costArr = np.nansum(costArr, axis=0).tolist()
    
    return costArr

# -----------------------------------------------------------------------------

def flatDemandCalc(rate, mx, maxPower):
    """
    Calculates flat demand charges for a given flat demand schedule
    using a monthly max power input.

    control flow is based on whether or not there is a tiered rate structure 
    in the rate input

    rate: flat demand rate structure
    mx: max values for each tier
    maxPower: max power for each month
    """
    # if max is false (empty) then there is a flat rate and the function 
    # calculates that 
    if mx == False:
        # flatten rate[0] to remove nested lists
        xsublist = [x for y in rate for x in y]
        # return maxPower * rate for each month
        return (np.multiply(maxPower, xsublist)
                .tolist())
    
    # if rate[1][0] (max vals) is not empty, then there is a tiered rate and the
    # function calls the tierCalc function to calculate the demand charge for 
    # each month
    else:
        return [tierCalc(maxPower[i], rate[i], mx[i]) for i in range(12)]

# -----------------------------------------------------------------------------

def demandTOUCalc(rate, power):
  '''
  takes in a 12 x 24 array for rate and a 12 x 24 array for power
  and calculates the demand charge for each month

  rate: demand rate structure
  power: hourly power for each month
  '''

  # get unique values in rate (these are the periods)
  rateU = [list(set(i)) for i in rate]
    
  # get max power for each period (complicated list comprehension to get
  # max power for each period across all 12 months)
  maxPower = [[max(power[z][i] for i in range(24) if rate[z][i] == x)
                  for x in rateU[z]] 
                    for z in range(len(rateU))]
                    
  return [sum(maxPower[n][i] * rateU[n][i] for i in range(len(rateU[n])))
             for n in range(12)]


###################### Run Calcuation Functions ###############################

def calcSetup(inputfile, filter, days, curveType):
    '''
    This function is used to setup the calculation. It is called by the calc
    function. It returns the rates, energy, power, days, maxPower, and
    total_energy variables that are used in the coreCalc function.
    '''

    # assemble data for calculation--------------------------------------------
    # first get the rates from cache or URDB
    rates, filters = imp.checkCache()

    # then filter the rates
    rates = imp.filterRates(filter, rates, filters)

    # then get user inputs (this function may return an error that will return
    # user to the main menu)
    energy, power = imp.parseUserInputs(inputfile, curveType)
    
    # precalculate common inputs for all calculations---------------------------
    # then calculate days in month
    days = daysMonth(days)

    # then get total energy
    total_energy = nrgUse(energy, days)

    # then get max and min power
    maxPower = getMaxPower(power)

    return rates, energy, power, days, maxPower, total_energy
    
# ---------------------------------------------------------------------------- #

def coreCalc(rate, energy, power, days, 
             maxPower, total_energy):
    
    '''
    This function is the core of the calculation. It takes in the rates, energy,
    power, days, maxPower, and total_energy variables and returns the output
    dictionary from the calculation.

    '''

    output = {}
    empty = [0 for i in range(12)]
    
    # if rate is not valid return unsupported
    if imp.validRates(rate) is False:
        return 'unsupported'

    # if anything in rate = 'unsupported' then return unsupported
    if 'unsupported' in rate.values():
        return 'unsupported'
    
    # if schedule is not valid return unsupported
    if 'schedule invalid' in rate.values():
        return 'unsupported'
    
    #----------------------------------------

    # energy charges
    if rate['nrgTierRates'] is not False:
            output['TieredEnergyCharge'] = nrgTierCalc(total_energy,
                                                 rate['nrgTierRates'],
                                                 rate['nrgTierMax'])
    else:
        output['TieredEnergyCharge'] = empty

    if rate['nrgTOUWkdRates'] is not False:
        output['TOUEnergyCharge'] = nrgTOUCalc(energy,
                                               rate['nrgTOUWkdRates'],
                                               rate['nrgTOUWkeRates'],
                                               days)
    else:
        output['TOUEnergyCharge'] = empty

    # demand charges
    
    if rate['demandFlatRates'] is not False:
        output['FlatDemandCharge'] = flatDemandCalc(rate['demandFlatRates'],
                                                    rate['demandFlatMax'],
                                                    maxPower)       
    else:
        output['FlatDemandCharge'] = empty

    if rate['demandTOUwkdRates'] is not False:
            output['TOUDemandCharge'] = demandTOUCalc(rate['demandTOUwkdRates'],
                                                      power)
    else:
        output['TOUDemandCharge'] = empty

    return output


# --------------------------------------------------

def calcRun(inputfile, filter, days, curveType, filename):
    '''
    This function is the primary control function for the calculation.
    it calls the calcSetup and coreCalc functions from this module and 
    then the output processing functions from the outputFunctions module.
    '''

    # define setup variables    
    (rates, energy, power, days,
    maxPower, total_energy) = calcSetup(inputfile, filter, days, curveType)

    # run the calculator function    
    (print ('\ndoing the math...'))
    # run coreCalc function in a dictionary comprehension
    iter = alive_it(rates.items(), title='Processing rates')
    output = {k : coreCalc(v, energy, power, days, maxPower, total_energy) for k, v in iter}
    output = {k : out.processOutput(v, total_energy) for k, v in output.items()}

    process = [out.toDataFrame,
               out.addRateInfo,
               out.createSummaries]
    
    print ('\nAssemblying output...')
    iter = alive_it(process, title='Processing output')
    
    for i in iter: 
        output = i(output, rates)
    
    # unpack output
    longdf, summarydf = output
    
    # write output to excel
    out.write2ExcelTables(filename, [summarydf, longdf],
                         ['Annual Summary', 'Monthly Summary'])
    
    # wrap up

    itf.askOpenFile(filename)
    logging.info('Rate calculation completed without error')
    itf.exitOrMain('Rate calculation complete...')

    

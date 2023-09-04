'''
outputFunctions module contains all of the data transformation functions used to
output the results of the calculator.

Built by Atlas Public Policy in Washington, DC
2023
'''

# external dependencies
from alive_progress import alive_it
import pandas as pd
import numpy as np
import time
import os

# internal dependencies
import lib.interfaceFunctions as itf

# ------------------------------------------------------------------------------
def processOutput(output, total_energy):
    '''
    This function applies a post-processing step to the output dictionary. It 
    calculates total cost and cost per kWh, and adds them to the output
    dictionary. If the rate is not supported, it fills in the output with NaNs.

    '''
    
    # start output dictionary with label
    out = {}

    # add in the month number and name
    out['month'] = [i for i in range(1,13)]
    out['monthname'] = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                            'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] 

    # add in the output if it is supported
    if output != 'unsupported':
        out['rateSupported'] = True

        # append the output dictionary to the output dictionary
        out.update(output)
        
        out['totalCost'] = [sum([out['TieredEnergyCharge'][i],
                             out['TOUEnergyCharge'][i], 
                             out['FlatDemandCharge'][i], 
                             out['TOUDemandCharge'][i]]) 
                             for i in range(12)]
        # catch divide by zero errors
        try:
            out['costPerkWH'] = [out['totalCost'][i] / total_energy[i]
                                  for i in range(12)]
        except ZeroDivisionError:
            out['costPerkWH'] = [0 for i in range(12)]

        out['totalEnergy'] = total_energy

    # fill in the output with NaNs if the rate is not supported
    else:    
        for i in ['TieredEnergyCharge', 'TOUEnergyCharge', 
                  'FlatDemandCharge', 'TOUDemandCharge',
                  'totalCost', 'costPerkWH', 'totalEnergy']:
            out['rateSupported'] = False
            out[i] = [np.nan for i in range(12)]

    return out

# ------------------------------------------------------------------------------


def toDataFrame(output, rates):

    '''
    This function takes the output dictionary and converts it to a dataframe
    '''
            
    df = pd.DataFrame.from_dict(output, orient='index')
    df['id'] = df.index
    df.index = range(len(df))
    df = df.apply(pd.Series.explode)

    return df

# ------------------------------------------------------------------------------

def addRateInfo(df, rates):
    '''
    This function takes the output dataframe and adds in the rate information
    from the rates dictionary

    note: Candidate for reengineering: This is not the best way to manage the
    data. It would be better to have a separate dataframe for the rate information
    that can be cached and pulled in here. This would avoid the need to pass
    so much data around in the rates dictionary. 
    '''

    # details dictionary
    details = ['id', 'rateName', 'utilityName', 'eiaId', 'sector', 
               'fixedChargeFirstMeter', 'sourceReference', 'description',
                 'demandMax', 'demandMin']
    
    detailsDF = pd.DataFrame.from_dict(rates, orient='index').reset_index()
    detailsDF = detailsDF[details]

    # add details to the output dataframe
    df = df.merge(detailsDF, left_on='id', right_on='id', how='left')

    return df

# ------------------------------------------------------------------------------

def createSummaries(df, rates):
    '''
    pass in the output dataframe and get back two dataframes, one with the
    results in a long format with one row per month, (indexed to the id) and
    one with the results in a wide format with one row per rate (with rate details)

    Note that it would be more efficient to join in the rate details here rather
    than prior as it would allow for a faster join. However, things are currently
    fast enough that this is not a priority.

    '''
    longdf = df[['id', 'rateSupported', 'month', 'monthname',
                 'TieredEnergyCharge', 'TOUEnergyCharge', 
                 'FlatDemandCharge', 'TOUDemandCharge','totalCost',
                 'costPerkWH']]
        
    summarydf = (df.groupby(['id', 'rateSupported', 'rateName', 'utilityName', 
                             'eiaId', 'sector', 'fixedChargeFirstMeter',
                             'sourceReference', 'description', 'demandMax',
                             'demandMin'])

                       .agg({'TieredEnergyCharge': 'sum', 'TOUEnergyCharge': 'sum',
                             'FlatDemandCharge': 'sum', 'TOUDemandCharge': 'sum',
                             'totalCost': 'sum', 'totalEnergy': 'sum'})
                       .reset_index())
    
    # generate annual cost/kWh field
    np.seterr(divide='ignore', invalid='ignore')
    summarydf['costPerkWh'] = [np.divide(i,j) for i,j in
                                zip(summarydf['totalCost'],
                                    summarydf['totalEnergy'])]
 
    return longdf, summarydf

# ------------------------------------------------------------------------------

def write2ExcelTables(filename, dfs, sheet_names):
    '''
    This function takes a list of dataframes and writes them to an excel file
    with each dataframe on a separate sheet. It also formats the sheets as tables
    with header rows.

    This function is very slow so may be a good candidate for optimization in
    the future. Otherwise it may be better to write the dataframes to csv files
    by default and then have an option to write to excel.
    '''
        
    filename = f'results/{filename}.xlsx'

    print(f'\nWriting results to {filename}, this may take a while...')
    for i in range(10):
        try:
            writer = pd.ExcelWriter(filename, engine='xlsxwriter')
            break
        except PermissionError:
            print('Error writing to file, file is open or inaccessible')
            input(f'try closing {filename} and press enter to continue')
            time.sleep(3)
            
        if i == 9:  
            input('file inaccessible...press enter to exit to main menu')
            itf.exitOrMain()

    iter = alive_it(zip(dfs, sheet_names), title='Writing data')

    for dataframe, sheet in iter:
        dataframe.to_excel(writer, sheet_name=sheet, index=False)

    # get xlsxwriter objects from writer
    worksheet = writer.sheets

        # format each worksheet as a table with header row based on 
        # dataframe column names
    
    for sheet in sheet_names:
        worksheet[sheet].add_table(0, 0,
        len(dfs[sheet_names.index(sheet)]),
        len(dfs[sheet_names.index(sheet)].columns)-1,
            {'header_row': True,
             'columns': [{'header': column} 
            for column in dfs[sheet_names.index(sheet)].columns]})

        # increase column width for columns in writer to fit header width
    for worksheet_name in writer.sheets:
        worksheet = writer.sheets[worksheet_name]
        dataframe = dfs[sheet_names.index(worksheet_name)]
        for idx, col in enumerate(dataframe):
            series = dataframe[col]
            max_len = len(str(series.name)) + 2
            worksheet.set_column(idx, idx, max_len)

        # close the Pandas Excel writer and output the Excel file.
    out = [writer.close]
    iter = alive_it(out, title = 'saving file')
    for i in iter:
        i()

    print(f'results saved in {filename}/n')
    return filename
    

# ------------------------------------------------------------------------------

def openExcelFile(filepath):

    '''
    This function opens an excel file in the default program for excel files.
    '''

    # if file exists, open it
    print('opening workbook...this will only work on a windows machine with'
          'excel installed\n')

    if os.path.exists(filepath):
        excelfile = os.path.abspath(filepath)
        os.system(f"start EXCEL.EXE \"{excelfile}\"")
    else:
        print(f'Error: could not find {filepath}\n')
import numpy as np
import pandas as pd
from pytz import timezone
import datetime
import math
import time
import re
import functools
import itertools

from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output

from zipline.utils import tradingcalendar
vixUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv'
vxstUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxstcurrent.csv'
vxvUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxvdailyprices.csv'
vxmtUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxmtdailyprices.csv'
vvixUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vvixtimeseries.csv'
df_data = 'https://dl.dropboxusercontent.com/u/264353/df_data.csv'


History = 128

def preprocess(df):  
    df = df.dropna()
    return df


def initialize(context):  
    fetch_csv(df_data,  
              pre_func=preprocess,  
              date_column='Date',  
              symbol = 'vxx'
              )  
    

def before_trading_start(context, data):  
    print data.current('vxx', 'PrevContango')
    
    

# def initialize(context):
#     context.fetch_failed = False
    
#     context.vxx = sid(38054)
#     context.vxz = sid(38055)
    
#     pipe = Pipeline()
#     attach_pipeline(pipe, 'vix_pipeline')  
    
    
#     schedule_function(allocation, date_rule=date_rules.every_day(), time_rule=time_rules.market_open(minutes=15))

#     fetch_csv(vixUrl, 
#               symbol='VIX', 
#               skiprows=1,
#               date_column='Date', 
#               pre_func=addFieldsVIX,
#               post_func=shift_data)
#  #   fetch_csv(vxstUrl, 
#  #             symbol='VXST', 
#  #             skiprows=3,
#  #             date_column='Date', 
#  #             pre_func=addFieldsVXST,
#  #             post_func=shift_data)
#     fetch_csv(vxvUrl, 
#               symbol='VXV', 
#               skiprows=2,
#               date_column='Date', 
#               pre_func=addFieldsVXV,
#               post_func=shift_data)
#     fetch_csv(vxmtUrl, 
#               symbol='VXMT', 
#               skiprows=2,
#               date_column='Date', 
#               pre_func=addFieldsVXMT,
#               post_func=shift_data)
# #    fetch_csv(vvixUrl, 
# #              symbol='VVIX', 
# #              skiprows=1,
# #              date_column='Date', 
# #              pre_func=addFieldsVVIX,
# #              post_func=shift_data)

def handle_data(context, data):
    pass


    

# this is our allocation function.  the vix data
# available after update_indices is lookahead-
# bias free.
def allocation(context, data):
    update_indices(context, data)
    record(fetch_failed = context.fetch_failed * 20)
    # we have access to all the VIX of the past History days
    record(vix=context.vix_vals[-1])
    record(vxv=context.vxv_vals[-1])
    record(vxmt=context.vxmt_vals[-1])

def update_indices(context, data):
    context.fetch_failed = False
    context.vix_vals = unpack_from_data(context, data, 'VIX')    
    context.vxv_vals = unpack_from_data(context, data, 'VXV')  
    context.vxmt_vals = unpack_from_data(context, data, 'VXMT')
    # context.vvix_vals = unpack_from_data(context, data, 'VVIX')
    # context.vxst_vals = unpack_from_data(context, data, 'VXST')

def fix_close(df,closeField):
    df = df.rename(columns={closeField:'Close'})
    # remove spurious asterisks
    df['Date'] = df['Date'].apply(lambda dt: re.sub('\*','',dt))
    # convert date column to timestamps
    df['Date'] = df['Date'].apply(lambda dt: pd.Timestamp(datetime.datetime.strptime(dt,'%m/%d/%Y')))
    df = df.sort(columns='Date', ascending=True)
    return df

def subsequent_trading_date(date):
    tdays = tradingcalendar.trading_days
    last_date = pd.to_datetime(date)
    last_dt = tradingcalendar.canonicalize_datetime(last_date)
    next_dt = tdays[tdays.searchsorted(last_dt) + 1]
    return next_dt

def add_last_bar(df):
    last_date = df.index[-1]
    subsequent_date = subsequent_trading_date(last_date)
    blank_row = pd.Series({}, index=df.columns, name=subsequent_date)
    # add today, and shift all previous data up to today. This 
    # should result in the same data frames as in backtest
    df = df.append(blank_row).shift(1).dropna(how='all')
    return df

def shift_data(df):
    log.info("Pre-Shift")
    df = add_last_bar(df)
    df.fillna(method='ffill') 
    df['PrevCloses'] = my_rolling_apply_series(df['Close'], to_csv_str, History)
    dates = pd.Series(df.index)
    dates.index = df.index
    df['PrevDates'] = my_rolling_apply_series(dates, to_csv_str, History)
    return df

def unpack_from_data(context, data, sym):
    try:
        v = data.current(sym, 'PrevCloses')
        i = data.current(sym, 'PrevDates')
        return from_csv_strs(i,v,True).apply(float)
    except:
        log.warn("Unable to unpack historical {s} data.".format(s=sym))
        context.fetch_failed = True

def addFieldsVIX(df):
    log.info("VIX: Pre-Massage")
    df = fix_close(df,'VIX Close')
    log.info("VIX: Post-Massage")
    return df

def addFieldsVXST(df):
    log.info("VXST: Pre-Massage")
    df = fix_close(df,'Close')
    log.info("VXST: Post-Massage")
    return df

def addFieldsVXMT(df):
    log.info("VXMT: Pre-Massage")
    df = fix_close(df,'Close')
    log.info("VXMT: Post-Massage")
    return df

def addFieldsVXV(df):
    log.info("VXV: Pre-Massage")
    df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = fix_close(df,'CLOSE')
    log.info("VXV: Post-Massage")
    return df

def addFieldsVVIX(df):
    log.info("VVIX: Pre-Massage")
    df = fix_close(df,'VVIX')
    log.info("VVIX: Post-Massage")
    return df

# convert a series of values to a comma-separated string of said values
def to_csv_str(s):
    return functools.reduce(lambda x,y: x+','+y, pd.Series(s).apply(str))

# a specific instance of rolling apply, for Series of any type (not just numeric,
# ala pandas.rolling_apply), where the index of the series is set to the indices
# of the last elements of each subset
def my_rolling_apply_series(s_in, f, n):
    s_out = pd.Series([f(s_in[i:i+n]) for i in range(0,len(s_in)-(n-1))]) 
    s_out.index = s_in.index[n-1:]
    return s_out

# reconstitutes a Series from two csv-encoded strings, one of the index, one of the values
def from_csv_strs(x, y, idx_is_date):
    s = pd.Series(y.split(','),index=x.split(','))
    if (idx_is_date):
        s.index = s.index.map(lambda x: pd.Timestamp(x))
    return s

"""
【検証期間延長】先物プレミアムでXIV（2049）買　先物ディスカウントでVXX（1552）買のバックテスト - room5110 - 
https://room5110.com/vix/backtest-premium-discount-20151204

+ Buy VXX for Vol long
+ Buy XIV for Vol short 
+ Detect signal at Equity Close Time 
+ Hold until signal changes 
+ When signal changes, close all position and open new one. 
+ Start from $10000 

XIV(2049)/VXX(1552)ストラテジーバックテスト【2016年7月まで版】 - room5110 - https://room5110.com/vix/backtest201607#XIV2049_VXX1552
+ VX2 / VX1 -1 > 0, Vol long
+ VX2 / VX1 -1 < 0, Vol short
"""
import pandas as pd
import re 
from zipline.utils import tradingcalendar
from quantopian.algorithm import calendars

def initialize(context):
    context.vxx = sid(38054)
    context.xiv = sid(40516)
    context.vx1 = continuous_future('VX', offset=0, roll='volume', adjustment='mul')
    context.vx2 = continuous_future('VX', offset=1, roll='volume', adjustment='mul')    
    context.contango = None 
    context.currently_long_vol = False
    context.currently_short_vol = False
    
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)
    
    schedule_function(rebalance,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)
    
    schedule_function(record_contango, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)
                      

    
def rebalance(context, data):
    # close position
    if context.contango > 0 and context.currently_long_vol:
        order_percent(context.vxx, 0) 
        context.currently_long_vol = False
        
    elif context.contango < 0 and context.currently_short_vol:
        order_percent(context.xiv, 0) 
        context.currently_short_vol = False
    
    # open position 
    if context.contango > 0 and (not context.currently_short_vol):
        order_percent(context.xiv, 0.9) 
        context.currently_short_vol = True 
        
    elif context.contango < 0 and (not context.currently_long_vol):
        order_percent(context.vxx, 0.9) 
        context.currently_long_vol = True 
        

def calc_contango(context, data):
    vx1_price = data.current(context.vx1, 'price')
    vx2_price = data.current(context.vx2, 'price')
    context.contango = vx2_price / vx1_price - 1 
    print context.contango
    return context.contango
    

def record_contango(context, data):
    record(contango=context.contango)


def reformat_quandl(df,closeField):
    df = df.rename(columns={closeField:'Close'})
    dates = df.Date.apply(lambda dt: pd.Timestamp(re.sub('\*','',dt), tz='US/Eastern'))
    df['Date'] = dates.apply(next_trading_day)
    df = df.sort(columns='Date', ascending=True)
    df.index = range(df.shape[0])
    return df

def next_trading_day(dt):
    tdays = tradingcalendar.trading_days
    normalized_dt = tradingcalendar.canonicalize_datetime(dt)
    idx = tdays.searchsorted(normalized_dt)
    return tdays[idx + 1]

def addFieldsVXV(df):
    df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'CLOSE')
    return df

def addFieldsVIX(df):
    #df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'VIX Close')
    return df
    
                 
        
        
    
    
    
    
    
    
    
    
    































 

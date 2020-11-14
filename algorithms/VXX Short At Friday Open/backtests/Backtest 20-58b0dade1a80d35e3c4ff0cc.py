"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q500US
from zipline.utils import tradingcalendar

import pandas as pd
import re


def initialize(context):
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.spx = sid(8554)
    context.order_id = None
    context.order_id2 = None
    context.ivts = None
    context.ivts_vixvxx = None
    context.pfoliopl = None

    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxvdailyprices.csv',  
              symbol='vxv', 
              skiprows=2, 
              date_column='Date', 
              pre_func=addFieldsVXV)
    
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)    
    
    # ショートポジション 金曜日のクローズ
    schedule_function(my_rebalance_position_open, date_rules.week_end(2), time_rules.market_close())
    # ポジションクローズ　水曜日のオープン
    schedule_function(my_rebalance_position_close, date_rules.week_start(2), time_rules.market_open())
    
    # record はリバランスを終えてから描く．リバランスで更新しているデータを使っているから，
    schedule_function(my_record, date_rules.every_day(), time_rules.market_close())

def before_trading_start(context, data):
    context.go = False
    context.vix = data.current('vix', 'Close')
    context.vxv = data.current('vxv', 'Close')   
    
def my_rebalance_position_open(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)

    if(data.can_trade(context.vxx)) & (execdate.day <= 25):
        context.order_id = order_percent(context.vxx, -1.0)
        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))

def myfactor(context, data):
    context.ivts = data.current(context.vxx, 'price') / data.current(context.vxz, 'price')
    context.ivts_vixvxx = context.vix / context.vxv 
    if context.ivts_vixvxx <= 0.91:
        context.go = True
       
        
def my_rebalance_position_open1(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)
    
    myfactor(context, data)
    
    if not context.go:
        log.info('No Trade because ivts %s < 2 ' % context.ivts)
    if(data.can_trade(context.vxx)) & (execdate.day <= 25) & context.go:
        context.order_id = order_percent(context.vxx, -0.5)
        context.order_id2 = order_percent(context.vxz, 0.5)

        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))
        log.info('VXZ Long Position Opened: %s @ %s: Total %s' % (
                get_order(context.order_id2).amount, data.current(context.vxz, 'price'), 
                get_order(context.order_id2).amount * data.current(context.vxz, 'price')))

       
def my_rebalance_position_open2(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)
    
    myfactor(context, data)
    
    if not context.go:
        log.info('No Trade because ivts %s < 0.91 ' % context.ivts)
    if(data.can_trade(context.vxx)) & (execdate.day <= 25) & context.go:
        context.order_id = order_percent(context.vxx, -1.0)

        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))
        
def my_rebalance_position_close(context, data):
    execdate = get_datetime('US/Eastern')
    context.order_id = order_target(context.vxx, 0.0)
    # context.order_id = order_target(context.vxz, 0.0)
    log.info('VXX Close at %s: %s' % (execdate, data.current(context.vxx, 'price')))
    # log.info('VXZ Close at %s: %s' % (execdate, data.current(context.vxz, 'price')))    

def my_record(context, data):
    log.info('PnL on %s is %s ' % ( get_datetime('US/Eastern'), context.portfolio.pnl))
    
    if context.pfoliopl != None:
        log.info((context.portfolio.pnl - context.pfoliopl)/context.pfoliopl)

    #     if abs(context.pfoliopl / context.portfolio.pnl -1 ) >=0.2:
    #         log.info('Positions on %s is %s' %( get_datetime('US/Eastern'), context.portfolio.pnl))
    record(vxx=data.current(context.vxx, 'price'))
    # record(vxz=data.current(context.vxz, 'price'))
    # record(ivts=context.ivts) 
    # record(ivts_vixvxx = context.ivts_vixvxx) 
    context.pfoliopl = context.portfolio.pnl
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass


##### fetch_csv helpers #####

    
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
    
                 
        
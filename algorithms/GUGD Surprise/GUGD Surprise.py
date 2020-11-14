"""
surprice.csv を読み込む
spy 



"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
from zipline.utils.tradingcalendar import trading_day  


# Your backtest must begin on or after: 2007-01-01 and end on or before: 2015-07-19.
from quantopian.pipeline.data.eventvestor import EarningsCalendar

# To use built-in Pipeline factors for this dataset
from quantopian.pipeline.factors.eventvestor import (
BusinessDaysUntilNextEarnings,
BusinessDaysSincePreviousEarnings
)

import pandas as pd
import pytz

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    msgs = '\t%s\t%s:\t%s'%(dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)
    log.info(msgs)

    
def initialize(context):
    # schedule_function(my_order_at_1600, date_rules.every_day(), time_rules.market_close())    
    schedule_open_close()
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.sell = None
    context.buy = None
    context.diff = {}
    context.partially_filled = False
    
    context.date_range = pd.date_range(, freq=trading_day)
    
    fetch_csv('https://docs.google.com/spreadsheets/d/1WH_gj5Ivftl4UQ1GBYKEIrRFvDT_Q2Bc-LEAiVw_PtQ/edit#gid=344742122',
              symbol = "surprise", 
              date_column=':Time',
              date_format = '%Y-%m-%d',
              timezone = pytz.timezone('America/New_York'))
    
def hoge(context, data): 
    print data.history('surprise', [':%Suprise', 'symbol'], )
def schedule_open_close():  
    # daytime return
    schedule_function(close_partially_filled, date_rules.every_day(), time_rules.market_open())
    schedule_function(my_order_at_0930, date_rules.every_day(), time_rules.market_open())
    schedule_function(close_all, date_rules.every_day(), time_rules.market_close(minutes=5))

def schedule_open_open():  
    # open to next open return
    schedule_function(close_all, date_rules.every_day(), time_rules.market_open())
    schedule_function(my_order_at_0930, date_rules.every_day(), time_rules.market_open(minutes=5))
    

def make_pipeline():
    close = USEquityPricing.close
    open_ = USEquityPricing.open
    high = USEquityPricing.high
    low = USEquityPricing.low
    
    pipe = Pipeline(
        columns = { 'close': close.latest,}, 
        screen = Q1500US())
    return pipe 

 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
        


def price_change(context, data, clm_name):
    sids = context.targets.index
    prices = data.current(sids, 'price').rename(clm_name)
    context.targets = pd.concat([context.targets, prices], axis=1)
    context.targets["return at " + clm_name] = context.targets[clm_name] / context.targets["yesterday_close"] - 1 
    #context.targets.sort_values(by="return at " + clm_name, ascending=False, inplace=True)
    

def my_order(context, data, clm_name):
    price_change(context, data, clm_name)
    context.sell = context.targets[(context.targets["return at " + clm_name] > 0.25)].index
    context.buy = context.targets[(context.targets["return at " + clm_name] < -0.25)].index
    if context.sell.any() :
        for sid in context.sell:
            if data.can_trade(sid):
                context.diff[sid] = context.targets["return at " + clm_name].ix[sid]
                order_percent(sid, -1.0/len(context.sell)*0.5)
            
            
    if context.buy.any() :
        for sid in context.buy:
            if data.can_trade(sid):
                context.diff[sid] = context.targets["return at " + clm_name].ix[sid]
                order_percent(sid, 1.0/len(context.buy)*0.5)

def my_order_at_0930(context, data):
    my_order(context, data, "0930")
    
def my_order_at_1600(context, data):
    my_order(context, data, "1600")
        
def close_partially_filled(context, data):
    if context.partially_filled:
        for sid in context.portfolio.positions:  
            context.diff[sid] = "Partially Filled"
        for sid in context.portfolio.positions:  
            my_close(context, data, sid) 
        context.diff = {}
    context.partially_filled = False 
    
    
def close_all(context, data):  
    for sid in context.portfolio.positions:  
        my_close(context, data, sid) 
    context.diff = {}

def my_close(context, data, sid):
    if data.can_trade(sid):
        logging("%s\t%s\t%s\t%s\t%s\t%s" % (
                sid.symbol,
                context.diff[sid], 
                context.portfolio.positions[sid].last_sale_price, ## 現在価格
                context.portfolio.positions[sid].cost_basis, ## ポジションオープンした時の価格
                context.portfolio.positions[sid].amount, 
                context.portfolio.positions[sid].last_sale_date.astimezone(pytz.timezone('US/Eastern'))) ## ポジションオープンした時間をNYTで
                )
        order_target(sid, 0)

        
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def my_rebalance(context,data):
    """
    Execute orders according to our schedule_function() timing. 
    """
    pass
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass

def handle_data(context,data):
    """
    Called every minute.
    """
    pass 

    
   

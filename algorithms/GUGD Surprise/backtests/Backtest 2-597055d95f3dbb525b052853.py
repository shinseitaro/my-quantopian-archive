"""
前日 pe が-1だった銘柄を
今日の 15:55 の price を見て 25%以上上がっていたらショート，逆をロング．次の日のクローズでCloseする

"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US

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
    #schedule_function(price_change_at_open, date_rules.every_day(), time_rules.market_open())
    schedule_function(close_all, date_rules.every_day(), time_rules.market_close(minutes=5))        
    schedule_function(price_change_at_close, date_rules.every_day(), time_rules.market_close())    
    attach_pipeline(make_pipeline(), 'my_pipeline')
    context.sell = None
    context.buy = None
    context.diff = {}
         
def make_pipeline():
    """
    A function to create our dynamic stock selector (pipeline). Documentation on
    pipeline can be found here: https://www.quantopian.com/help#pipeline-title
    """
    
    # Base universe set to the Q500US
    base_universe = Q1500US()
    pe = BusinessDaysSincePreviousEarnings()
    

    # Factor of yesterday's close price.
    yesterday_close = USEquityPricing.close.latest
    
     
    pipe = Pipeline(
        screen = base_universe, 
        columns = {
            'yesterday_close': yesterday_close,
            # 'next_earning': ne, 
            'previous_earning': pe, 
        }
    )
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
    context.targets = context.output[context.output["previous_earning"] == 1]


def price_change(context, data, clm_name):
    sids = context.targets.index
    prices = data.current(sids, 'price').rename(clm_name)
    context.targets = pd.concat([context.targets, prices], axis=1)
    context.targets["return at " + clm_name] = context.targets[clm_name] / context.targets["yesterday_close"] - 1 
    #context.targets.sort_values(by="return at " + clm_name, ascending=False, inplace=True)
    
    
def price_change_at_open(context, data):
    price_change(context, data, "0930")
    x = context.targets[(context.targets["return at 0930"] > 0.25) | (context.targets["return at 0930"] < -0.25)]
    if not x.empty:
        print x["return at 0930"]
    
def price_change_at_close(context, data):
    price_change(context, data, "1600")
    context.sell = context.targets[(context.targets["return at 1600"] > 0.25)].index
    context.buy = context.targets[(context.targets["return at 1600"] < -0.25)].index
    if context.sell.any() :
        for sid in context.sell:
            context.diff[sid] = context.targets["return at 1600"].ix[sid]
            order_percent(sid, -1.0/len(context.sell)*0.5)
            
            
    if context.buy.any() :
        for sid in context.buy:
            context.diff[sid] = context.targets["return at 1600"].ix[sid]
            order_percent(sid, 1.0/len(context.buy)*0.5)
            

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

    
   

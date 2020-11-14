import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 

from zipline.utils.calendars import get_calendar

##原油とガソリンのスプレッド

def initialize(context):
    # 原油とガソリンの連続データを取得
    context.crude_oil = continuous_future('CL', offset=0, roll='calendar')
    context.gasoline = continuous_future('XB', offset=0, roll='calendar')
    context.futures_calendar = get_calendar('us_futures')
    
    context.term = 14
    context.target_spread = 0.01
    context.short_spread = False 
    context.long_spread = False  
    
    schedule_function(rebalance_pairs,
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_close())
    
    schedule_function(record_price, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_close())

    
def get_spread(context, data):
    hist = data.history(assets=[context.crude_oil, context.gasoline], 
                        fields='price', 
                        bar_count=context.term, 
                        frequency='1d') 

    cl_price = hist[context.crude_oil]
    xb_price = hist[context.gasoline]
    
    cl_price_change = cl_price.pct_change()[1:]
    xb_price_change = xb_price.pct_change()[1:]
    
    regression = sp.stats.linregress(xb_price_change,cl_price_change)
    spread = cl_price_change[-1] - regression.slope * xb_price_change[-1]
    return spread 
    
def get_target_weights(context, data):
    cl_contract, xb_contract = data.current(
        [context.crude_oil, context.gasoline], 
        'contract')
    
    context.spread = get_spread(context, data)
    target_weights = {}
    
    if context.spread > context.target_spread: 
        ## 原油を売って，ガソリンを買う
        context.long_spread = False
        if context.short_spread:
            pass
        else:
            log.info("Short Spread")
            context.short_spread = True 
            target_weights[cl_contract] = -0.5
            target_weights[xb_contract] = 0.5
    elif context.spread < -context.target_spread:  
        ## 原油を買って，ガソリンを売る
        context.short_spread = False
        if context.long_spread:
            pass 
        else:
            log.info("Long Spread")
            context.long_spread = True
            target_weights[cl_contract] = 0.5
            target_weights[xb_contract] = -0.5    
            
    return target_weights 

def rebalance_pairs(context, data): 
    target_weights = get_target_weights(context, data)
    
    if target_weights:
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[])
    
def record_price(context, data):
    record(spread=context.spread)
    

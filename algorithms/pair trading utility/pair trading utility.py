"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
 
def initialize(context):
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close())
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    context.s1 = sid(2071) #D
    context.s2 = sid(14372)#EIX
    context.spread_long = False
    context.spread_short = False 
    context.thredshold = 1.5
    
def condition1(context, data):
    ## 上限threshold を超えたらShort，
    ## 下限threshold を超えたらLong
    ## それぞれ，0をまたぐまでHold
    
    if context.zscore >= context.thredshold:
        if context.spread_long:
            close_positions(context, data)
        if not context.spread_short:
            go_short(context, data)
            
    elif context.zscore <= - context.thredshold:
        if context.spread_short:
            close_positions(context, data)
        if not context.spread_long:
            go_long(context, data) 
            
    elif 0 < context.zscore < context.thredshold:
        if context.spread_long:
            close_positions(context, data)
            
    elif 0 > context.zscore >= - context.thredshold:
        if context.spread_short:
            close_positions(context, data)

def condition2(context, data):
    ## 上限threshold を超えている間はShortHold
    ## 下限threshold を超えている間はLongHold
    if - context.thredshold > context.zscore:
        if context.spread_short: 
            close_positions(context, data)
        if not context.spread_long:
            go_long(context, data) 
    elif context.thredshold < context.zscore:
        if context.spread_long:
            close_positions(context, data)
        if not context.spread_short:
            go_short(context, data) 
    else:
        if context.spread_long or context.spread_short:
            close_positions(context, data)
            
            
def my_rebalance(context,data):
    data_s1 = data.history(context.s1, 'price', 60, "1d")
    data_s2 = data.history(context.s2, 'price', 60, "1d")
    diff = data_s1 - data_s2
    
    ma10_s1 = data_s1[-10:].mean()
    ma10_s2 = data_s2[-10:].mean()
    ma60_s1 = data_s1[-60:].mean()
    ma60_s2 = data_s2[-60:].mean()
    diff_ma10 = ma10_s1 - ma10_s2
    diff_ma60 = ma60_s1 - ma60_s2
    diff_std = diff.std()
    context.zscore = (diff_ma10 - diff_ma60) / diff_std
    condition1(context, data)
    

def go_short(context, data):
    context.spread_short = True 
    context.spread_long = False 
    if (data.can_trade(context.s1) and data.can_trade(context.s2)):
        order_target_percent(context.s2, 0.45)
        order_target_percent(context.s1, -0.45)
        
def go_long(context, data):
    context.spread_short = False 
    context.spread_long = True 
    if (data.can_trade(context.s1) and data.can_trade(context.s2)):
        order_target_percent(context.s1, 0.45)
        order_target_percent(context.s2, -0.45)

def close_positions(context, data):
    context.spread_short = False 
    context.spread_long = False 

    open_positions = context.portfolio.positions
    for position in open_positions:
        order_target(position, 0)
    
 
def my_record_vars(context, data):
    record(zcore=context.zscore)
    record(top=1.0)
    record(bottom=-1.0)
    
 

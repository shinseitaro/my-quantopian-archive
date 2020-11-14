"""
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

    schedule_function(rebalance,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)
    
    schedule_function(record_contango, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)
                      
def calc_contango(context, data):
    vx1_price = data.current(context.vx1, 'price')
    vx2_price = data.current(context.vx2, 'price')
    context.contango = vx2_price / vx1_price - 1 
    print context.contango
    return context.contango
    
def rebalance(context, data):
    calc_contango(context,data)
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
        

def record_contango(context, data):
    record(contango=context.contango)



import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 

from zipline.utils.calendars import get_calendar
    
def initialize(context):
    # SoyBeans
    context.soybeans_1 = continuous_future('CL', offset=0, roll='calendar')
    context.soybeans_2 = continuous_future('CL', offset=1, roll='calendar')
    context.soybeans_3 = continuous_future('CL', offset=2, roll='calendar')
    context.soybeans_4 = continuous_future('CL', offset=3, roll='calendar')
    context.soybeans_5 = continuous_future('CL', offset=4, roll='calendar')

    context.slope = 0.001
    context.target_slope = 0.01
    context.short_spread = False 
    context.long_spread = False  
    
    schedule_function(get_slope)
    schedule_function(my_rebalance)
    schedule_function(my_record)

def get_slope(context, data):

    hist = data.current([context.soybeans_1, 
                         context.soybeans_2, 
                         context.soybeans_3, 
                         context.soybeans_4, 
                         context.soybeans_5],
                        'price',)
    context.sy1_price = hist[context.soybeans_1]
    context.sy5_price = hist[context.soybeans_5]
    
    regression = sp.stats.linregress(range(0,4), hist.pct_change()[1:])
    
    log.info(regression.slope)
    return regression.slope
    

def my_rebalance(context, data):
    ## 現在の期近と５限月のコントラクトを取得
    sy_1_contract = data.current(context.soybeans_1, 'contract')
    sy_5_contract = data.current(context.soybeans_5, 'contract')
    target_weights = {}
    
    context.my_slope = get_slope(context, data)
    
    if context.my_slope > context.target_slope:
        if not context.short_spread:
            context.short_spread = True
            target_weights[sy_1_contract] = -0.5
            target_weights[sy_5_contract] = 0.5
        else:
            pass 
    elif context.my_slope < -context.slope:
        if not context.long_spread:
            context.long_spread = True
            target_weights[sy_1_contract] = 0.5
            target_weights[sy_5_contract] = -0.5
        else:
            pass 
    elif (-0.005 < context.my_slope) and (context.my_slope < 0.005):
        context.short_spread = False 
        context.long_spread = False
        target_weights[sy_1_contract] = 0.0
        target_weights[sy_5_contract] = 0.0
    
    log.info(context.short_spread)
    #log.info("context.long_spread:", context.long_spread)
    
    if target_weights:
        order_optimal_portfolio(objective=opt.TargetWeights(target_weights),
                                constraints=[])
        
    
def my_record(context, data):
    record(sy1=context.sy1_price,
           sy5=context.sy5_price,
          )
        
    
    
    
   
    


    
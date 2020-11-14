"""
This is the pair trading example from the end of the Getting
Started With Futures tutorial.
Ref: (https://www.quantopian.com/tutorials/futures-getting-started)
"""

import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):
    context.future_symbol = 'SY' # SoyBeans
    
    # continuous_future コントラクトオブジェクト．
    # このオブジェクトで，現在やヒストリカルの価格等にアクセスする．
    context.f_1 = continuous_future(context.future_symbol, offset=0, roll='calendar')
    context.f_2 = continuous_future(context.future_symbol, offset=1, roll='calendar')
    context.f_3 = continuous_future(context.future_symbol, offset=2, roll='calendar')
    context.f_4 = continuous_future(context.future_symbol, offset=3, roll='calendar')
    context.f_5 = continuous_future(context.future_symbol, offset=4, roll='calendar')

    
    schedule_function(my_rebalance,
                      date_rules.every_day(),
                      time_rules.market_open(minutes=30))
    
    # schedule_function(my_record,
    #                   date_rules.every_day(),
    #                   time_rules.market_open())

def get_entry_flag(context, data):
    context.price = data.current(
        [context.f_1, context.f_2, context.f_3, context.f_4, context.f_5],
        fields='price')
    
    contango = context.price.pct_change()
    context.near_price_contango = contango[context.f_2]
    context.far_price_contango = contango[context.f_3]
    sign_near = np.sign(context.near_price_contango)
    sign_far = np.sign(context.far_price_contango)
    
    return sign_near, sign_far, sign_near == sign_far

def my_rebalance(context, data): 
    near = data.current(context.f_1, 'contract')
    far = data.current(context.f_2, 'contract')
    target_weights = {}
    sign_near, sign_far, entry_flag = get_entry_flag(context, data)
    
    if entry_flag:
        order_target(near, 0)
        order_target(far, 0) 
    else:
        if sign_near > 0: 
            order_target(near, 1)
            order_target(far, -1)
        else :
            order_target(near, -1)
            order_target(far, 1)
            
            
            
        
        
        
        
        
        
        
        
    
   
    

        
    
    
    
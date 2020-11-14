"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその7：カレンダースプレッド

"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar

import pandas as pd

def initialize(context):
    sym1 = 'HO'
    
    context.f1 = continuous_future(sym1, roll='calendar', offset=0)
    context.f2 = continuous_future(sym1, roll='calendar', offset=1)
    context.f3 = continuous_future(sym1, roll='calendar', offset=2)    
    
    context.holding_days = 0
    context.n_days_before_expired = 10
    
    context.lower_thred = 1 #0.9982#
    context.close_thred = 1.01
    
    context.long_boco = False

    
    schedule_function(my_rebalance)
    schedule_function(my_record)
    
def is_near_expiration(contract, n):
    return (contract.expiration_date - get_datetime()).days < n

def show_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 'amount':v.amount, 'average value':v.cost_basis,}
        l.append(d)
    log.info(pd.DataFrame(l))    

# {Future(1059201706 [HOM17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': -15, 'last_sale_price': 1.556, 'asset': Future(1059201706 [HOM17]), 'cost_basis': 1.5992207008101993}), Future(1059201707 [HON17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': 30, 'last_sale_price': 1.5599, 'asset': Future(1059201707 [HON17]), 'cost_basis': 1.5952347858155072}), Future(1059201708 [HOQ17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': -15, 'last_sale_price': 1.5652000000000001, 'asset': Future(1059201708 [HOQ17]), 'cost_basis': 1.608453998966117})}


def my_rebalance(context, data):
    cpp = context.portfolio.positions  
    if cpp:
        show_my_position(cpp)

    price = data.current([context.f1, context.f2, context.f3], 'price')
    contract_f1 = data.current(context.f1, 'contract')
    contract_f2 = data.current(context.f2, 'contract')
    contract_f3 = data.current(context.f3, 'contract')
    multiplier = contract_f1.multiplier
    
    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean * 1.0
    
    if is_near_expiration < context.n_days_before_expired:
        order_target(contract_f1, 0) 
        order_target(contract_f2, 0) 
        order_target(contract_f3, 0) 
        context.long_boco = False 
        log.info('Closed as near expiry'.format())
        
    else: 
        #if not context.long_boco and context.f2_mean_diff < context.lower_thred:
        if context.f2_mean_diff < context.lower_thred:
            order_target_value(contract_f1, -1*multiplier) 
            order_target_value(contract_f2, 2*multiplier) 
            order_target_value(contract_f3, -1*multiplier) 
            context.long_boco = True 
            log.info('{}: Go Long {} and Short {} and {}'.format(context.f2_mean_diff,
                                                                contract_f2.symbol,
                                                                 contract_f1.symbol,
                                                                 contract_f3.symbol,
                                                                ))
        elif context.long_boco and context.f2_mean_diff > context.close_thred:
            order_target(contract_f1, 0) 
            order_target(contract_f2, 0) 
            order_target(contract_f3, 0)
            context.long_boco = False 
            log.info('{}: Closed.'.format(context.f2_mean_diff,))
        else:
            pass 

def my_record(context, data):
    #log.info( [context.long_boco, context.f2_mean_diff] )
    record(diff=context.f2_mean_diff)
"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその7：カレンダースプレッド

"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar

import pandas as pd
import numpy as np 


def initialize(context):
    sym1 = 'HO'
    
    context.first_contract = continuous_future(sym1, roll='calendar', offset=0)
    context.f1 = continuous_future(sym1, roll='calendar', offset=1)
    context.f2 = continuous_future(sym1, roll='calendar', offset=2)
    context.f3 = continuous_future(sym1, roll='calendar', offset=3)    
    
    context.holding_days = 0
    context.n_days_before_expired = 10
    
    context.lower_thred = 1 #0.9982#
    context.close_thred = 1.01
    
    context.long_boco = False

    
    schedule_function(my_rebalance)
    schedule_function(my_record)
    
def is_near_expiration(contract):
    return (contract.expiration_date - get_datetime()).days

def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 'amount':v.amount, 'average value':v.cost_basis,
            'last_sale_price': v.last_sale_price, 'current value': v.last_sale_price*v.amount, 
             'PL':((v.cost_basis/v.last_sale_price-1)*v.amount*k.multiplier), 
             'exp date': k.expiration_date.strftime("%Y%m%d")}
        
        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index('symbol')
    log.info(df)
    return df 

def my_rebalance(context, data):
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
        if np.abs(df['amount'].sum() ) > 5:
            partially_filled = True
            
    price = data.current([context.f1, context.f2, context.f3], 'price')
    contract_f1 = data.current(context.f1, 'contract')
    contract_f2 = data.current(context.f2, 'contract')
    contract_f3 = data.current(context.f3, 'contract')
    contract_first_contract = data.current(context.first_contract, 'contract')
    
    multiplier = contract_f1.multiplier
    
    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean * 1.0
    remain_days = is_near_expiration(contract_first_contract)
    
    ## 残存期間が context.n_days_before_expiredより短い場合は，ポジションをゼロにする．
    if remain_days < context.n_days_before_expired:
        if context.long_boco:
            order_target(contract_f1, 0) 
            order_target(contract_f2, 0) 
            order_target(contract_f3, 0) 
            context.long_boco = False 
            log.info('Closed as near expiry: {}'.format(remain_days))

    ## 残存期間が残っている場合        
    else: 
        #if not context.long_boco and context.f2_mean_diff < context.lower_thred:
        if context.f2_mean_diff < context.lower_thred:
            log.info('Order: {}'.format(context.f2_mean_diff ))
            order_target_value(contract_f1, -1*multiplier) 
            order_target_value(contract_f2, 2*multiplier) 
            order_target_value(contract_f3, -1*multiplier) 
            context.long_boco = True 
            # log.info('{}: Go Long {} and Short {} and {}'.format(context.f2_mean_diff,
            #                                                     contract_f2.symbol,
            #                                                      contract_f1.symbol,
            #                                                      contract_f3.symbol,
            #                                                     ))
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
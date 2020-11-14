"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその7：カレンダースプレッド
order_optimal_portfolioを使う
DEBESO 
https://github.com/drillan/quantopian/blob/master/driller/forward_curves01.ipynb

"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar
import numpy as np

import pandas as pd

def initialize(context):
    sym1 = 'CL'
    
    context.first_contract = continuous_future(sym1, roll='calendar', offset=0)
    context.f1 = continuous_future(sym1, roll='calendar', offset=0)
    context.f2 = continuous_future(sym1, roll='calendar', offset=1)
    context.f3 = continuous_future(sym1, roll='calendar', offset=2)    
    
    context.holding_days = 0
    context.n_days_before_expired = 15
    
    context.boco_thred = 0.994570
    context.close_boco = 1.007414
    
    context.deco_thred = 1.007414
    context.close_deco = 0.994570
    
    context.long_boco = False
    context.short_deco = False
    
    schedule_function(my_rebalance)
    schedule_function(my_record)
    
def count_remain_days(first_contract ):
    return (first_contract.expiration_date - get_datetime()).days 

   
def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 'amount':v.amount, 'average value':v.cost_basis,
            'last_sale_price': v.last_sale_price, 'current value': v.last_sale_price*v.amount, 
             'PL':((v.cost_basis/v.last_sale_price-1)*v.amount*k.multiplier), 'exp date': k.expiration_date.strftime("%Y%m%d")}
        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index('symbol')
    log.info(df)
    return df 

# {Future(1059201706 [HOM17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': -15, 'last_sale_price': 1.556, 'asset': Future(1059201706 [HOM17]), 'cost_basis': 1.5992207008101993}), Future(1059201707 [HON17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': 30, 'last_sale_price': 1.5599, 'asset': Future(1059201707 [HON17]), 'cost_basis': 1.5952347858155072}), Future(1059201708 [HOQ17]): Position({'last_sale_date': Timestamp('2017-05-26 10:31:00+0000', tz='UTC'), 'amount': -15, 'last_sale_price': 1.5652000000000001, 'asset': Future(1059201708 [HOQ17]), 'cost_basis': 1.608453998966117})}


def my_rebalance(context, data):
    target_weight = {}
    cpp = context.portfolio.positions  
    partially_filled = False
   
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
        if np.abs(df['amount'].sum() ) > 5:
            partially_filled = True
        
    log.info(partially_filled)
    price = data.current([context.f1, context.f2, context.f3], 'price')
    first_contract = data.current(context.first_contract , 'contract')
    contract_f1 = data.current(context.f1, 'contract')
    contract_f2 = data.current(context.f2, 'contract')
    contract_f3 = data.current(context.f3, 'contract')
    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean
    remain_days = count_remain_days(first_contract)
    log.info(remain_days)
    
   
    if partially_filled or (remain_days < context.n_days_before_expired) :
        target_weight[contract_f1] = 0
        target_weight[contract_f2] = 0
        target_weight[contract_f3] = 0
        context.long_boco = False 
        context.long_deco = False 
        
    else: 
        if context.f2_mean_diff < context.boco_thred: #not context.long_boco and 
            target_weight[contract_f1] = -0.15
            target_weight[contract_f2] = 0.3
            target_weight[contract_f3] = -0.15
            context.long_boco = True 
            log.info('{}: Long boco'.format(context.f2_mean_diff))
                     
        elif context.long_boco and context.f2_mean_diff > context.close_boco:
            target_weight[contract_f1] = 0
            target_weight[contract_f2] = 0
            target_weight[contract_f3] = 0
            context.long_boco = False 
            log.info('{}: Closed.'.format(context.f2_mean_diff,))
                
                     
        elif context.f2_mean_diff > context.deco_thred:
            target_weight[contract_f1] = 0.15
            target_weight[contract_f2] = -0.3
            target_weight[contract_f3] = 0.15
            context.short_deco = True 
            log.info('{}: Long boco'.format(context.f2_mean_diff))
                     
        elif context.short_deco and context.f2_mean_diff < context.close_deco:
            target_weight[contract_f1] = 0
            target_weight[contract_f2] = 0
            target_weight[contract_f3] = 0
            context.long_boco = False 
            log.info('{}: Closed.'.format(context.f2_mean_diff,))              
                     
        else:
            pass 

    if target_weight:
        order_optimal_portfolio(
            opt.TargetWeights(target_weight),
            constraints=[]
        )
def my_record(context, data):
    record(diff=context.f2_mean_diff)
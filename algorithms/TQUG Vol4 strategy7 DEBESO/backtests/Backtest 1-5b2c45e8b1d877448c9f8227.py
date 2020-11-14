"""
Tokyo Quantopian User Group handson Vol4
strategy4.py  
アルゴリズムその7：カレンダースプレッド
"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar


def initialize(context):
    sym1 = 'HO'
    
    context.f1 = continuous_future(sym1, roll='calendar', offset=0)
    context.f2 = continuous_future(sym1, roll='calendar', offset=1)
    context.f3 = continuous_future(sym1, roll='calendar', offset=2)    
    
    context.holding_days = 0
    context.n_days_before_expired = 5
    
    context.lower_thred = 0.98#0.9982
    context.close_thred = 1.0
    
    context.long_boco = False

    
    schedule_function(my_rebalance)
    schedule_function(my_record)
    
def is_near_expiration(contract, n):
    return (contract.expiration_date - get_datetime()).days < n

def my_rebalance(context, data):
    target_weight = {}
    
    price = data.current([context.f1, context.f2, context.f3], 'price')
    contract_f1 = data.current(context.f1, 'contract')
    contract_f2 = data.current(context.f2, 'contract')
    contract_f3 = data.current(context.f3, 'contract')
    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean
    
    if is_near_expiration < context.n_days_before_expired:
        pass 
        target_weight[contract_f1] = 0
        target_weight[contract_f2] = 0
        target_weight[contract_f3] = 0
        context.long_boco = False 
    else: 
        if not context.long_boco and context.f2_mean_diff < context.lower_thred:
            target_weight[contract_f1] = -0.3
            target_weight[contract_f2] = 0.6
            target_weight[contract_f3] = -0.3
            context.long_boco = True 
            log.info('{}: Go Long {} and Short {} and {}'.format(context.f2_mean_diff,
                                                                contract_f2.symbol,
                                                                 contract_f1.symbol,
                                                                 contract_f3.symbol,
                                                                ))
        elif context.long_boco and context.f2_mean_diff > context.close_thred:
            target_weight[contract_f1] = 0
            target_weight[contract_f2] = 0
            target_weight[contract_f3] = 0
            context.long_boco = False 
        else:
            pass 

    if target_weight:
        order_optimal_portfolio(
            opt.TargetWeights(target_weight),
            constraints=[]
        )
def my_record(context, data):
    record(diff=context.f2_mean_diff)
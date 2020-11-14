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
    sym1 = 'CL'
    
    context.first_contract = continuous_future(sym1, roll='calendar', offset=0)
    context.f1 = continuous_future(sym1, roll='calendar', offset=2)
    context.f2 = continuous_future(sym1, roll='calendar', offset=3)
    context.f3 = continuous_future(sym1, roll='calendar', offset=4)    
    
    context.holding_days = 0
    context.n_days_before_expired = 10
    
    # 凹んだところをLongするときの閾値と，それをクローズするときの閾値
    context.long_boco = False 
    context.boco_thred = 0.999
    context.close_boco_thred = 1.0
    
    # 凸んだどころをShortするときの閾値とそれをクローズするときの閾値　（凸む＝つばくむ）
    context.short_deco = False
    context.deco_thred = 1.001
    context.close_deco_thred = 1.00
    
    # schedule 
    # 
    schedule_function(my_rebalance, date_rule=date_rules.every_day(),time_rule=time_rules.market_open())
    schedule_function(my_record, date_rule=date_rules.every_day(),time_rule=time_rules.market_open())
    
def is_near_expiration(contract):
    return (contract.expiration_date - get_datetime()).days

def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 'amount':v.amount, 'average value':v.cost_basis,
            'last_sale_price': v.last_sale_price, 'current value': v.last_sale_price*v.amount, 
             'PL':((v.cost_basis/v.last_sale_price-1)*v.amount*k.multiplier), 
            # 'exp date': k.expiration_date.strftime("%Y%m%d")
            }
        
        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index('symbol')
    log.info(df)
    return df 


def rebalance_deco(context, data):
    # 出っ張っている真ん中の先物をショートし，両端をロングする．
    # 既にポジションを持っている場合，
    if context.short_deco:
        # 中央の先物が閾値より下がった場合，ポジションをクローズ
        if context.f2_mean_diff < context.close_deco_thred:
            close_all_potision(context, data)
            context.short_deco = False
            
    # ポジションが無い場合            
    else:
        # 中央の先物が閾値より上がった場合，ポジションを開く
        if context.f2_mean_diff > context.deco_thred:
            log.info('Order deco potision: {}'.format(context.f2_mean_diff))
            order_target(context.contract_f1, 1) 
            order_target(context.contract_f2, -2) 
            order_target(context.contract_f3, 1)  
            context.short_deco = True
            
def rebalnace_boco(context,data):
    # 凹んでいる中央の先物をロングし，両端をショートする
    # 既にポジションを持っている場合，
    if context.long_boco:
        # 中央の先物が閾値を上回った場合は，ポジションをクローズ
        if context.f2_mean_diff > context.close_boco_thred :
            close_all_potision(context, data)
            context.long_boco = False 
            
    # ポジションが無い場合            
    else:
        # 中央の先物が閾値を下回った場合，ポジションを開く
        if context.f2_mean_diff < context.boco_thred:
            log.info('Order boco potision: {}'.format(context.f2_mean_diff))
            order_target(context.contract_f1, -1) 
            order_target(context.contract_f2, 2) 
            order_target(context.contract_f3, -1) 
            context.long_boco = True

def close_all_potision(context, data):
    log.info('close potision'.format())
    order_target(context.contract_f1, 0) 
    order_target(context.contract_f2, 0) 
    order_target(context.contract_f3, 0)  
     

def my_rebalance(context, data):
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
        if np.abs(df['amount'].sum() ) > 5:
            partially_filled = True
            
    price = data.current([context.f1, context.f2, context.f3], 'price')
    context.contract_f1 = data.current(context.f1, 'contract')
    context.contract_f2 = data.current(context.f2, 'contract')
    context.contract_f3 = data.current(context.f3, 'contract')
    
    contract_first_contract = data.current(context.first_contract, 'contract')
   
    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean * 1.0
    remain_days = is_near_expiration(contract_first_contract)
    
    ## 残存期間が context.n_days_before_expiredより短い場合は，ポジションをゼロにする．
    if remain_days < context.n_days_before_expired:
        close_all_potision(context, data)
        context.long_boco = False 
        context.short_deco = False
        log.info('Closed as near expiry: {}'.format(remain_days))

    ## 残存期間が残っている場合        
    else:
        rebalance_deco(context,data)
        rebalnace_boco(context,data)
        
def my_record(context, data):
    log.info(context.f2_mean_diff)
    record(diff=context.f2_mean_diff)
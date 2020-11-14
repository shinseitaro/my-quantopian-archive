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
    sym1 = 'XB'
    
    context.first_contract = continuous_future(sym1, roll='calendar', offset=0)
    context.f1 = continuous_future(sym1, roll='calendar', offset=1)
    context.f2 = continuous_future(sym1, roll='calendar', offset=2)
    context.f3 = continuous_future(sym1, roll='calendar', offset=3)    
    
    context.holding_days = 0
    context.n_days_before_expired = 10
    
    # 凹んだところをLongするときの閾値
    context.boco_thred = 0.9982
    # それをクローズするときの閾値
    context.close_boco_thred = 1.0
    
    # 凸んだどころをShortする．（凸む＝つばくむ）
    context.deco_thred = 1.002
    # それをクローズするときの閾値
    context.close_deco_thred = 1.00
    
    context.long_deco = False
    context.short_boco = False 

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

def rebalance_deco(context,data):
    # 既にポジションを持っている場合，
    if context.long_deco:
        # ポジションを閉じる閾値に達している場合は，ポジションをクローズ
        if context.f2_mean_diff > context.close_deco_thred :
            close_all_potision(context, data)
            context.long_deco = False
    # ポジションが無い場合            
    else:
        # 設定した凹み閾値よりもf2が低ければ，ポジションを開く
        if context.f2_mean_diff < context.boco_thred:
            log.info('Order boco potision'.format())
            order_target(context.contract_f1, -1) 
            order_target(context.contract_f2, 2) 
            order_target(context.contract_f3, -1)  
            context.long_deco = True
            
def rebalnace_boco(context,data):
    # 既にポジションを持っている場合，
    if context.short_boco:
        # ポジションを閉じる閾値に達している場合は，ポジションをクローズ
        if context.f2_mean_diff < context.close_boco_thred :
            close_all_potision(context, data)
            context.short_boco = False 
    # ポジションが無い場合            
    else:
        # 設定した凸の閾値よりもf2が高ければ，ポジションを開く
        if context.f2_mean_diff > context.deco_thred:
            log.info('Order deco potision'.format())
            order_target(context.contract_f1, 1) 
            order_target(context.contract_f2, -2) 
            order_target(context.contract_f3, 1) 
            context.short_boco = True

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
    #log.info( [context.long_boco, context.f2_mean_diff] )
    record(diff=context.f2_mean_diff)
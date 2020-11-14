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

    target_num = 3
    context.first_contract = continuous_future(sym1, roll='calendar', offset=0)
    context.f1 = continuous_future(sym1, roll='calendar', offset=target_num-1)
    context.f2 = continuous_future(sym1, roll='calendar', offset=target_num)
    context.f3 = continuous_future(sym1, roll='calendar', offset=target_num+1)    
    context.n_days_before_expired = 10 if target_num <= 2 else 0

    entry_threshold = 0.0015
    exit_threshold =  0.0005
    
    # 凹んだところをLongするときの閾値と，それをクローズするときの閾値
    context.side = 0 
    context.long_entry_thred = -entry_threshold
    context.long_exit_thred = -exit_threshold

    # 凸んだどころをShortするときの閾値とそれをクローズするときの閾値　（凸む＝つばくむ）
    context.short_entry_thred = entry_threshold
    context.short_exit_thred = exit_threshold

    # スリッページなし
    set_slippage(us_futures=slippage.FixedSlippage(spread=0.00))
    
    # schedule 
    # 
    schedule_function(my_rebalance, date_rule=date_rules.every_day(), time_rule=time_rules.market_open(minutes=1))
    #schedule_function(my_record, date_rule=date_rules.every_day(),time_rule=time_rules.market_open())

    
def is_near_expiration(contract):
    return (contract.expiration_date - get_datetime()).days


def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 
             'amount': v.amount,
             'average value': v.cost_basis,
             'last_sale_price': v.last_sale_price, 
             'current value': v.last_sale_price*v.amount, 
             'PL': ((v.cost_basis/v.last_sale_price-1)*v.amount*k.multiplier), 
            # 'exp date': k.expiration_date.strftime("%Y%m%d")
            }
        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index('symbol')
    log.info(df)
    return df 


def has_long(context):
    return context.side > 0


def has_short(context):
    return context.side < 0


def is_long_entry(context):
    return context.f2_mean_diff < context.long_entry_thred


def is_long_exit(context):
    return context.f2_mean_diff > context.long_exit_thred


def is_short_entry(context):
    return context.f2_mean_diff > context.short_entry_thred


def is_short_exit(context):
    return context.f2_mean_diff < context.short_exit_thred


def make_positions(context, data, side, size):
    order_target(context.contract_f1, -side*size) 
    order_target(context.contract_f2, side*2*size) 
    order_target(context.contract_f3, -side*size)  
    context.side = side

    
def close_all_potisions(context, data):
    log.info('close potisions'.format())
    order_target(context.contract_f1, 0) 
    order_target(context.contract_f2, 0) 
    order_target(context.contract_f3, 0)  
    context.side = 0


def execute(context, data):
    order_size = 1
    # 出っ張っている真ん中の先物をショートし，両端をロングする．
    # 既にポジションを持っている場合，
    # 中央の先物が閾値より上がった場合，ポジションを開く
    # 中央の先物が閾値を下回った場合，ポジションを開く
    # 凹んでいる中央の先物をロングし，両端をショートする
    # 既にポジションを持っている場合，
    # 中央の先物が閾値より下がった場合，ポジションをクローズ
    # ポジションが無い場合     
    if not has_short(context) and is_short_entry(context):
        log.info('Order boko short potision: {}'.format(context.f2_mean_diff))
        make_positions(context, data, -1, order_size)
        return

    if not has_long(context) and is_long_entry(context):
        log.info('Order boko long potision: {}'.format(context.f2_mean_diff))
        make_positions(context, data, 1, order_size)
        return
    
    if has_long(context)  and not is_long_exit(context):
        return
    if has_short(context) and not is_short_exit(context):
        return
    close_all_potisions(context, data)

    

def my_rebalance(context, data):
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
        # if np.abs(df['amount'].sum() ) > 5:
        #     partially_filled = True

    price = data.current([context.f1, context.f2, context.f3], 'price')
    contract_first_contract = data.current(context.first_contract, 'contract')
    context.contract_f1 = data.current(context.f1, 'contract')
    context.contract_f2 = data.current(context.f2, 'contract')
    context.contract_f3 = data.current(context.f3, 'contract')

    f1_f3_mean = (price[context.f1] + price[context.f3]) / 2
    context.f2_mean_diff = price[context.f2] /  f1_f3_mean - 1.0
    remain_days = is_near_expiration(contract_first_contract)

    ## 残存期間が context.n_days_before_expiredより短い場合は，ポジションをゼロにする．
    expiring = remain_days < context.n_days_before_expired
    if expiring:
        close_all_potisions(context, data)
        log.info('Closed as near expiry: {}'.format(remain_days))

    ## 残存期間が残っている場合        
    else:
        execute(context,data)
    #
    log.info(context.f2_mean_diff)
    record(diff=context.f2_mean_diff)
    mag = 0.001
    record(side=-context.side*mag)
    record(expiring=expiring*0.01)
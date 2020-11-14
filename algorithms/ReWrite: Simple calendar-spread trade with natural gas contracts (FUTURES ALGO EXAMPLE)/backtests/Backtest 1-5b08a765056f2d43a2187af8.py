"""
https://www.quantopian.com/posts/simple-calendar-spread-trade-with-natural-gas-contracts-futures-algo-example を書き直し
ストラテジー：
NG1とNatural GasのETFであるFCGで，
cost_of_carry = (NG1 / FCG) / 残存期間
の過去20日間を算出し，直近のcost_of_carryが，過去20日と比べてどの大きければNG１をショート，小さければロング．
ただし，残存期間が１９日以下になった場合，ポジションは持たない．

"""
import numpy as np
import pandas as pd
import math

import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar


#import quantopian.algorithm as algo

def initialize(context):
    # NG1
    context.NG1 = continuous_future('NG', offset=0, roll='calendar', adjustment=None)
    #context.NG1 = continuous_future('NG', offset=0, roll='volume', adjustment='mul')
    
    #FCG
    context.FCG = sid(33837)
    
    context.costs_of_carry = list()
    
    context.futures_calendar = get_calendar('us_futures')
    
    # market_open(hours=1) => 07:30:00（ET）
    # schedule_function(train_algorithm, date_rules.every_day(), time_rules.market_open(hours=1))
    schedule_function(daily_rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
    schedule_function(record_vars, date_rules.every_day(), time_rules.market_open(hours=1))
    

def daily_rebalance(context, data): 
    """
    cost_of_carry = np.log（NG1/CFG）/残存期間
    log.info(get_datetime("US/Eastern"))
    残存期間を取得するのに，current contractが必要なので，history を使うことができない．
    """
    NG1_contract = data.current(context.NG1, 'contract')
    price = data.current([context.NG1, context.FCG], fields='price')
    remain_period = context.futures_calendar.session_distance(get_datetime("US/Eastern"), 
                                                              NG1_contract.expiration_date)
    
    
    context.costs_of_carry.append(np.log(price[context.NG1] / price[context.FCG]) / remain_period)
    
    if len(context.costs_of_carry) > 30:
        costs_of_carry_quantiles = pd.qcut(context.costs_of_carry[-30:], 5, labels=False) + 1
        if remain_period >=20:
            if costs_of_carry_quantiles[-1] == 5:
                order_target(NG1_contract, -1)
            elif costs_of_carry_quantiles[-1] == 1:  
                order_target(NG1_contract, 1)
        else:
            order_target(NG1_contract, 0)
            
def record_vars(context, data):
    pass
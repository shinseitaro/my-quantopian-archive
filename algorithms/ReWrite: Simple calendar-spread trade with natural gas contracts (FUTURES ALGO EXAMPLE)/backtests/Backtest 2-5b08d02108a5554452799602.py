"""
https://www.quantopian.com/posts/simple-calendar-spread-trade-with-natural-gas-contracts-futures-algo-example を書き直し
ストラテジー：
NG1とNatural GasのETFであるFCGで，
cost_of_carry = (NG1 / FCG) / 残存期間
の過去３０日間を算出し，直近のcost_of_carryが，過去３０日と比べてどの大きければNG１をショート，小さければロング．
ただし，残存期間が１９日以下になった場合，ポジションは持たない．

メモ
order_optimal_portfolio　だとすごく時間かかる
理由は不明


"""
import numpy as np
import pandas as pd
import math

import quantopian.optimize as opt
from quantopian.algorithm import order_optimal_portfolio
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
    

def get_weight(context, data): 
    """
    cost_of_carry = np.log（NG1/CFG）/残存期間
    log.info(get_datetime("US/Eastern"))
    残存期間を取得するのに，current contractが必要なので，history を使うことができない．
    """
    weights = {}
    NG1_contract = data.current(context.NG1, 'contract')
    price = data.current([context.NG1, context.FCG], fields='price')
    
    ## 営業日カレンダーではなく実質の残存期間
    #remain_period = context.futures_calendar.session_distance(get_datetime("US/Eastern"),                                                              NG1_contract.expiration_date)
    
    #timezone を指定するとと怒られる
    #remain_period = (NG1_contract.expiration_date - get_datetime("US/Eastern")).days　# Timestamp subtraction must have the same timezones or no timezones
    remain_period = (NG1_contract.expiration_date - get_datetime()).days
    context.costs_of_carry.append(np.log(price[context.NG1] / price[context.FCG]) / remain_period)
    
    if len(context.costs_of_carry) > 30:
        costs_of_carry_quantiles = pd.qcut(context.costs_of_carry[-30:], 5, labels=False) + 1
        if remain_period >=20:
            if costs_of_carry_quantiles[-1] == 5:
                weights[NG1_contract] = -1.0
                
            elif costs_of_carry_quantiles[-1] == 1:  
                weights[NG1_contract] = 1.0
                
        else:
            weights[NG1_contract] = 0.0
    return weights             

            

def daily_rebalance(context, data): 
    """
    order_optimal_portfolio がすごく時間がかかるので、
    
    """
    weights = get_weight(context, data)
    if weights: 
        contract =  data.current(context.NG1, 'contract')
        value = weights[ data.current(context.NG1, 'contract')]
        order_target_percent( contract, value)
        
        # 本当はこれだけでいいはず
        #order_optimal_portfolio(weights, contraints=[])
    
            
def record_vars(context, data):
    pass
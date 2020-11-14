"""
Tokyo Quantopian User Group handson Vol4(old)
アルゴリズムその4：クラックスプレッド
どりらーさんの 
https://github.com/drillan/quantopian/blob/master/driller/Crack_spread-CL_HO-sma01.ipynb
をベースに
"""

import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar


def initialize(context):

    # Crude Oil つなぎ足
    f1 = 'CL'
    f2 = 'HO'
    
    context.No2_f1 = continuous_future(f1, roll='calendar', offset=1)
    context.No2_f2 = continuous_future(f2, roll='calendar', offset=1)
    
    context.No3_f1 = continuous_future(f1, roll='calendar', offset=2)
    context.No3_f2 = continuous_future(f2, roll='calendar', offset=2)
    
    # 満期日まで
    context.remain_days_1 = 100
    context.remain_days_2 = 20 
    context.short_ma = 10
    context.long_ma = 20 # short_ma に対して十分ながければそれでいい・
    
    
    # ポジションを持つときに使うフラグ。ロング、ショートポジションを持っているかどうかを確認。
    context.currently_long_the_spread = False
    context.currently_short_the_spread = False
    
    # リバランス用のスケジュール。毎日、オープン３０分後に実行する。
    schedule_function(func=rebalance_pairs, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(minutes=30))
    
    # データの可視化
    schedule_function(record_price, 
                      date_rules.every_day(), 
                      time_rules.market_open())

def calc_ratio(context, data, future1, future2):
    contract1, contract2 = data.current([future1, future2], 'contract')
    
    if (contract1.expiration_date - get_datetime()).days > context.remain_days_2 & \
       (contract1.expiration_date - get_datetime()).days < context.remain_days_1:
            hist = data.history([future1, future2,],
                                'price', 
                                context.long_ma, 
                                '1d')
            ratio = hist[future1] / hist[future2]
            ratio_ma_mean = ratio.rolling(context.short_ma).mean()
            return (ratio[-1], ratio_ma_mean[-1])
    else:
        return None
    
def rebalance_pairs(context, data):
    calc_ratio_2 = calc_ratio(context, data, context.No2_f1, context.No2_f2) 
    #calc_ratio_3 = calc_ratio(context, data, context.No3_f1, context.No3_f2) 
    contract1, contract2 = data.current([context.No2_f1, context.No2_f2], 'contract')
    
    target_weights = {}
    
    if calc_ratio_2:
        ratio, ratio_ma_mean = calc_ratio_2
        if ratio > ratio_ma_mean:
            target_weights[contract1] = -0.25
            target_weights[contract2] = 0.25
        # elif ratio < ratio_ma_mean:
        #     target_weights[contract1] = 0.25
        #     target_weights[contract2] = -0.25            
    
        else:
            target_weights[contract1] = 0.0
            target_weights[contract2] = 0.0            
  
    if target_weights:
        # オーダー.
        # opt.TargetWeights(target_weights)　を使うことで、枚数を指定するのではなく、
        # 現在のポートフォリオ価格に対して、〜％を投入するかを指示できます。
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[]
        )
    record(ratio=ratio, ratio_ma_mean=ratio_ma_mean)

def record_price(context, data):
    pass
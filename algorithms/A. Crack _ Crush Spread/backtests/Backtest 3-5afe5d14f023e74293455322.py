import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 

from zipline.utils.calendars import get_calendar

def initialize(context):
    # 原油とガソリンの連続データを取得
    # 他のsymbol名はリンク先参照
    # https://www.quantopian.com/help#available-futures
    FUTURE_1 = 'CL'
    FUTURE_2 = 'XB'
    context.f1 = continuous_future(FUTURE_1, offset=0, roll='calendar')
    context.f2 = continuous_future(FUTURE_2, offset=0, roll='calendar')
    
    context.term = 14
    context.target_spread = 0.01
    
    context.short_spread = False 
    context.long_spread = False  
    context.futures_calendar = get_calendar('us_futures')
    
    schedule_function(rebalance_pairs,
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_close())
    
    schedule_function(record_price, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_close())

    
def get_spread(context, data):
    
    hist = data.history(assets=[context.f1, context.f2], 
                        fields='price', 
                        bar_count=context.term, 
                        frequency='1d') 

    f1_price = hist[context.f1]
    f2_price = hist[context.f2]
    
    # context.term 日分の日々の変化率を取得
    f1_price_change = f1_price.pct_change()[1:]
    f2_price_change = f2_price.pct_change()[1:]
    
    # その変化率で単回帰直線の slope を取得．
    regression = sp.stats.linregress(f2_price_change, f1_price_change)
    
    # f1の最新価格がどのくらいはなれているかを spread として返す．
    spread = f1_price_change[-1] - regression.slope * f2_price_change[-1]
    
    return spread 
    
def get_target_weights(context, data):
    # トレード日における期近のコントラクトを取得
    f1_contract, f2_contract = data.current(
        [context.f1, context.f2], 
        'contract')
    
    context.spread = get_spread(context, data)
    target_weights = {}
    
    if context.spread > context.target_spread: 
        ## f1を売って，f2を買う
        context.long_spread = False
        if context.short_spread:
            pass
        else:
            log.info("Short Spread")
            context.short_spread = True 
            target_weights[f1_contract] = -0.5
            target_weights[f2_contract] = 0.5
    elif context.spread < -context.target_spread:  
        ## f2を売って，f1を買う
        context.short_spread = False
        if context.long_spread:
            pass 
        else:
            log.info("Long Spread")
            context.long_spread = True
            target_weights[f1_contract] = 0.5
            target_weights[f2_contract] = -0.5    
            
    return target_weights 

def rebalance_pairs(context, data): 
    target_weights = get_target_weights(context, data)
    
    if target_weights:
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[])
    
def record_price(context, data):
    record(spread=context.spread)
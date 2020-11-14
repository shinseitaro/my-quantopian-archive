import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 

from zipline.utils.calendars import get_calendar

## expirty date についてのメモ
## Rolling futures expiry w/ Continuous Futures - https://www.quantopian.com/posts/rolling-futures-expiry-w-slash-continuous-futures
## https://www.quantopian.com/posts/futures-have-launched-research-backtesting-lectures-tutorial-and-more#590a61401f7c7a24f51e17c8
    
def initialize(context):
    # 原油とガソリンの連続データを取得
    context.crude_oil = continuous_future('CL', offset=0, roll='calendar')
    context.gasoline = continuous_future('XB', offset=0, roll='calendar')
    context.futures_calendar = get_calendar('us_futures')

    #print(dir(context.crude_oil))
    #PRINT ['adjustment', 'end_date', 'exchange', 'from_dict', 'is_alive_for_session', 'is_exchange_open', 'offset', 'roll_style', 'root_symbol', 'sid', 'start_date', 'to_dict']
        
    context.long_ma = 65 
    context.short_ma = 5 
    
    context.currently_long_the_spread = False
    context.currently_short_the_spread = False
    
    schedule_function(func=rebalance_pairs,
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(minutes=30))
    
    schedule_function(record_price, 
                      date_rules.every_day(),
                      time_rules.market_open())
    
def rebalance_pairs(context, data): 
    zscore = calc_spread_zscore(context, data)
    target_weights = get_target_weights(context, data, zscore)
    
    if target_weights: 
        ## order_optimal_portfolio は，ポートフォリオをオブジェクトを引数にとり注文を指示する関数
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[])

def calc_spread_zscore(context, data): 
    prices = data.history([context.crude_oil, context.gasoline], 
                           'price', 
                           context.long_ma, 
                           '1d')
    cl_price = prices[context.crude_oil]
    xb_price = prices[context.gasoline]
    
    cl_returns = cl_price.pct_change()[1:]
    xb_returns = xb_price.pct_change()[1:]
    
    regression = sp.stats.linregress(
        xb_returns[-context.long_ma:],
        cl_returns[-context.long_ma:],
        )
    spreads = cl_returns - (regression.slope * xb_returns) 
    
    zscore = (np.mean(spreads[-context.short_ma]) - np.mean(spreads)) / np.std(spreads, ddof = 1) 
    return zscore
    
def get_target_weights(context, data, zscore):
    cl_contract, xb_contract = data.current(
        [context.crude_oil, context.gasoline], 
        'contract'
        )
    target_weights = {}
    
    if context.currently_short_the_spread and zscore < 0.0:
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0
        context.currently_long_the_spread = False
        context.currently_short_the_spread = False
        
    elif context.currently_long_the_spread and zscore > 0.0: 
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0
        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore < -1.0 and (not context.currently_long_the_spread):
        target_weights[cl_contract] = 0.5
        target_weights[xb_contract] = -0.5
        context.currently_long_the_spread = True
        context.currently_short_the_spread = False
        
    elif zscore > 1.0 and (not context.currently_short_the_spread):        
        target_weights[cl_contract] = -0.5
        target_weights[xb_contract] = 0.5
        context.currently_long_the_spread = False
        context.currently_short_the_spread = True

    return target_weights 

def record_price(context, data):
    crude_oil_price = np.log2(data.current(context.crude_oil, 'price'))
    gasoline_price = np.log2(data.current(context.gasoline, 'price'))
    
    #log.info(data.current_chain(context.crude_oil))
    remain_dates = context.futures_calendar.session_distance(
            get_datetime('US/Eastern'),
            data.current_chain(context.crude_oil)[0].auto_close_date)
    # log.info(context.futures_calendar.session_distance(
    #         get_datetime('US/Eastern'),
    #         data.current_chain(context.crude_oil)[0].auto_close_date))
           
    
    #record(Crude=crude_oil_price, Gasoline=gasoline_price) 
    record(RemainDates=remain_dates)
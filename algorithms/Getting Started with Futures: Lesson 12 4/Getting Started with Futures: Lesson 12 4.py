import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):

    context.future1 = continuous_future('BO', roll='calendar', offset=3)
    context.future2 = continuous_future('SM', roll='calendar', offset=3)
    context.future3 = continuous_future('SY', roll='calendar', offset=3)

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

def get_ratio(context, data):
    prices = data.history([context.future1, 
                           context.future2,
                           context.future3,
                          ], 
                          'price', 
                          context.long_ma, 
                          '1d')
    change = (prices / prices.iloc[0]).applymap(np.log)
    f1_f3 = change[context.future1]-change[context.future3]
    f2_f3 = change[context.future2]-change[context.future3]    
    return np.abs(f1_f3.sum() - f2_f3.sum())
    
    
def rebalance_pairs(context, data):

    zscore = calc_spread_zscore(context, data)
    target_weights = get_target_weights(context, data, zscore)
        
    if target_weights:
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[]
        )

def calc_spread_zscore(context, data):

    prices = data.history([context.future1, 
                           context.future2], 
                          'price', 
                          context.long_ma, 
                          '1d')
    
    f1_price = prices[context.future1]
    f2_price = prices[context.future2]
        
    # Calculate returns for each continuous future  
    f1_returns = f1_price.pct_change()[1:]
    f2_returns = f2_price.pct_change()[1:]
    
    # Calculate the spread
    regression = sp.stats.linregress(
        f2_returns[-context.long_ma:],
        f1_returns[-context.long_ma:],
    )
    spreads = f1_returns - (regression.slope * f2_returns)

    # Calculate zscore of current spread
    zscore = (np.mean(spreads[-context.short_ma]) - np.mean(spreads)) / np.std(spreads, ddof=1)

    return zscore

def get_target_weights(context, data, zscore):

    # Get current contracts for both continuous futures
    f1_contract, f2_contract = data.current(
        [context.future1, context.future2], 
        'contract'
    )
    
    # Initialize target weights
    target_weights = {}  

    if context.currently_short_the_spread and zscore < 0.0:
        # Update target weights to exit position
        target_weights[f1_contract] = 0
        target_weights[f2_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif context.currently_long_the_spread and zscore > 0.0:
        # Update target weights to exit position
        target_weights[f1_contract] = 0
        target_weights[f2_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore < -1.0 and (not context.currently_long_the_spread):
        # Update target weights to long the spread
        target_weights[f1_contract] = 0.5
        target_weights[f2_contract] = -0.5
        
        context.currently_long_the_spread = True
        context.currently_short_the_spread = False

    elif zscore > 1.0 and (not context.currently_short_the_spread):
        # Update target weights to short the spread
        target_weights[f1_contract] = -0.5
        target_weights[f2_contract] = 0.5

        context.currently_long_the_spread = False
        context.currently_short_the_spread = True

    return target_weights

def record_price(context, data):

    # Get current price of primary crude oil and gasoline contracts.
    f1_price = data.current(context.future1, 'price')
    f2_price = data.current(context.future2, 'price')
      
    # Adjust price of gasoline (42x) so that both futures have same scale.
    record(SY=f1_price, SM=f2_price)
import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):

    # Get continuous futures for Light Sweet Crude Oil...
    context.crude_oil = continuous_future('CL', roll='calendar')
    # ... and RBOB Gasoline
    context.gasoline = continuous_future('XB', roll='calendar')
    
    # Long and short moving average window lengths     
    context.long_ma = 65
    context.short_ma = 5
    
    # True if we currently hold a long position on the spread
    context.currently_long_the_spread = False
    # True if we currently hold a short position on the spread
    context.currently_short_the_spread = False
    
    # Rebalance pairs every day, 30 minutes after market open
    schedule_function(func=rebalance_pairs, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(minutes=30))
    
    # Record Crude Oil and Gasoline Futures prices everyday
    schedule_function(record_price, 
                      date_rules.every_day(), 
                      time_rules.market_open())

def rebalance_pairs(context, data):

    # Calculate how far away the current spread is from its equilibrium
    zscore = calc_spread_zscore(context, data)
    
    # Get target weights to rebalance portfolio
    target_weights = get_target_weights(context, data, zscore)
        
    if target_weights:
        # If we have target weights, rebalance portfolio
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[]
        )

def calc_spread_zscore(context, data):

    # Get pricing data for our pair of continuous futures
    prices = data.history([context.crude_oil, 
                           context.gasoline], 
                          'price', 
                          context.long_ma, 
                          '1d')
    
    cl_price = prices[context.crude_oil]
    xb_price = prices[context.gasoline]
        
    # Calculate returns for each continuous future  
    cl_returns = cl_price.pct_change()[1:]
    xb_returns = xb_price.pct_change()[1:]
    
    # Calculate the spread
    regression = sp.stats.linregress(
        xb_returns[-context.long_ma:],
        cl_returns[-context.long_ma:],
    )
    spreads = cl_returns - (regression.slope * xb_returns)

    # Calculate zscore of current spread
    zscore = (np.mean(spreads[-context.short_ma]) - np.mean(spreads)) / np.std(spreads, ddof=1)

    return zscore

def get_target_weights(context, data, zscore):

    # Get current contracts for both continuous futures
    cl_contract, xb_contract = data.current(
        [context.crude_oil, context.gasoline], 
        'contract'
    )
    
    # Initialize target weights
    target_weights = {}  

    if context.currently_short_the_spread and zscore < 0.0:
        # Update target weights to exit position
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif context.currently_long_the_spread and zscore > 0.0:
        # Update target weights to exit position
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore < -1.0 and (not context.currently_long_the_spread):
        # Update target weights to long the spread
        target_weights[cl_contract] = 0.5
        target_weights[xb_contract] = -0.5
        
        context.currently_long_the_spread = True
        context.currently_short_the_spread = False

    elif zscore > 1.0 and (not context.currently_short_the_spread):
        # Update target weights to short the spread
        target_weights[cl_contract] = -0.5
        target_weights[xb_contract] = 0.5

        context.currently_long_the_spread = False
        context.currently_short_the_spread = True

    return target_weights

def record_price(context, data):

    # Get current price of primary crude oil and gasoline contracts.
    crude_oil_price = data.current(context.crude_oil, 'price')
    gasoline_price = data.current(context.gasoline, 'price')
      
    # Adjust price of gasoline (42x) so that both futures have same scale.
    record(Crude_Oil=crude_oil_price, Gasoline=gasoline_price*42)

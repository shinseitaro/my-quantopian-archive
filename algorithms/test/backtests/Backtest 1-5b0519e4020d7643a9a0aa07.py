"""
This is the pair trading example from the end of the Getting
Started With Futures tutorial.
Ref: (https://www.quantopian.com/tutorials/futures-getting-started)
"""

import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):
    # Get continuous futures for Light Sweet Crude Oil...
    context.crude_oil = continuous_future('CL', roll='calendar')
    # ... and RBOB Gasoline
    context.crude_oil_2 = continuous_future('CL', roll='calendar', offset=1)
    
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
    crude_oil_price = data.current(context.crude_oil, 'contract')
    crude_oil_2_price = data.current(context.crude_oil_2, 'contract')
    
    # Get target weights to rebalance portfolio
    target_weights = {}
    target_weights[crude_oil_price] = -0.5
    target_weights[crude_oil_2_price] = 0.5
    
    if target_weights:
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[])


def record_price(context, data):
    # Get current price of primary crude oil and gasoline contracts.
    crude_oil_price = data.current(context.crude_oil, 'price')
    gasoline_price = data.current(context.crude_oil_2, 'price')

    
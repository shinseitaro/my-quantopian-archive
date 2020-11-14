"""
This algorithm demonstrates the concept of long-short equity. It uses two price based factors to rank all equities. It then longs the top of the ranking and shorts the bottom. For information on momentum strategies, please see the corresponding lecture on

https://www.quantopian.com/lectures

The dollar volume threshold is in place because orders of thinly traded securities can fail to fill in time and result in worse pricing and returns.

This algorithm was developed as part of 
Quantopian's Lecture Series. Please direct any 
questions, feedback, or corrections to delaney@quantopian.com
"""

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Returns, SimpleMovingAverage, AverageDollarVolume, Latest

import pandas as pd
import numpy as np


class CrossSectionalMomentum(CustomFactor):    
    inputs = [USEquityPricing.close]
    window_length = 252
    
    def compute(self, today, assets, out, prices):
        prices = pd.DataFrame(prices)
        R = (prices / prices.shift(100))
        out[:] = (R.T - R.T.mean()).T.mean()

        
def make_pipeline():
    """
    Create and return our pipeline.
    
    We break this piece of logic out into its own function to make it easier to
    test and modify in isolation.
    
    In particular, this function can be copy/pasted into research and run by itself.
    """

    # Basic momentum metrics.
    cross_momentum = CrossSectionalMomentum()

    
    abs_momentum = Returns(inputs=[USEquityPricing.close], window_length=252)
 
    
    # We only want to trade relatively liquid stocks.
    # Build a filter that only passes stocks that have $10,000,000 average
    # daily dollar volume over the last 20 days.
    dollar_volume = AverageDollarVolume(window_length=20)
    is_liquid = (dollar_volume > 1e7)
    
    # We also don't want to trade penny stocks, which we define as any stock with an
    # average price of less than $5.00 over the last 200 days.
    sma_200 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=200)
    not_a_penny_stock = (sma_200 > 5)
    
    # Before we do any other ranking, we want to throw away the bad assets.
    initial_screen = (is_liquid & not_a_penny_stock)

    # By applying a mask to the rank computations, we remove any stocks that failed 
    # to meet our initial criteria **before** computing ranks.  This means that the 
    # stock with rank 10.0 is the 10th-lowest stock that passed `initial_screen`.
    combined_rank = (cross_momentum.rank(mask=initial_screen) + abs_momentum.rank(mask=initial_screen))


    # Build Filters representing the top and bottom 5% of stocks by our combined ranking system.
    # We'll use these as our tradeable universe each day.
    longs = combined_rank.percentile_between(95, 100)
    shorts = combined_rank.percentile_between(0, 5)
    
    # The final output of our pipeline should only include 
    # the top/bottom 5% of stocks by our criteria.
    pipe_screen = (longs | shorts)


    pipe_columns = {
        'longs':longs,
        'shorts':shorts,
        'combined_rank':combined_rank,
        'abs_momentum':abs_momentum,
        'cross_momentum':cross_momentum
    }

    # Create pipe
    pipe = Pipeline(columns = pipe_columns, screen = pipe_screen)
    return pipe


# Put any initialization logic here.  The context object will be passed to
# the other methods in your algorithm.
def initialize(context):
    
    attach_pipeline(make_pipeline(), 'momentum_metrics')
    
    context.shorts = None
    context.longs = None
    context.output = None
    
    schedule_function(rebalance, date_rules.month_start())
    schedule_function(cancel_open_orders, date_rules.every_day(),
                      time_rules.market_close())
    
    
def before_trading_start(context, data):
    context.output = pipeline_output('momentum_metrics')
    ranks = context.output['combined_rank']
    
    context.longs = ranks[context.output['longs']]
    context.shorts = ranks[context.output['shorts']]
    
    context.active_portfolio = context.longs.index.union(context.shorts.index)
    update_universe(context.active_portfolio)
    
    
def handle_data(context, data):
    pass
 
    
def cancel_open_orders(context, data):
    open_orders = get_open_orders()
    for security in open_orders:
        for order in open_orders[security]:
            cancel_order(order)
            
    record(lever=context.account.leverage,
           exposure=context.account.net_leverage,
           num_pos=len(context.portfolio.positions))
    
    
def rebalance(context, data):
             
    for security in context.shorts.index:
        if get_open_orders(security):
            continue
        if security in data:
            order_target_percent(security, -0.5 / len(context.shorts.index))
            
    for security in context.longs.index:
        if get_open_orders(security):
            continue
        if security in data:
            order_target_percent(security, 0.5 / len(context.longs.index))
            
    for security in context.portfolio.positions:
        if get_open_orders(security):
            continue
        if security in data:
            if security not in (context.longs.index | context.shorts.index):
                order_target_percent(security, 0)

"""
This algorithm demonstrates the concept of long-short equity. It uses two fundamental factors to rank all equities. It then longs the top of the ranking and shorts the bottom. For information on long-short equity strategies, please see the corresponding lecture on

https://www.quantopian.com/lectures

The dollar volume threshold is in place because orders of thinly traded securities can fail to fill in time and result in worse pricing and returns.

WARNING: These factors were selected because they worked in the past over the specific time period we choose. We do not anticipate them working in the future. In practice finding your own factors is the hardest part of developing any long-short equity strategy. This algorithm is meant to serve as a framework for testing your own ranking factors.

This algorithm was developed as part of 
Quantopian's Lecture Series. Please direct any 
questions, feedback, or corrections to delaney@quantopian.com
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.factors import CustomFactor, SimpleMovingAverage
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar

import numpy as np
import pandas as pd


class Value(CustomFactor):
    inputs = [morningstar.income_statement.ebit,
              morningstar.valuation.enterprise_value]
    window_length = 1
    
    def compute(self, today, assets, out, ebit, ev):
        out[:] = ebit[-1] / ev[-1]
        
        
class Quality(CustomFactor):
    
    # Pre-declare inputs and window_length
    inputs = [morningstar.operation_ratios.roe,]
    window_length = 1
    
    def compute(self, today, assets, out, roe):
        out[:] = roe[-1]
        
        
class AvgDailyDollarVolumeTraded(CustomFactor):
    inputs = [USEquityPricing.close, USEquityPricing.volume]
    
    def compute(self, today, assets, out, close_price, volume):
        out[:] = np.mean(close_price * volume, axis=0)

        
def make_pipeline():
    """
    Create and return our pipeline.
    
    We break this piece of logic out into its own function to make it easier to
    test and modify in isolation.
    
    In particular, this function can be copy/pasted into research and run by itself.
    """
    pipe = Pipeline()

    # Basic value and quality metrics.
    value = Value()
    pipe.add(value, "value")
    quality = Quality()
    pipe.add(quality, "quality")
    
     # We only want to trade relatively liquid stocks.
    # Build a filter that only passes stocks that have $10,000,000 average
    # daily dollar volume over the last 20 days.
    dollar_volume = AvgDailyDollarVolumeTraded(window_length=20)
    is_liquid = (dollar_volume > 1e7)
    
    # We also don't want to trade penny stocks, which we define as any stock with an
    # average price of less than $5.00 over the last 200 days.
    sma_200 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=200)
    not_a_penny_stock = (sma_200 > 5)
    
    # Before we do any other ranking, we want to throw away these assets.
    initial_screen = (is_liquid & not_a_penny_stock)

    # Construct and add a Factor representing the average rank of each asset by our 
    # value and quality metrics. 
    # By applying a mask to the rank computations, we remove any stocks that failed 
    # to meet our initial criteria **before** computing ranks.  This means that the 
    # stock with rank 10.0 is the 10th-lowest stock that passed `initial_screen`.
    combined_rank = (
        value.rank(mask=initial_screen) + 
        quality.rank(mask=initial_screen)
    )
    pipe.add(combined_rank, 'combined_rank')

    # Build Filters representing the top and bottom 200 stocks by our combined ranking system.
    # We'll use these as our tradeable universe each day.
    longs = combined_rank.top(200)
    shorts = combined_rank.bottom(200)
    
    # The final output of our pipeline should only include 
    # the top/bottom 200 stocks by our criteria.
    pipe.set_screen(longs | shorts)
    
    pipe.add(longs, 'longs')
    pipe.add(shorts, 'shorts')
    
    return pipe


def initialize(context):
    
    # Set slippage and commission to zero to evaulate the signal generating 
    # ability of the algorithm 
    set_commission(commission.PerShare(cost=0.0075, min_trade_cost=1.0))
    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))

    context.long_leverage = 0.50
    context.short_leverage = -0.50
    context.spy = sid(8554)
    
    attach_pipeline(make_pipeline(), 'ranking_example')
    
    # Used to avoid purchasing any leveraged ETFs 
    context.dont_buys = security_lists.leveraged_etf_list
     
    # Schedule my rebalance function
    schedule_function(func=rebalance, 
                      date_rule=date_rules.month_start(days_offset=0), 
                      time_rule=time_rules.market_open(hours=0,minutes=30), 
                      half_days=True)
    
    # Schedule a function to plot leverage and position count
    schedule_function(func=record_vars, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_close(), 
                      half_days=True)

def before_trading_start(context, data):
    # Call pipeline_output to get the output
    # Note this is a dataframe where the index is the SIDs for all 
    # securities to pass my screen and the columns are the factors which
    output = pipeline_output('ranking_example')
    ranks = output['combined_rank']

    long_ranks = ranks[output['longs']]
    short_ranks = ranks[output['shorts']]

    context.long_weights = (long_ranks / long_ranks.sum())
    log.info("Long Weights:")
    log.info(context.long_weights)
    
    context.short_weights = (short_ranks / short_ranks.sum())
    log.info("Short Weights:")
    log.info(context.short_weights)
    
    context.active_portfolio = context.long_weights.index.union(context.short_weights.index)


def record_vars(context, data):  
    
    # Record and plot the leverage, number of positions, and expsoure of our portfolio over time. 
    record(num_positions=len(context.portfolio.positions),
           exposure=context.account.net_leverage, 
           leverage=context.account.leverage)
    

# This function is scheduled to run at the start of each month.
def rebalance(context, data):
    """
    Allocate our long/short portfolio based on the weights supplied by
    context.long_weights and context.short_weights.
    """
    # Order our longs.
    log.info("ordering longs")
    for long_stock, long_weight in context.long_weights.iterkv():
        if data.can_trade(long_stock):
            if get_open_orders(long_stock):
                continue
            if long_stock in context.dont_buys:
                continue
            order_target_percent(long_stock, context.long_leverage * long_weight)
    
    # Order our shorts.
    log.info("ordering shorts")
    for short_stock, short_weight in context.short_weights.iterkv():
        if data.can_trade(short_stock):
            if get_open_orders(short_stock):
                continue
            if short_stock in context.dont_buys:
                continue
            order_target_percent(short_stock, context.short_leverage * short_weight)
    
    # Sell any positions in assets that are no longer in our target portfolio.
    for security in context.portfolio.positions:
        if get_open_orders(security):
            continue
        if data.can_trade(security):  # Work around inability to sell de-listed stocks.
            if security not in context.active_portfolio:
                order_target_percent(security, 0)
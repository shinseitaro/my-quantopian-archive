from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.filters.morningstar import Q1500US
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.data.sentdex import sentiment
from quantopian.pipeline.factors.eventvestor import (
    BusinessDaysUntilNextEarnings,
    BusinessDaysSincePreviousEarnings,
)
from quantopian.pipeline.filters.eventvestor import IsAnnouncedAcqTarget
from quantopian.pipeline.factors import BusinessDaysSincePreviousEvent
 
def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
     
    # Record tracking variables at the end of each day.
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
     
    # Create our dynamic stock selector.
    attach_pipeline(make_pipeline(), 'my_pipeline')
    
    set_commission(commission.PerTrade(cost=0.000))
    
def make_pipeline():
    
    # 5-day sentiment moving average factor.
    sentiment_factor = SimpleMovingAverage(inputs=[sentiment.sentiment_signal], window_length=5)
    
     # Filter for stocks that are not within 2 days of an earnings announcement.
    not_near_earnings_announcement = ~((BusinessDaysUntilNextEarnings() <= 2)
                                | (BusinessDaysSincePreviousEarnings() <= 2))
    
    # Filter for stocks that are announced acquisition target.
    not_announced_acq_target = ~IsAnnouncedAcqTarget()
    
    # Filter for stocks that had their sentiment signal updated in the last day.
    new_info = (BusinessDaysSincePreviousEvent(inputs=[sentiment.asof_date.latest]) <= 1)
    
    # Our universe is made up of stocks that have a non-null sentiment signal that was updated in
    # the last day, are not within 2 days of an earnings announcement, are not announced acquisition
    # targets, and are in the Q1500US.
    universe = (Q1500US() 
                & sentiment_factor.notnull() 
                & not_near_earnings_announcement
                & not_announced_acq_target
                & new_info)
    
    # A classifier to separate the stocks into quantiles based on sentiment rank.
    sentiment_quantiles = sentiment_factor.rank(mask=universe, method='average').quantiles(3)
    
    # Go short the stocks in the 0th quantile, and long the stocks in the 2nd quantile.
    pipe = Pipeline(
        columns={
            'sentiment': sentiment_quantiles,
            'shorts': sentiment_quantiles.eq(0),
            'longs': sentiment_quantiles.eq(2),
        },
        screen=universe
    )
    
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
  
    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index.tolist()
    
 
def my_rebalance(context,data):
    """
    Place orders according to our schedule_function() timing.
    """
    
    # Compute our portfolio weights.
    long_secs = context.output[context.output['longs']].index
    long_weight = 0.5 / len(long_secs)
    
    short_secs = context.output[context.output['shorts']].index
    short_weight = -0.5 / len(short_secs)

    # Open our long positions.
    for security in long_secs:
        if data.can_trade(security):
            order_target_percent(security, long_weight)
    
    # Open our short positions.
    for security in short_secs:
        if data.can_trade(security):
            order_target_percent(security, short_weight)

    # Close positions that are no longer in our pipeline.
    for security in context.portfolio.positions:
        if data.can_trade(security) and security not in long_secs and security not in short_secs:
            order_target_percent(security, 0)
    
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    long_count = 0
    short_count = 0

    for position in context.portfolio.positions.itervalues():
        if position.amount > 0:
            long_count += 1
        if position.amount < 0:
            short_count += 1
            
    # Plot the counts
    record(num_long=long_count, num_short=short_count, leverage=context.account.leverage)

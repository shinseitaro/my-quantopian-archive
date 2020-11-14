
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
from quantopian.pipeline.data.sentdex import sentiment


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
         
def make_pipeline():
    sentiment_factor=sentiment.sentiment_signal.latest
    universe = (Q1500US() & sentiment_factor.notnull())
    sentiment_quantiles = sentiment_factor.rank(mask=universe, method='average').quantiles(2)
    pipe = Pipeline(columns={'sentiment':sentiment_factor,
                             'longs':(sentiment_factor >= 4), 
                             'shorts':(sentiment_factor <= -2), },
                    screen=universe)
    return pipe
                    
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
  
    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index
    
    
     
def my_rebalance(context,data):
    long_sec = context.output[context.output['longs']].index 
    long_weight = 0.5 / len(long_sec) 
    
    short_sec = context.output[context.output['shorts']].index 
    short_weight = -0.5 / len(short_sec) 
    
    for sec in long_sec:
        if data.can_trade(sec):
            order_target_percent(sec, long_weight)
    for sec in short_sec:
        if data.can_trade(sec):
            order_target_percent(sec, short_weight)
    
    for sec in context.portfolio.positions:
        if data.can_trade(sec) and sec not in long_sec and sec not in short_sec:
            order_target_percent(sec, 0) 
            
    
    
def my_record_vars(context, data):
    long_count = 0 
    short_count = 0 
    for position in context.portfolio.positions.itervalues():
        if position.amount > 0: 
            long_count += 1
        elif position.amount < 0: 
            short_count += 1
    record(num_longs=long_count, num_shorts=short_count, leverage=context.account.leverage) 
    
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

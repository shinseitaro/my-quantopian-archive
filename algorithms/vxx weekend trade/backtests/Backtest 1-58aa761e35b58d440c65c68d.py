"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q500US
from quantopian.pipeline.factors import CustomFactor, Latest

def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    context.vxx = sid(38054)
    schedule_function(rebalance_monday, date_rules.week_start(), time_rules.market_open())
    schedule_function(rebalance_tuesday, date_rules.week_start(days_offset=1), time_rules.market_open())
    attach_pipeline(make_pipeline(), 'my_pipeline')
    
         
def make_pipeline():
    """
    A function to create our dynamic stock selector (pipeline). Documentation on
    pipeline can be found here: https://www.quantopian.com/help#pipeline-title
    """
    open = Latest(inputs=[USEquityPricing.open], window_length=1)
    close = Latest(inputs=[USEquityPricing.close], window_length=1)
     
    pipe = Pipeline(
        columns = {
            'close': close,
            'open': open
        }
    )
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
  
    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index

 
def rebalance_tuesday(context,data):
    if (data.can_trade(context.vxx)) & (context.portfolio.positions[context.vxx].amount != 0):
        order_percent(context.vxx, 0)
        log.info('Closed VXX') 
    else:
        log.warn('Cannot close vxx in some reasons')
        
   
def rebalance_monday(context,data):
    order_percent(context.vxx, -1.0)
    log.info('VXX Short Position Open')
        

def handle_data(context,data):
    """
    Called every minute.
    """
    pass

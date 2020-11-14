"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, CustomFactor, Returns
from quantopian.pipeline.filters import StaticAssets
from quantopian.pipeline.filters.morningstar import Q1500US 
 
def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    context.vxx = sid(38054)
    context.tvix = sid(40515)
    context.xiv = sid(40516)
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close())
    set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    set_slippage(slippage.FixedSlippage(spread=0))
     
    # Record tracking variables at the end of each day.
    #schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
     
    # Create our dynamic stock selector.
    attach_pipeline(make_pipeline(), 'my_pipeline')
class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]
        
def make_pipeline():
    """
    A function to create our dynamic stock selector (pipeline). Documentation on
    pipeline can be found here: https://www.quantopian.com/help#pipeline-title
    """
    
    sids = StaticAssets(symbols('VXX', 'XIV', 'TVIX'))
    base_universe = sids 

    # Factor of yesterday's close price.
    yesterday_close = PrevClose()
    close_to_close = Returns(window_length=2)
    
    
    pipe = Pipeline(
        screen = base_universe,
        columns = {
            'yesterday_close': yesterday_close,
            'close_to_close': close_to_close, 
            
        }
    )
    return pipe
 
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
    context.go = False 
    if abs(context.output.ix[context.vxx]['close_to_close']) > 0.01:
        print context.output.ix[context.vxx]['close_to_close'] 
        context.go = True
     
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def my_rebalance(context,data):

    if context.portfolio.positions[context.vxx]:
        if data.can_trade(context.vxx):
            order_target(context.vxx, 0)
    if context.portfolio.positions[context.xiv]:
        if data.can_trade(context.xiv):
            order_target(context.xiv, 0)
            
    if context.portfolio.positions[context.tvix]:
        if data.can_trade(context.tvix):
            order_target(context.tvix, 0)
            

    if context.go and data.can_trade(context.vxx) and data.can_trade(context.tvix):
    #if data.can_trade(context.xiv) and data.can_trade(context.tvix):        
        order_percent(context.vxx, 0.6)
        order_percent(context.tvix,-0.3) 
        #order_percent(context.xiv,-0.6)         
        
        
        
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

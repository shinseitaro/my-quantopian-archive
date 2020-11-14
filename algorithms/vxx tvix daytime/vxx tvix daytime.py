"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, CustomFactor, Returns
from quantopian.pipeline.filters import StaticAssets
from quantopian.pipeline.filters.morningstar import Q1500US 
import pytz

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0:"Sun", 1:"Mon", 2:"Tue", 3:"Wed", 4:"Thu", 5:"Fri", 6:"Sat"}
    msgs = '\t%s\t%s:\t%s' % (dt.strftime('%Y/%m/%d %H:%M'), youbidict[int(youbi)], msgs) 
    log.info(msgs)

def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    context.vxx = sid(38054)
    context.tvix = sid(40515)
    context.xiv = sid(40516)
    context.forward = sid(8554)
    context.inverse = sid(32382)
    
    
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance_open, date_rules.every_day(), time_rules.market_close(minutes=60))    
    
    schedule_function(my_rebalance_close, date_rules.every_day(), time_rules.market_close())

    
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
        logging("VXX Return: %s" % context.output.ix[context.vxx]['close_to_close'] )
        context.go = True
  
    # These are the securities that we are interested in trading each day.
    #context.security_list = context.output.index
     
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def my_rebalance_close(context,data):

    if abs(context.portfolio.positions[context.vxx].amount) > 0 and data.can_trade(context.vxx):
        
        logging("VXX closed @ %s (Opened @ %s at %s)" % 
                (context.portfolio.positions[context.vxx].last_sale_price,
                 context.portfolio.positions[context.vxx].cost_basis,
                 context.portfolio.positions[context.vxx].last_sale_date.astimezone(pytz.timezone('US/Eastern')).strftime('%Y/%m/%d  %H:%M'))
                )
        order_target(context.vxx, 0)
            
    if abs(context.portfolio.positions[context.tvix].amount) > 0 and data.can_trade(context.tvix):
        logging("TVIX closed @ %s (Opened @ %s at %s)" % 
                (context.portfolio.positions[context.tvix].last_sale_price,
                 context.portfolio.positions[context.tvix].cost_basis,
                context.portfolio.positions[context.vxx].last_sale_date.astimezone(pytz.timezone('US/Eastern')).strftime('%Y/%m/%d  %H:%M')))
        order_target(context.tvix, 0)            
            
def my_rebalance_open(context,data):

    if context.go and data.can_trade(context.vxx) and data.can_trade(context.tvix):
        order_percent(context.vxx, 0.6)
        order_percent(context.tvix,-0.3)
        
 
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


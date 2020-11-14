from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, CustomFactor, Returns
from quantopian.pipeline.filters import StaticAssets
from quantopian.pipeline.filters.morningstar import Q1500US 
 
def initialize(context):
    context.no_leveraged = sid(25426)
    context.leveraged = sid(48643)
    schedule_function(my_rebalance_open, date_rules.every_day(), time_rules.market_open(minutes=60))    
    schedule_function(my_rebalance_close, date_rules.every_day(), time_rules.market_close())
    
    set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    set_slippage(slippage.FixedSlippage(spread=0))
    attach_pipeline(make_pipeline(context), 'my_pipeline')
   

class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]
        
def make_pipeline(context):
    
    sids = StaticAssets([context.leveraged, context.no_leveraged])
    base_universe = sids 

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
    context.output = pipeline_output('my_pipeline')
    context.go = False 
    if abs(context.output.ix[context.leveraged]['close_to_close']) > 0.01:
        print context.output.ix[context.leveraged]['close_to_close'] 
        context.go = True
 

def my_rebalance_close(context,data):
    if context.portfolio.positions[context.leveraged]:
        if data.can_trade(context.leveraged):
            order_target(context.leveraged, 0)
            
    if context.portfolio.positions[context.no_leveraged]:
        if data.can_trade(context.no_leveraged):
            order_target(context.no_leveraged, 0)
            
def my_rebalance_open(context,data):

    if context.go and data.can_trade(context.leveraged) and data.can_trade(context.no_leveraged):

        order_percent(context.leveraged, 0.3)
        order_percent(context.no_leveraged, 0.6) 
        
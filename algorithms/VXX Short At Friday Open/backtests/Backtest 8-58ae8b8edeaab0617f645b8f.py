"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q500US
 
def initialize(context):
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.order_id = None
    context.order_id2 = None
    
    # ショートポジション 金曜日のクローズ
    schedule_function(my_rebalance_position_open, date_rules.week_end(), time_rules.market_close())
    # ポジションクローズ　水曜日のオープン
    schedule_function(my_rebalance_position_close, date_rules.week_start(2), time_rules.market_open())
    
def my_rebalance_position_open(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)

    if(data.can_trade(context.vxx)) & (execdate.day <= 25):
        context.order_id = order_percent(context.vxx, -0.5)
        context.order_id2 = order_percent(context.vxz, 0.5)

        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))
        log.info('VXZ Long Position Opened: %s @ %s: Total %s' % (
                get_order(context.order_id2).amount, data.current(context.vxz, 'price'), 
                get_order(context.order_id2).amount * data.current(context.vxz, 'price')))
        
def my_rebalance_position_close(context, data):
    execdate = get_datetime('US/Eastern')
    log.info('Close at %s' % execdate)
    order_percent(context.vxx, 0)
    order_percent(context.vxz, 0)
   
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

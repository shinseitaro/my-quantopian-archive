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
    context.order_id = None
    
    # ショートポジション 金曜日のクローズ
    schedule_function(my_rebalance_position_open, date_rules.week_end(), time_rules.market_close())
    # ポジションクローズ　水曜日のオープン
    schedule_function(my_rebalance_position_close, date_rules.week_start(2), time_rules.market_open())
    
def my_rebalance_position_open(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)

    if(data.can_trade(context.vxx)) & (execdate.day <= 25):
        context.order_id = order_percent(context.vxx, -1.0)
        log.info('VXX Short Position Opened: %s' % get_order(context.order_id).amount)
        
def my_rebalance_position_close(context, data):
    if context.order_id == None:
        log.warn('There seems to be NO Open Position. Please Check the status')
    else:
        log.info('Order ID %s will be closed now' % context.order_id)
        order_percent(context.vxx, 0)
    context.order_id = None  
    
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

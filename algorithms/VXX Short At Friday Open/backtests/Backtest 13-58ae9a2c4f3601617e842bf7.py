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
    context.spx = sid(8554)
    context.order_id = None
    context.order_id2 = None
    
    # ショートポジション 金曜日のクローズ
    schedule_function(my_rebalance_position_open, date_rules.week_end(), time_rules.market_close())
    # ポジションクローズ　水曜日のオープン
    schedule_function(my_rebalance_position_close, date_rules.week_start(2), time_rules.market_open())
    
    schedule_function(my_record, date_rules.every_day(), time_rules.market_close())
    
def my_rebalance_position_open(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)

    if(data.can_trade(context.vxx)) & (execdate.day <= 25):
        context.order_id = order_percent(context.vxx, -1.0)
        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))

        
def my_rebalance_position_open1(context,data):
    execdate = get_datetime('US/Eastern')
    log.info('Today is %s' % execdate)

    if(data.can_trade(context.vxx)) & (execdate.day <= 25):
        context.order_id = order_percent(context.vxx, -0.2)
        context.order_id2 = order_percent(context.vxz, 0.2)

        log.info('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))
        log.info('VXZ Long Position Opened: %s @ %s: Total %s' % (
                get_order(context.order_id2).amount, data.current(context.vxz, 'price'), 
                get_order(context.order_id2).amount * data.current(context.vxz, 'price')))
        
def my_rebalance_position_close(context, data):
    execdate = get_datetime('US/Eastern')
    context.order_id = order_target(context.vxx, 0.0)
    log.info('Close at %s: %s' % (execdate, data.current(context.vxx, 'price')))
    # order_percent(context.vxz, 0)

def my_record(context, data):
    log.info('PnL on %s is %s ' % ( get_datetime('US/Eastern'), context.portfolio.pnl))
    log.info('Positions on %s is %s' %( get_datetime('US/Eastern'), context.portfolio.positions))
    record(vxx=data.current(context.vxx, 'price'))
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

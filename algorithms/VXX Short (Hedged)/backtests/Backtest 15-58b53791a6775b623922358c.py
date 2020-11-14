"""
VXX Short VXZ Long 
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q500US
from zipline.utils import tradingcalendar

import pandas as pd
import re


def initialize(context):
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.spx = sid(8554)
    context.ivts = None
    context.ivts_vixvxx = None
    context.pfoliopl = None
    context.trade_price = None
    context.is_trade_open = False
    context.vx1 = None
    context.contango = None 
    context.tradabale_dates = 0
    context.traded_dates = 0
    context.msg_isBackwardation = None 

    
    set_slippage(slippage.VolumeShareSlippage(volume_limit=0.025, price_impact=0.1))
 
    fetch_csv('https://dl.dropboxusercontent.com/u/264353/vix_update_2017-02-27.csv', 
              symbol='vx', date_column='Date',  date_format='%y-%m-%d')

    # ショートポジション 金曜日のクローズ5分前
    schedule_function(my_rebalance_position_open_vxz, date_rules.week_end(), time_rules.market_close(minutes=5))
    # ショートポジション 金曜日のクローズ
    schedule_function(my_rebalance_position_open_vxx, date_rules.week_end(), time_rules.market_close())

    
    # ポジションクローズ　水曜日のオープン
    schedule_function(my_rebalance_position_close, date_rules.week_start(2), time_rules.market_open())
    
    # record はリバランスを終えてから描く．リバランスで更新しているデータを使っているから，
    schedule_function(my_record, date_rules.every_day(), time_rules.market_close())
    
def logging(msgs):
    dt = get_datetime('US/Eastern')
    msgs = '%s: %s' % (dt, msgs)  
    log.info(msgs)

def before_trading_start(context, data):
    context.go = False
    context.order_id = None
    context.order_id2 = None
    
def myfactor(context, data):
    context.ivts = data.current(context.vxx, 'price') / data.current(context.vxz, 'price')
    context.ivts_vixvxx = context.vix / context.vxv 
    if context.ivts_vixvxx <= 0.91:
        context.go = True

#         
def isBackwardation(context, data):
    context.vx1 = data.current('vx', 'VX1 High')
    context.vx2 = data.current('vx', 'VX2 High')
    context.vx3 = data.current('vx', 'VX3 High')
    context.vix = data.current('vx', 'VIX High')
    
    context.contango = context.vx1 - context.vix
    if (context.contango > 0) & (context.vx2/context.vx1 > context.vx1/context.vix):
        context.go = True
        context.msg_isBackwardation = None
    else:
        context.go = False
        context.msg_isBackwardation = 'NoGO. contango: %s, contango comp %s ' % \
        (context.contango, context.vx2/context.vx1 > context.vx1/context.vix)
        
        
def my_rebalance_position_open_vxz(context,data):
    execdate = get_datetime('US/Eastern')
    isBackwardation(context, data)
    
    if execdate.day >= 25:
        logging('Today is %s: We do not trade last 5 days of a Month' % execdate)
        return None
    
    if not context.go:
        logging(context.msg_isBackwardation)
        return None 
    
    if data.can_trade(context.vxz):
        context.order_id2 = order_percent(context.vxz, 0.5)
        

def my_rebalance_position_open_vxx(context,data):
    logging('context.portfolio.positions[context.vxz].amount: %s ' % context.portfolio.positions[symbol('VXZ')].amount)
    if context.order_id2: 
        context.order_id = order_value(context.vxx, 
                                       context.portfolio.positions[symbol('VXZ')].amount * data.current(context.vxz, 'price') * -1)
        logging('VXX Short Position Opened: %s @ %s: Total %s' %( 
                 get_order(context.order_id).amount, data.current(context.vxx, 'price'),
                 get_order(context.order_id).amount * data.current(context.vxx, 'price')))

        logging('VXZ Long Position Opened: %s @ %s: Total %s' % (
                get_order(context.order_id2).amount, data.current(context.vxz, 'price'), 
                context.portfolio.positions[symbol('VXZ')].amount * data.current(context.vxz, 'price')))

        
def my_rebalance_position_close(context, data):

    context.order_id = order_target(context.vxx, 0.0)
    context.order_id = order_target(context.vxz, 0.0)
    logging('VXX Close @ %s' % data.current(context.vxx, 'price'))
    logging('VXZ Close @ %s' % data.current(context.vxz, 'price'))    
    
    
def my_record(context, data):
    if context.is_trade_open:
        logging('PnL is %s ' % context.portfolio.pnl)
    # logging('PnL on %s is %s ' % ( get_datetime('US/Eastern'), context.portfolio.pnl))
    #record(vxx=data.current(context.vxx, 'price'))
    # record(vxz=data.current(context.vxz, 'price'))
    # record(ivts=context.ivts) 
    # record(ivts_vixvxx = context.ivts_vixvxx) 
    #record(vix=data.current('vx1', 'Close'))
    #record(vx1=data.current('vx', 'VX1 Close'))
    record(contango=context.contango)
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass



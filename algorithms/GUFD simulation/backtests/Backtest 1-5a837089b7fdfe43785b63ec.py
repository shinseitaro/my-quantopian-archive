from __future__ import division

"""
特定の日付で特定の銘柄を取引

"""
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import Q1500US
from datetime import datetime 


def initialize(context):

    ##銘柄と日付リスト
    context.sid_date_list = [
        (sid(24), "2017/08/02"),
        (sid(46631), "2017/08/02"),
        (sid(42950), "2017/08/03"),
        ]
    
    ## エントリー
    algo.schedule_function(
        rebalance,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=30),
    )
    ## クローズ
    algo.schedule_function(
        all_close,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=70),
    )
    

def make_pipeline():
    pass 

def before_trading_start(context, data):
    pass 

def rebalance(context, data):
    today = get_datetime('US/Eastern').strftime("%Y/%m/%d")
    todays_order = []
    log.info('today: {}'.format(today))
    for s, d in context.sid_date_list:
        log.info(d)
        if d == today:
            todays_order.append(s)
    for s in todays_order:
        if data.can_trade(s):
            order_target_percent(s, 1.0/len(todays_order)*0.9)
def all_close(context, data):
    for s in context.portfolio.positions:
        order_target(s,0)

def handle_data(context, data):
    pass
"""
週間の間に下がった銘柄１０個を翌週ロング
同じく上がった銘柄を１０個ショート
を毎週繰り返す
一応平均回帰に近い話
１０個がいいかはわかんない
ただ実証研究はある模様
"""
from __future__ import division
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import Q1500US,Q500US
from quantopian.pipeline.factors import Returns
import pandas as pd 



def initialize(context):
    """
    Called once at the start of the algorithm.
    """
    # Rebalance every day, 1 hour after market open.
    algo.schedule_function(
        rebalance,
        algo.date_rules.week_start(),
        algo.time_rules.market_open(),
    )
    algo.schedule_function(
        rebalance_checker,
        algo.date_rules.week_start(),
        algo.time_rules.market_open(minutes=5),
    )    
    # Record tracking variables at the end of each day.
    algo.schedule_function(
        record_vars,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(),
    )

    # Create our dynamic stock selector.
    algo.attach_pipeline(make_pipeline(), 'pipeline')
    context.df = None 


def make_pipeline():
    base_universe = Q500US()

    # 一週間のリターンをとりあえず過去５日間のリターンと考える
    fiveday_return = Returns(window_length=5) 

    pipe = Pipeline(
        screen=base_universe,
        columns={
            'fiveday_return': fiveday_return,
        }
    )
    return pipe

def before_trading_start(context, data):
    context.output = algo.pipeline_output('pipeline')


def rebalance(context, data):
    df = context.output.sort_values(by="fiveday_return")
    weaks = df.head(10)
    strongs = df.tail(10)
    
    context.orders =list()
    
    
    for sid in weaks.index:
        if data.can_trade(sid):
            context.orders.append(order_target_percent(sid, 1.0/20))
            
    for sid in strongs.index:
        if data.can_trade(sid):
            context.orders.append(order_target_percent(sid, -1.0/20))
            
def rebalance_checker(context, data):
    for order_id in context.orders:
        order_obj = get_order(order_id)
        if order_obj.status != 1: # not filled
            cancel_order(order_id)
            log.warn("CANCELLED {}, order status {}".format(order_obj.sid.symbol, order_obj.status))
            

def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass


def handle_data(context, data):
    """
    Called every minute.
    """
    pass
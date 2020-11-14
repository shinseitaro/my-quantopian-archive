"""
週間の間に下がった銘柄１０個を翌週ロング
同じく上がった銘柄を１０個ショート
を毎週繰り返す
一応平均回帰に近い話
１０個がいいかはわかんない
ただ実証研究はある模様

canncel される株が多すぎるので，キャンセルされなかった株をポジ直すコードを入れる
https://www.quantopian.com/research/notebooks/studies/Week%20Short%20Long%20Strategy%20.ipynb
リサーチする

"""
from __future__ import division
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import Q1500US,Q500US,default_us_equity_universe_mask,make_us_equity_universe
from quantopian.pipeline.factors import Returns, SimpleMovingAverage, AverageDollarVolume
from quantopian.pipeline.classifiers.morningstar import Sector

import pandas as pd 



def initialize(context):
    """
    Called once at the start of the algorithm.
    """
    context.holding = 10
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

def MYQ500US():
    return make_us_equity_universe(
        target_size=500,
        rankby=AverageDollarVolume(window_length=200),
        mask=default_us_equity_universe_mask(),
        groupby=Sector(),
        max_group_weight=1.0,
        smoothing_func=lambda f: f.downsample('month_start'),
    )

def make_pipeline():
    base_universe = MYQ500US()# Q500US()

    # 一週間のリターンをとりあえず過去５日間のリターンと考える
    fiveday_return = Returns(window_length=5) 
    sma30 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=30)
    remove_penny_stocks = sma30 > 10.0
    remove_expensive_stocks = sma30 < 100.0
    
    pipe = Pipeline(
        screen=base_universe & remove_penny_stocks & remove_expensive_stocks,
        columns={
            'fiveday_return': fiveday_return,
        }
    )
    return pipe

def before_trading_start(context, data):
    context.output = algo.pipeline_output('pipeline')


def rebalance(context, data):
    context.orders = list()
    df = context.output.sort_values(by="fiveday_return")
    df = df.dropna()
    weaks = df.head(context.holding)
    strongs = df.tail(context.holding)
    
    df_candidate = pd.concat([weaks, strongs])
    df_candidate["weight"] = df_candidate["fiveday_return"]/df_candidate["fiveday_return"].abs().sum()
    #df_candidate["weight"] = 1.0 / len(df_candidate) * np.sign(df_candidate["fiveday_return"])
    df_candidate["can_trade"] = data.can_trade(df_candidate.index)
    df_candidate = df_candidate[df_candidate["can_trade"]]
    df_candidate["isOrdered"] = False
    
    for sid, row in df_candidate.iterrows():
        try:
            order_id = order_target_percent(sid, row["weight"] * -1.0)
        except ValueError:
            log.error(df_candidate.ix[sid])
            
        if order_id == None:
            log.warn("CANNOT ORDER {}".format(sid))
        else:
            context.orders.append(order_id)
            df_candidate.at[sid, "isOrdered"] = True
            
    context.df_candidate = df_candidate.copy() 
            
def rebalance_checker(context, data):
    for order_id in context.orders:
        order_obj = get_order(order_id)
        if order_obj== None:
            log.warn("No status for {}".format(order_id))
            context.df_candidate.at[order_obj.sid, "isOrdered"] = False
            
        elif order_obj.status != 1: # not filled
            cancel_order(order_id)
            log.warn("CANCELLED {}, order status {}".format(order_obj.sid.symbol, order_obj.status))
            context.df_candidate.at[order_obj.sid, "isOrdered"] = False

    ## 最終的に取引できた銘柄だけでもう一度ポジションを作りなおす
    context.df_candidate = context.df_candidate[context.df_candidate["isOrdered"]] 
    context.df_candidate["weight"] = context.df_candidate["fiveday_return"]/context.df_candidate["fiveday_return"].abs().sum()
    for sid, row in context.df_candidate.iterrows():
        order_target_percent(sid, row["weight"] * -1.0)
        
            
        

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
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
    # holdする株数（片側）
    context.holding = 50
    # 毎週，週初めにリバランス
    algo.schedule_function(
        rebalance,
        algo.date_rules.week_start(),
        algo.time_rules.market_open(),
    )
    # 取引出来たかどうかのチェッカー
    algo.schedule_function(
        rebalance_checker,
        algo.date_rules.week_start(),
        algo.time_rules.market_open(minutes=5),
    )    
    
    algo.attach_pipeline(make_pipeline(), 'pipeline')
    set_slippage(slippage.VolumeShareSlippage(volume_limit=1.00))
    
    context.df = None 

def make_pipeline():
    base_universe = Q500US()

    # 一週間のリターンをとりあえず過去５日間のリターンと考える
    # 本当は，休日の事も考えなくては行けないが，とりあえず決め打ち．
    fiveday_return = Returns(window_length=5) 
    
    # 過去30日の移動平均を取得
    sma30 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=30)
    # 移動平均が10ドル以上
    remove_penny_stocks = sma30 > 10.0
    # 過去30日の売買高
    dollar_volume = AverageDollarVolume(window_length=30)
    # 上位１０％だけを対象
    high_dollar_volume = dollar_volume.percentile_between(90, 100)
    
    pipe = Pipeline(
        screen=base_universe & remove_penny_stocks & high_dollar_volume,
        columns={
            'fiveday_return': fiveday_return,
        }
    )
    return pipe

def before_trading_start(context, data):
    context.output = algo.pipeline_output('pipeline')


def rebalance(context, data):
    context.output = context.output.dropna()
    
    # 過去5日間リターンの下位
    df_weaks = context.output.nlargest(context.holding, "fiveday_return")
    # 過去5日間リターンの上位
    df_strongs = context.output.nsmallest(context.holding, "fiveday_return")
    
    df = pd.concat([df_weaks, df_strongs])
    # Weight
    df["weight"] = df["fiveday_return"]/df["fiveday_return"].abs().sum()
    # トレード可能な銘柄だけフィルタリング
    df["can_trade"] = data.can_trade(df.index)
    df = df[df["can_trade"]]
    # orderが通ったかどうかを確認するコラム
    df["isOrdered"] = False
    # orderid を格納するコラム
    df["order_id"] = False 
    
    
    for sid, row in df.iterrows():
        try:
            # 上位銘柄をShort,下位銘柄をLong
            order_id = order_target_percent(sid, row["weight"] * -1.0)
            log.info(order_id)
        except ValueError:
            log.error(df.ix[sid])
            
        if order_id == None:
            log.warn("CANNOT ORDER {}".format(sid))
        else:
            df.at[sid, "isOrdered"] = True
            df.at[sid, "order_id"] = order_id
            
    context.df = df.copy() 
    log.info(context.df)
            
def rebalance_checker(context, data):
    df = context.df.copy()
    
    for sid, row in df.iterrows():
        order_obj = get_order(row["order_id"])
        if order_obj== None:
            log.warn("No status for {}".format(row["order_id"]))
            df.at[sid, "isOrdered"] = False
            
        elif order_obj.status != 1: # not filled
            cancel_order(row["order_id"])
            log.warn("CANCELLED {}, order status {}".format(sid.symbol, order_obj.status))
            df.at[sid, "isOrdered"] = False

    ## orderが通らなかったリスト
    not_orders = df[df["isOrdered"] == False]
    log.warn("Not Ordered: {} ({})".format(len(not_orders), not_orders.index.tolist()))
        

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
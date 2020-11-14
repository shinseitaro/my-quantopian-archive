"""
Quantopian Lecture Sample: Momentum Trading 1　の勉強
long short equity 
全株をランク分けしてロングショートする
上位をロング，下位をショート
"""

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Returns, SimpleMovingAverage, AverageDollarVolume, Latest

import pandas as pd
import numpy as np

class CrossSectionalMomentum(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 252 
    
    def compute(self, today, assets, out, prices):
        prices = pd.DataFrame(prices)
        R = (prices / prices.shift(100))
        # 各銘柄100日前とのDiffを取得し，それを転置して各日付で標準化
        # それをもう一度転置して，各銘柄の平均を出す．
        # out は 銘柄数 * 1 列シリーズ
        out[:] = (R.T - R.T.mean()).T.mean()
        
def make_pipeline():
    """
    pipeline を作る
    make_pipeline を作ったほうが，research にもコピペして使えるし，テストや修正も簡単に出来るので，幸せになれます
    """
    # クロスモメンタム
    cross_momentum = CrossSectionalMomentum()
    # Returns で過去252分全てのクローズベースのリターンを取得
    abs_momentum = Returns(inputs=[USEquityPricing.close], window_length = 252)
    # 流動性がある株式だけ取引する.過去20日間，平均1千万ドル平均の取引高（price*volume）があるものだけを取引
    dollar_volume = AverageDollarVolume(window_length=20)
    is_liquid = (dollar_volume > 1e7) 
    # 過去200日平均で株価5ドル以下のペニーストックはトレードしない．
    sma_200 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=200)
    not_a_penny_stock = (sma_200 > 5) 
    # 不必要な銘柄は取り除く
    initial_screen = (is_liquid & not_a_penny_stock)
    # cross momentum を適用したあとに，ランク付けをする
    combined_rank = (cross_momentum.rank(mask=initial_screen) + abs_momentum.rank(mask=initial_screen))
    # top 5 % をロング    
    longs = combined_rank.percentile_between(95, 100)
    shorts = combined_rank.percentile_between(0, 5)
    # パイプラインにロングショートする銘柄を取得
    pipe_screen = (longs | shorts) 
    
    pipe_columns = {
        'longs': longs,
        'shorts': shorts,
        'combined_rank': combined_rank, 
        'abs_momentum': abs_momentum, 
        'cross_momentum': cross_momentum, 
    }
    
    # パイプ作成
    pipe = Pipeline(columns=pipe_columns, screen=pipe_screen)
    return pipe


def initialize(context):
    attach_pipeline(make_pipeline(), 'momentum_metrics')
    context.shorts = None
    context.longs = None
    context.output = None
    
    schedule_function(rebalance, date_rules.month_start())
    schedule_function(cancel_open_orders, date_rules.every_day(),
                      time_rules.market_close())
    

def before_trading_start(context, data): 
    context.output = pipeline_output('momentum_metrics')
    ranks = context.output['combined_rank']
    context.longs = ranks[context.output['longs']]
    context.shorts = ranks[context.output['shorts']]
    # union は 論理和． set{a,b,c}.union(set{'a, d'}) => set{a,b,c,d}
    context.active_portfolio = context.longs.index.union(context.shorts.index)
    update_universe(context.active_portfolio)
    

def handle_data(context, data):
    pass

def cancel_open_orders(context, data):
    open_orders = get_open_orders()
    for security in open_orders: 
        for order in open_orders[security]:
            cancel_order(order)
            
    record(lever=context.account.leverage, 
           exposure=context.account.net_leverage, 
           num_pos=len(context.portfolio.positions))
    
def rebalance(context, data):
    for security in context.shorts.index:
        if get_open_orders(security):
            continue
        if security in data:
            order_target_percent(security, -0.5 / len(context.shorts.index))
    for security in context.longs.index:
        if get_open_orders(security):
            continue
        if security in data: 
           order_target_percent(security, 0.5 / len(context.longs.index))
        
    for security in context.portfolio.positions:
        if get_open_orders(security):
            continue
        if security in data: 
            if security not in (context.longs.index | context.shorts.index):
                order_target_percent(security, 0)
  
    
    
    
    
                     
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    

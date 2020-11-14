"""
条件にあう銘柄を探して算出する
"""
from __future__ import division

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import Q500US 
from quantopian.pipeline.experimental import QTradableStocksUS
from quantopian.pipeline.factors import SimpleMovingAverage

def initialize(context):
    # 空のパイプラインを作ります
    pipe = Pipeline()
    # research では run_pipeline 
    # algorithm では，initilize 内で attach_pipeline を実行して，パイプラインを毎日実行するように設定します．
    
    # ほしいデータを定義
    # pipeline 用に定義された　移動平均 SimpleMovingAverage を使う
    SMA10 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=10)
    SMA30 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=30)
    pipe.add(SMA10, 'SMA10') 
    pipe.add(SMA30, 'SMA30') 
  
    ## raw_weights 
    raw_weights = (SMA10 - SMA30) / SMA30
    abs_raw_weights = raw_weights.abs()
    pipe.add(raw_weights, 'raw_weights')
    pipe.add(abs_raw_weights, 'abs_raw_weights')
    
    pipe.set_screen(Q500US())
    
    attach_pipeline(pipe, "my_pipeline") 

    # 毎週月曜日にどの銘柄を保有するか決定する
    schedule_function(rebalance,
                      date_rules.week_start(),
                      time_rules.market_open())

    # 毎週金曜日の取引時間終了時に持っている銘柄を全部クローズする．
    schedule_function(all_position_close,
                      date_rule = date_rules.week_end(days_offset=0),
                      time_rule = time_rules.market_close())
    

def rebalance(context, data):
    """
    rebalance: ポジション調整．
    """
    output = pipeline_output('my_pipeline')
    # pandas dataframe 
    security_list = output.sort_values(by = "abs_raw_weights", ascending=False).head()
    
    # Calculate our target weights.
    security_list["normalize_weights"] = security_list["raw_weights"] / security_list["abs_raw_weights"].sum()

    # Place orders for each of our securities.
    for security in security_list.index:
        if data.can_trade(security):
            order_target_percent(security, security_list["raw_weights"][security])

def all_position_close(context, data): 
    for pos in context.portfolio.positions:
        if data.can_trade(pos):
            order_target_percent(pos, 0) 

def before_trading_start(context, data):
    pass 
   
def handle_data(context, data):
    pass 

    
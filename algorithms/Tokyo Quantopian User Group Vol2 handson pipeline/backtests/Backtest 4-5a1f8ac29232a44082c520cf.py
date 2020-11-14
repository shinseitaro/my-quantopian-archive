"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
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
    raw_weights = SMA10 / SMA30 - 1
    abs_raw_weights = raw_weights.abs()
    pipe.add(raw_weights, 'raw_weights')
    pipe.add(abs_raw_weights, 'abs_raw_weights')
    
    pipe.set_screen(Q500US())
    
    attach_pipeline(pipe, "my_pipeline") 

    # Rebalance every Monday (or the first trading day if it's a holiday)
    # at market open.
    schedule_function(rebalance,
                      date_rules.week_start(),
                      time_rules.market_open())

    schedule_function(all_position_close,
                      date_rule = date_rules.week_end(),
                      time_rule = time_rules.market_close())
    
    
def before_trading_start(context, data):
    # initialize で定義した pipeline を毎日取引所が開く前に算出する．
    context.output = pipeline_output('my_pipeline')
    # pandas dataframe 
    context.security_list = context.output.sort_values(by = "abs_raw_weights", ascending=False).head()
    
def compute_weights(context, data):
    ## normalized_weightsを算出
    context.security_list["normalize_weights"] = context.security_list["raw_weights"] / context.security_list["abs_raw_weights"].sum()
 
def rebalance(context, data):
    """
    rebalance: ポジション調整．
    
    """
    # Calculate our target weights.
    compute_weights(context, data)

    # Place orders for each of our securities.
    for security in context.security_list.index:
        if data.can_trade(security):
            # 現在の口座の金額に併せて，ポジションを調整してくる．
            # ここの説明は，スプレッドシートを使いたい．
            order_target_percent(security, context.security_list["raw_weights"][security])

def all_position_close(context, data): 
    for pos in context.portfolio.positions:
        if data.can_trade(pos):
            order_target_percent(pos, 0) 
        
    
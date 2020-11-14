"""
GUGDのバックテストその２　（その１は，58b78b2af6ee215f2a5dd1ab）
その１にEarningデータも入れる．
参考　Earnings drift with Estimize - https://www.quantopian.com/posts/earnings-drift-with-estimize

update_universe 
    + 出来高過去平均トップ５００
    + 前日終値から当日始値のDiffが大きいものをそれぞれ１０銘柄
rebalance 
    + GUしたものは，Open５分後にショート
    + GDしたものは，Open５分後にロング
    + ウェイトは銘柄分の１
logging 
    + 銘柄，株数，購入額
    + PLはFullBacktestで確認するのでログには出さない

参考
https://www.quantopian.com/posts/newbie-question-pipe-dot-set-screen-typererror
https://www.quantopian.com/posts/ranked-universe-and-long-short-equity-strategy
"""

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume,RSI
from quantopian.pipeline.filters.morningstar import Q1500US
import pandas as pd
   
    
class Gap(CustomFactor):
    inputs = [USEquityPricing.open, USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, open_price, close):
        out[:] = open_price[-1] / close[-2] - 1 
        
class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]

        
def initialize(context):
    context.gapdowns = []
    context.gapups = []
    
    schedule_function(check_gdgu, date_rules.every_day(), time_rules.market_open())
    schedule_function(gugd_price_data, date_rules.every_day(), time_rules.market_open()) 
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(my_rebalance_close, date_rules.every_day(), time_rules.market_open(minutes=30)) 
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    attach_pipeline(make_pipeline(), 'pipe')

    
def make_pipeline():
    base_universe = Q1500US()
    yesterday_close = PrevClose()
    today_open = USEquityPricing.open
    dollar_volume = AverageDollarVolume(window_length=30)
    ## gap = today_open / yesterday_close - 1 では出来ない．
    ## TypeError: unsupported operand type(s) for /: 'BoundColumn' and 'BoundColumn'
    gap = Gap()
    rsi = RSI()#default window_length = 15
    rsi_under_60 = rsi < 60
    
    #ToDo この範囲を色々変えてみる．
    high_dollar_volume = dollar_volume.percentile_between(98, 100)
    pipe = Pipeline(
        columns = {
            'close': yesterday_close,
            'today_open': today_open.latest, 
            'dollar_volume': dollar_volume,
            'high_dollar_volume': high_dollar_volume, 
            'gap': gap, 
        },
        screen = base_universe & high_dollar_volume & rsi_under_60,
    )
    return pipe
 
def before_trading_start(context, data):
    context.cnt = 0 # handle data で開始30分だけdfにデータストアするための変数
    
    pass 

def check_gdgu(context, data):
    context.output = pipeline_output('pipe')
    context.security_list = context.output.index
    
    # GUGD sid_list
    context.gapdowns = context.output.sort_values(by='gap').head(5).index
    #context.gapups =  context.output.sort_values(by='gap').tail(5).index
    
def gugd_price_data(context, data):
    pass 
    # if context.gapups is not None:
    #     context.gapups_data = data.history(context.gapups, 
    #                                        fields="price", 
    #                                        bar_count=context.waiting_time, 
    #                                        frequency="1m")
    # if context.gapdowns is not None:
    #     context.gapdowns_data = data.history(context.gapdowns, 
    #                                          fields="price", 
    #                                          bar_count=context.waiting_time, 
    #                                          frequency="1m")
    #     print([s.symbol for s in context.gapdowns_data])
     
def my_assign_weights(price_data, sid):
    pass 
    # ## 
    # if price_data.describe().ix['std'][sid] < 0.1:
    #     print(sid.symbol,  price_data.describe().ix['std'][sid])
    #     return 1.0
    # else:
    #     return 0.0
 
def my_rebalance(context,data):
    cnt = len(context.gapdowns) + len(context.gapups)
    for sid in context.gapdowns:
        order_percent(sid, 1.0/cnt)
    for sid in context.gapups:
        order_percent(sid, -1.0/cnt)
        
def my_rebalance_close(context, data):
    for sid in context.gapdowns:
        order_percent(sid, 0)
    for sid in context.gapups:
        order_percent(sid, 0)
    
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

        

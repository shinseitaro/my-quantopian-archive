from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume,RSI,Returns
from quantopian.pipeline.filters.morningstar import Q1500US,Q500US
import pandas as pd
   
def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0:"Sun", 1:"Mon", 2:"Tue", 3:"Wed", 4:"Thu", 5:"Fri", 6:"Sat"}
    msgs = '\t%s\t%s:\t%s' % (dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)  
    log.info(msgs)
        
class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]
        
class PrevVolume(CustomFactor):
    inputs = [USEquityPricing.volume]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]
        
def initialize(context):
    context.gapdowns = []
    context.gapups = []

    context.sids = None 
    context.bar_count = 12
    context.turnover_threshold = 0.0
    context.gapup_threshold = 0.04
    
    schedule_function(find_gapup, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(close_orders, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    attach_pipeline(make_pipeline(), 'pipe')

def make_pipeline():
    base_universe = Q500US()
    yesterday_close = PrevClose()
    yesterday_volume = PrevVolume()
    dollar_volume = AverageDollarVolume(window_length=30)
    
    #ToDo この範囲を色々変えてみる．
    high_dollar_volume = dollar_volume.percentile_between(98, 100)
    pipe = Pipeline(
        
        columns = {
            'yesterday_close': yesterday_close,
            'yesterday_volume': yesterday_volume,
            'yesterday_turnover': yesterday_close * yesterday_volume,
            'dollar_volume': dollar_volume,
            'high_dollar_volume': high_dollar_volume, 
        },
        screen = base_universe & high_dollar_volume #& rsi_under_60
    )
    return pipe
 
def before_trading_start(context, data):
    context.cnt = 0 # handle data で開始30分だけdfにデータストアするための変数
    # 前日までのデータを pipeline から取得
    context.output = pipeline_output('pipe')
    context.sids = context.output.index
    logging([s.symbol for s in context.portfolio.positions])
    
    

def find_gapup(context, data): #results, date, turnover_threshold=0.05, gapdown_threshold = 0.0
    
    sids = context.output.index
    pan = data.history(sids,['price', 'volume'], 1, frequency='1m') 
    pan['turnover'] = pan.price * pan.volume

    df = pd.DataFrame({'gap': (pan.price.ix[0] / context.output.yesterday_close - 1),
                       'turnover': (pan.turnover.ix[0] / context.output.yesterday_turnover)})
    df = df.sort_values(by=['gap','turnover'], ascending=[True,False])
    df_gapups = df[(df.turnover > context.turnover_threshold) & (df.gap > context.gapup_threshold)]
    
    context.gapups = df_gapups.tail(5).index
    
    if context.gapups.any():
        logging(",".join([s.symbol for s in context.gapups]))
    return context.gapups 

     
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
    # for sid in context.gapdowns:
    #     logging("LONG: gapdown %s" % (sid.symbol))
    #     order_percent(sid, 1.0/cnt)
        
    for sid in context.gapups:
        logging("SHORT: gapup %s" % (sid.symbol))
        order_percent(sid, -1.0/cnt)

# def return_at_position_closed(context, data, sid):
    # df = data.history(sid, 
    #                   fields="price", 
    #                   bar_count=context.bar_count, 
    #                   frequency="1m")
    # return df[-1]/df[0]-1 

def return_at_short_position_closed(context, data, sid):
    df = data.history(sid, 
                      fields="price", 
                      bar_count=context.bar_count, 
                      frequency="1m")
    return df[0]/df[-1]-1 
    
def my_rebalance_close(context, data):
    # for sid in context.gapdowns:
    #     order_percent(sid, 0)
    #     logging("LONG position CLOSE: PL\t%s\t%s" % (sid.symbol, return_at_position_closed(context, data, sid)))

    for sid in context.gapups:
        order_percent(sid, 0)
        logging("SHORT position CLOSE: PL\t%s\t%s" % (sid.symbol, return_at_short_position_closed(context, data, sid)))

def close_orders(context,data):

    for sec in context.sids:  
        order_share = context.portfolio.positions[sec].amount  
        print("open order_share=",sec.symbol, " share=",order_share)

        if order_share > 0:  
            order_target(sec, 0)  
        elif order_share < 0:  
            order_target(sec,0)    

    #check all close order success  
    for sec in context.sids:  
        order_share = context.portfolio.positions[sec].amount  
        print("check order_share=",sec.symbol," share=",order_share)  
        
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    spy = data.history(sid(8554), fields='price',bar_count=context.bar_count, frequency='1m')
    record(spy_return=spy[-1]/spy[0]-1)
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

        

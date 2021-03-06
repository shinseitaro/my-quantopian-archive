from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume,RSI,Returns
from quantopian.pipeline.filters.morningstar import Q1500US
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
        
def make_pipeline():
    base_universe = Q1500US()
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

def initialize(context):
    context.bar_count = 62
    context.turnover_threshold = 0.03
    context.gapdown_threshold = -0.03
    
    schedule_function(find_gapdown, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(close_orders, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    attach_pipeline(make_pipeline(), 'pipe')
    
def before_trading_start(context, data):
    context.cnt = 0 
    # 前日までのデータを pipeline から取得
    context.output = pipeline_output('pipe')
    context.sids = context.output.index
    context.gapdowns = []
    context.gapups = []
    context.gapdown_ratio = None
    context.anyway_close = False 

def find_gapdown(context, data): #results, date, turnover_threshold=0.05, gapdown_threshold = 0.0
    
    sids = context.output.index
    pan = data.history(sids,['price', 'volume'], 1, frequency='1m') 
    pan['turnover'] = pan.price * pan.volume

    df = pd.DataFrame({'gap': (pan.price.ix[0] / context.output.yesterday_close - 1),
                       'turnover': (pan.turnover.ix[0] / context.output.yesterday_turnover)})
    
    df_gapdowns = df[(df.turnover > context.turnover_threshold) & (df.gap < context.gapdown_threshold)]    
    df_gapdowns = df_gapdowns.sort_values(by=['gap','turnover'], ascending=[True,False])
    
    context.gapdowns = df_gapdowns.head(5).index
    context.gapdown_ratio = df_gapdowns.head(5)['gap']
    
    if context.gapdowns.any():
        logging(",".join([s.symbol for s in context.gapdowns]))

     
def my_rebalance(context,data):
    cnt = len(context.gapdowns) + len(context.gapups)
    for sid in context.gapdowns:
        logging("LONG: gapdown %s" % (sid.symbol))
        order_percent(sid, 1.0/cnt)

def return_at_position_closed(context, data, sid):
    df = data.history(sid, 
                      fields="price", 
                      bar_count=context.bar_count, 
                      frequency="1m")
    return df[-1]/df[0]-1 

def close_orders(context,data):

    # for sec in context.gapdowns: 

    if context.portfolio.positions:
        print [s.symbol for s in context.portfolio.positions]        
        
        if context.anyway_close:
            for sec in context.gapdowns:  
                logging("LONG position LOSS CUT: PL\t%s\t%s" % (sec.symbol, return_at_position_closed(context, data, sec)))
                order_target(sec, 0)  
                
        for sec in context.gapdowns:
            print sec.symbol
            buy_price = context.portfolio.positions[sec].cost_basis
            current_price = context.portfolio.positions[sec].last_sale_price 
            if current_price >= buy_price * (1 + abs(context.gapdown_ratio.ix[sec])):
                logging("LONG position CLOSE: PL\t%s\t%s\tBuy@\t%s\tSell@\t%s" % (sec.symbol, return_at_position_closed(context, data, sec),buy_price,current_price))
                order_target(sec, 0)  
        
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
    if 10 < context.cnt and context.cnt < 61:
        close_orders(context,data)
    elif context.cnt == 61:
        context.anyway_close = True
        close_orders(context,data)
    else:
        pass 
    context.cnt += 1 
    
        

        

    
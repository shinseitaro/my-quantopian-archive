from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume,RSI,Returns
from quantopian.pipeline.filters.morningstar import Q1500US
import pandas as pd
import re 
from zipline.utils import tradingcalendar

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
    context.gapdown_threshold_upper = -0.00
    context.gapdown_threshold_lower = -0.05
    context.wincnt = 0
    context.losscnt = 0
    
    schedule_function(find_gapdown, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=1)) 
    schedule_function(all_open_position_close, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_open(minutes=context.bar_count)) 
    attach_pipeline(make_pipeline(), 'pipe')
    
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)    
    
def before_trading_start(context, data):
    context.cnt = 0 
    # 前日までのデータを pipeline から取得
    context.output = pipeline_output('pipe')
    context.sids = context.output.index
    context.gapdowns = []
    context.gapups = []
    context.gapdown_ratio = None
    context.anyway_close = False 
    context.vixcsv = data.current('vix', 'Close')
    
    # logging("Check if there is open positions %s" % [s.symbol for s in context.portfolio.positions])
   
    if context.wincnt > 0:
        x = context.wincnt*1.0/(context.wincnt + context.losscnt) 
        logging("Win Ratio %s" % x) 

def find_gapdown(context, data): #results, date, turnover_threshold=0.05, gapdown_threshold = 0.0
    
    sids = context.output.index
    pan = data.history(sids,['price', 'volume'], 1, frequency='1m') 
    pan['turnover'] = pan.price * pan.volume

    df = pd.DataFrame({'gap': (pan.price.ix[0] / context.output.yesterday_close - 1),
                       'turnover': (pan.turnover.ix[0] / context.output.yesterday_turnover)})
    
    df_gapdowns = df[(df.turnover > context.turnover_threshold) & (df.gap < context.gapdown_threshold_upper) & (df.gap >  context.gapdown_threshold_lower)]    
    df_gapdowns = df_gapdowns.sort_values(by=['gap','turnover'], ascending=[True,False])
    
    context.gapdowns = df_gapdowns.index
    # context.gapdown_ratio = df_gapdowns.head(10)['gap']
    
    # gaodowns 銘柄の昨日のパフォーマンスを確認
    if context.gapdowns.any():
        # 391 にすると前日の分足プラス今日の最初の一分が取れるので，最後の一分だけ外す
        df_yesterday = data.history(context.gapdowns,'price',391,frequency='1m') 
        dscr = df_yesterday[:-1].pct_change().dropna().describe() 
        context.gapdowns = dscr.loc[:, dscr.loc['mean'] > 0].T.index
        
        # context.gapdowns = dscr.loc[:, (dscr.loc['mean'] > 0)].T.sort_values(by='std', ascending=False).head().index

        if context.gapdowns.any():
            context.gapdown_ratio = df_gapdowns.ix[context.gapdowns]['gap']

        else:
            context.gapups = []
            context.gapdown_ratio = None
    
    # if context.gapdowns.any():
    #     logging(",".join([s.symbol for s in context.gapdowns]))

     
def my_rebalance(context,data):
    cnt = len(context.gapdowns) + len(context.gapups)
    if cnt > 0:
        for sid in context.gapdowns:
            # logging("LONG: gapdown %s" % (sid.symbol))
            order_percent(sid, 0.99/cnt)

def return_at_position_closed(context, data, sid):
    df = data.history(sid, 
                      fields="price", 
                      bar_count=context.cnt, 
                      frequency="1m")
    return df[-1]/df[0]-1 

def close_orders(context,data):

    # for sec in context.gapdowns: 

    if context.portfolio.positions:
        for sec in context.portfolio.positions:
            buy_price = context.portfolio.positions[sec].cost_basis
            current_price = context.portfolio.positions[sec].last_sale_price 
            
            if current_price > buy_price * (1 + abs(context.gapdown_ratio.ix[sec])):
                logging("LONG position PL:\t%s\t%s\tBuy@\t%s\tSell@\t%s\tGD\t%s\tVIX\t%s" % 
                        (sec.symbol, return_at_position_closed(context, data, sec),buy_price,current_price,context.gapdown_ratio.ix[sec],context.vixcsv))
                order_target(sec, 0)  
                context.wincnt += 1
                
def all_open_position_close(context,data):
    if context.portfolio.positions:
        for sec in context.portfolio.positions:  
            buy_price = context.portfolio.positions[sec].cost_basis
            current_price = context.portfolio.positions[sec].last_sale_price 
            
            logging("LONG position LOSSCUT:\t%s\t%s\tBuy@\t%s\tSell@\t%s\tGD\t%s\tVIX\t%s" % 
                        (sec.symbol, return_at_position_closed(context, data, sec),buy_price,current_price,context.gapdown_ratio.ix[sec],context.vixcsv))
            order_target(sec, 0)  
            if current_price > buy_price:
                context.wincnt += 1
            else:
                context.losscnt += 1
                
        
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
    # if 3 < context.cnt and context.cnt < 61:
    #     close_orders(context,data)
    # else:
    #     pass 
    context.cnt += 1 
    

def addFieldsVIX(df):
    #df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'VIX Close')
    return df
    
def next_trading_day(dt):
    tdays = tradingcalendar.trading_days
    normalized_dt = tradingcalendar.canonicalize_datetime(dt)
    idx = tdays.searchsorted(normalized_dt)
    return tdays[idx + 1]

def reformat_quandl(df,closeField):
    df = df.rename(columns={closeField:'Close'})
    dates = df.Date.apply(lambda dt: pd.Timestamp(re.sub('\*','',dt), tz='US/Eastern'))
    df['Date'] = dates.apply(next_trading_day)
    df = df.sort(columns='Date', ascending=True)
    df.index = range(df.shape[0])
    return df
    
        
        

        

    
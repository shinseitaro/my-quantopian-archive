"""
XIV(2049)/VXX(1552)ストラテジーバックテスト【2016年7月まで版】 - room5110 - https://room5110.com/vix/backtest201607#XIV2049_VXX1552-2
vix は csv から取得

+ VX1 / VIX -1 > 0, Vol Short
+ VX1 / VIX -1 < 0, Vol Long
"""
import pandas as pd
import re 
from zipline.utils import tradingcalendar
from quantopian.algorithm import calendars

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    msgs = '\t%s\t%s:\t%s'%(dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)
    log.info(msgs)
    
def initialize(context):
    context.vxx = sid(38054)
    context.xiv = sid(40516)
    context.vx1 = continuous_future('VX', offset=0, roll='volume', adjustment='mul')
    context.premium = None 
    context.vixcsv = None
    context.currently_long_vol = False
    context.currently_short_vol = False
    context.thred = 0.05

    schedule_function(rebalance,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)

    schedule_function(record_contango, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(),
                      calendar = calendars.US_EQUITIES)
    
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)
    logging('SYMBOL\tLATEST PRICE\tAVERAGE PRICE\tAMOUNT\tPL\tPREMIUM\tVIX')
    
def before_trading_start(context, data):
    
    symbol = None 
    
    if context.currently_long_vol:
        symbol = context.vxx
    elif context.currently_short_vol:
        symbol = context.xiv 
    if symbol:
        posi = context.portfolio.positions[symbol]
        ticker = posi.sid
        
        amount = posi.amount
        latest = posi.last_sale_price
        boughtat = posi.cost_basis
        pl = latest / boughtat - 1
        
        fotmatter = '{0}\t{1: .1f}\t{2: .5f}\t{3: .5f}\t{4: .5f}\t{5: .5f}\t{6: .5f}'
        logging(fotmatter.format(ticker, 
                                 latest,               
                                 boughtat,
                                 amount,
                                 pl,
                                context.premium,
                                context.vixcsv))

def calc_premium(context, data):
    vx1_price = data.current(context.vx1, 'price')
    context.vixcsv = data.current('vix', 'Close')
    
    context.premium = vx1_price / context.vixcsv - 1 
    return context.premium

def rebalance(context, data):
    calc_premium(context,data)

    # close position
    if context.premium > context.thred and context.currently_long_vol:
        order_percent(context.vxx, 0) 
        context.currently_long_vol = False

    elif context.premium < -context.thred and context.currently_short_vol:
        order_percent(context.xiv, 0) 
        context.currently_short_vol = False
        
    elif (-context.thred < context.premium) and (context.premium < context.thred) and ( context.currently_long_vol or context.currently_short_vol):
        order_percent(context.xiv, 0) 
        order_percent(context.vxx, 0) 
        context.currently_short_vol = False
        context.currently_long_vol = False

    # open position 
    if context.premium > context.thred and (not context.currently_short_vol) and data.can_trade(context.xiv):
        order_percent(context.xiv, 0.9) 
        context.currently_short_vol = True 

    elif context.premium < -context.thred and (not context.currently_long_vol) and data.can_trade(context.vxx):
        order_percent(context.vxx, 0.9) 
        context.currently_long_vol = True 

def record_contango(context, data):
    record(premium=context.premium)
    
def addFieldsVIX(df):
    #df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'VIX Close')
    return df

def reformat_quandl(df,closeField):
    df = df.rename(columns={closeField:'Close'})
    dates = df.Date.apply(lambda dt: pd.Timestamp(re.sub('\*','',dt), tz='US/Eastern'))
    df['Date'] = dates.apply(next_trading_day)
    df = df.sort(columns='Date', ascending=True)
    df.index = range(df.shape[0])
    return df

def next_trading_day(dt):
    tdays = tradingcalendar.trading_days
    normalized_dt = tradingcalendar.canonicalize_datetime(dt)
    idx = tdays.searchsorted(normalized_dt)
    return tdays[idx + 1]
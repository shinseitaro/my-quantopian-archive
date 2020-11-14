
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Latest
from quantopian.pipeline.data.quandl import cboe_vix, cboe_vxv, yahoo_index_vix
from zipline.utils import tradingcalendar
import numpy as np
import pandas as pd
import re
vxvurl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxvdailyprices.csv'
vixurl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv'
class GetVix(CustomFactor):
    window_length=1
    def compute(self, today, assets, out, vix):
        out[:] = vix[-1]

def initialize(context):
    pipe = Pipeline()
    attach_pipeline(pipe, 'vix_pipeline')
    close = Latest(inputs=[USEquityPricing.close], window_length=1)
    pipe.add(close, 'Close')
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.ivts = []
    context.vxx_weight = 0.0
    context.vxz_weight = 0.0
    fetch_csv(vxvurl,symbol='vxv', skiprows=2, date_column='Date', pre_func=addFieldsVXV)
    fetch_csv(vixurl,symbol='vix',skiprows=1,date_column='Date',pre_func=addFieldsVIX)
    schedule_function(ordering_logic, date_rule=date_rules.every_day(), time_rule=time_rules.market_close())

def before_trading_start(context, data):
    context.vixpipe = pipeline_output('vix_pipeline') # pipeline_output は pd.DataFrame を返す
    #context.vxv = data.current('vxv', 'Close')
    #context.vix = data.current('vix', 'Close')
    #log.info('context.vix' % context.vix)
   
def handle_data(context, data):
    pass 
    
def ordering_logic(context, data,):
    vix = data.current('vxv', 'Close')# context.vixpipe.loc[context.vxx]['vix']
    vxv = data.current('vix', 'Close')# context.vixpipe.loc[context.vxx]['vxv']
    # その日の implied vol term structure 1month / 3month 
    ivts = vix / vxv 
    context.ivts.append(ivts)
    record(ivts=ivts)
    
    if ivts <= 0.91:
        (vxx_weight, vxz_weight) = (-0.6, 0.4)
    elif 0.91 < ivts <= 0.97:
        (vxx_weight, vxz_weight) = (-0.32, 0.68)
    elif 0.97 < ivts <= 1.05:
        (vxx_weight, vxz_weight) = (-0.25, 0.75)
    else:
        (vxx_weight, vxz_weight) = (-0.1, 0.9)

    log.info('vxx_weight: %s, vxz_weight: %s, ivts: %s' % (vxx_weight, vxz_weight, ivts))   
    # weight が　前回とちがうのであれば一旦closeする        
    if context.vxx_weight == context.vxz_weight == 0:
        log.info('This is first trade.')
        rebalance(context.vxx_weight,  context.vxz_weight,context, data)
        
    if (vxx_weight == context.vxx_weight) & (vxz_weight == context.vxz_weight):
        log.info('Hold current position since No change in weights')
    elif False in [data.can_trade(context.vxx), data.can_trade(context.vxz)]:
        log.info('Hold current position since both or one of vxx/vxz can not trade')       
    else:
        price = context.portfolio.positions[context.vxx].last_sale_price
        amount = context.portfolio.positions[context.vxx].amount
        orderid = order_value(context.vxx, 0)
        log.info('Closed %s %s shares @ %s' % (context.vxx.symbol, amount, price))

        price = context.portfolio.positions[context.vxz].last_sale_price
        amount = context.portfolio.positions[context.vxz].amount        
        orderid = order_value(context.vxz, 0)
        log.info('Closed %s %s shars @ %s' % (context.vxz.symbol, amount, price))
        
        # クローズ後に新しいウェイト分オーダーする．
        rebalance(context.vxx_weight,  context.vxz_weight,context, data)

    # update weight 
    context.vxx_weight = vxx_weight 
    context.vxz_weight = vxz_weight
        

def rebalance(vxx_weight, vxz_weight, context, data):
    vxx_current_value = context.portfolio.positions[context.vxx].last_sale_price
    vxz_current_value = context.portfolio.positions[context.vxz].last_sale_price
    
    if data.can_trade(context.vxx) & data.can_trade(context.vxz):
        vxx_order_value = context.portfolio.portfolio_value * vxx_weight
        vxz_order_value = context.portfolio.portfolio_value * vxz_weight
        
        if (abs(vxx_order_value) > vxx_current_value) & (vxz_order_value > vxz_current_value): 
            log.info('VXX Short @ %s ' % vxx_current_value) 
            order_id = order_value(context.vxx, vxx_order_value)
            log.info('VXZ Long @ %s ' % vxz_current_value) 
            order_id = order_value(context.vxz, vxz_order_value)
           
    else:
        log.info('No change in position')
    
def reformat_quandl(df,closeField):
    df = df.rename(columns={closeField:'Close'})
    df['Date'] = df.Date.apply(lambda dt: pd.Timestamp(re.sub('\*','',dt), tz='US/Eastern'))
    df = df.sort(columns='Date', ascending=True)
    df.index = range(df.shape[0])
    return df

def shift_quandl(df):
    tdays = tradingcalendar.trading_days
    last_bar = df.iloc[-1].copy()
    last_date = pd.to_datetime(last_bar['Date'])
    last_dt = tradingcalendar.canonicalize_datetime(last_date)
    next_dt = tdays[tdays.searchsorted(last_dt) + 1]
    last_bar['Date'] = next_dt
    last_bar.name = df.index[-1] + 1
    df = df.append(last_bar)
    return df

def addFieldsVIX(df):
    df=reformat_quandl(df,'VIX Close')
    df=shift_quandl(df)
    log.info(df.head())
    log.info(df.tail())
    return df

def addFieldsVXST(df):
    df=reformat_quandl(df,'Close')
    df=shift_quandl(df)
    return df

def addFieldsVXV(df):
    df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df=reformat_quandl(df,'CLOSE')
    df=shift_quandl(df)
    return df
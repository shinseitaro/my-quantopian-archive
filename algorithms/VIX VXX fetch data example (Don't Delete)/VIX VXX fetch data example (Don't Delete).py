"""
VIX （１ヶ月）と VXV（３ヶ月） のコンタンゴ率でVXXとVXZをShort Longするストラテジー
注意！
VIX VXX といった　VIX index データは， quantopian が用意している　
from quantopian.pipeline.data.quandl import cboe_vix, cboe_vxv, yahoo_index_vix
をつかうと，実際のデータとは一致しないという事が確認されてている
https://www.quantopian.com/posts/vix-slash-vxv-pipeline-data-critical-issue-closing-prices-incorrect-help
なので，ここで紹介されているように，fetch_csv を使って cboe からデータを取得する
""" 
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import CustomFactor, Latest
from quantopian.pipeline.data.quandl import cboe_vix, cboe_vxv, yahoo_index_vix
from zipline.utils import tradingcalendar
import numpy as np
import pandas as pd
import re

class GetVIX(CustomFactor):
    # 一日分のVIXデータを取得するカスタムファクター
    window_length = 1
    def compute(self, today, assets, out, vix):
        out[:] = vix[-1]
        
def initialize(context):
    pipe = Pipeline()
    attach_pipeline(pipe, 'my_pipeline')
    close = Latest(inputs=[USEquityPricing.close], window_length=1)
    pipe.add(close, 'Close')
    
    # cboe_vix, yahoo_index_vix　でどれだけデータが違っているか，確認してみる
    pipe.add(GetVIX(inputs=[cboe_vix.vix_close]), 'QuandleVIXClose')
    pipe.add(GetVIX(inputs=[cboe_vxv.close]), 'QuandleVXVClose')
    context.vxx = sid(38054) ## これは，日付index用につかう　（下記の”⇐ここ”のところ）
    
    # fetch_csv したデータは， pd.DataFrame になり， symbol= でつけた名前で， data.current('symbol名', 'ファイル内のコラム') でアクセスできる
    # 参照 https://www.quantopian.com/help#overview-fetcher 
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxvdailyprices.csv',  
              symbol='vxv', 
              skiprows=2, 
              date_column='Date', 
              pre_func=addFieldsVXV)
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)
    
    schedule_function(outputlog, date_rules.every_day(), time_rules.market_open(minutes=5))
    
def before_trading_start(context, data):
    ## パイプラインにadd したデータと， fetch_csvでフェッチしたデータの取り込み方の違いも確認！！
    context.output = pipeline_output('my_pipeline')# pipeline_output は pandas.DataFrame を返す
    context.vix = context.output['QuandleVIXClose'].loc[context.vxx] # ⇐ここ
    context.vxv = context.output['QuandleVXVClose'].loc[context.vxx] # ⇐ここ
    context.vixcsv = data.current('vix', 'Close')
    context.vxvcsv = data.current('vxv', 'Close')
    
    
def outputlog(context, data):
    # log.info(' vix %s vixcsv %s' % (format(context.vix, '.2f'), format(context.vixcsv, '.2f')))
    # log.info(' vxv %s vxvcsv %s' % (format(context.vxv, '.2f'), format(context.vxvcsv, '.2f')))
    if abs(context.vix - context.vixcsv) > 0.01:
        record(vix_diff = 1)
        log.info(' vix %s vixcsv %s' % (format(context.vix, '.2f'), format(context.vixcsv, '.2f')))
    else:
        record(vix_diff = 0)
    if abs(context.vxv - context.vxvcsv) > 0.01:        
        record(vxv_diff = -1)
        log.info(' vxv %s vxvcsv %s' % (format(context.vxv, '.2f'), format(context.vxvcsv, '.2f')))
    else:
        record(vxv_diff = 0)
        
    
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

def addFieldsVXV(df):
    df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'CLOSE')
    return df

def addFieldsVIX(df):
    #df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df,'VIX Close')
    return df
    
                 
        
        
    
    
    
    
    
    
    
    
    


























from __future__ import division
from quantopian.algorithm import attach_pipeline, pipeline_output, calendars
from quantopian.pipeline import Pipeline, CustomFactor, CustomFilter
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
from quantopian.pipeline.filters import StaticSids
#
import numpy as np
import pandas as pd


TIME_ZONE = 'US/Eastern'
DAY_NAME_DIC = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
#PIPE_NAME = 'pipe'

VOLATILITY_LOOK_BACK_DAYS = 60
VOLATILITY_WINDOW_DAYS = 11
ADJUSTMENT_FACTOR = 0.9
MOMENTUM_LOOK_BACK_DAYS = 40
DAYS_PER_YEAR = 250
FEV_THRESHOLD = 0.25 
MOMENTUM_THRESHOLD = 0.02
CONTANGO_MIN_THRESHOLD = 0 #1.00
CONTANGO_MAX_THRESHOLD = 2 #1.15

THRESHOLD = 0.00
UTILIZATION = 0.95
TVIX_MULTIPLIER = 1.25

# Logging
def logging(msgs):
    now = get_datetime(TIME_ZONE)
    msgs = '\t{0}\t{1}:\t{2}'.format(now.strftime('%Y-%m-%d %H:%M'), DAY_NAME_DIC[now.weekday()], msgs)
    log.info(msgs)
    

def get_TE(l, h, c, adf, t, sqrt_year):
    def func(h, l, last_close, adf, sqrt_year):
        return np.max((np.abs(np.log(h / last_close)),
                       np.abs(np.log(l / last_close)))) * sqrt_year * adf

    h, l, c = h[1:], l[1:], c[:-1]
    te = np.vectorize(func)(h, l, c, adf, sqrt_year)
    for i in range(1, len(te)):
        te[i] =  te[i] * 2 / t + te[i - 1] * (1 - 2 / t)
    te[:t + 1] = np.nan
    return te


def calc_fev(context, data):
    l = data.history(context.spy, 'low', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    h = data.history(context.spy, 'high', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    c = data.history(context.spy, 'close', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    te = get_TE(l, h, c, ADJUSTMENT_FACTOR, VOLATILITY_WINDOW_DAYS, np.sqrt(DAYS_PER_YEAR))
    te = pd.Series(te)
    return te


def calc_momentum(context, data, te, days):
    return te.rolling(days, min_periods=1).mean().pct_change().iloc[-1]


def calc_contango(context, data):
    context.contango = data.current('v2','Settle')/data.current('v1','Settle')
    return context.contango


def rename_col(df):
    df = df.rename(columns={'Close': 'price','Trade Date': 'Date'})
    df = df.fillna(method='ffill')
    df = df[['price', 'Settle','sid']]
    # Shifting data by one day to avoid forward-looking bias
    return df.shift(1)


def initialize(context):
    context.contango = None
    #
    context.spy = sid(8554)
    context.vxx = sid(38054)
    context.xiv =  sid(49077)# xiv
    context.tvix = sid(49076)
    context.sids = [context.vxx, context.xiv, context.tvix]
    context.price_records = dict([(x, None) for x in context.sids])
    # Front month VIX futures data
    fetch_csv('http://www.quandl.com/api/v1/datasets/CHRIS/CBOE_VX1.csv', 
        date_column='Trade Date', 
        date_format='%Y-%m-%d',
        symbol='v1',
        post_func=rename_col)
    # Second month VIX futures data
    fetch_csv('http://www.quandl.com/api/v1/datasets/CHRIS/CBOE_VX2.csv', 
        date_column='Trade Date', 
        date_format='%Y-%m-%d',
        symbol='v2',
        post_func=rename_col)
    schedule_function(rebalance, 
                      date_rules.week_end(), 
                      time_rules.market_close(minutes=1),
                      calendar=calendars.US_EQUITIES)

 
def rebalance(context, data):
    df_entry = data.history(context.sids, 'price', 1, '1m')
    logging(df_entry[context.vxx])
    context.price_records = add_price_records(context, df_entry) 
    #
    contango = calc_contango(context, data)
    fev = calc_fev(context, data)
    momentum_fev = calc_momentum(context, data, fev, MOMENTUM_LOOK_BACK_DAYS)
    record(third_eye_fev=fev.iloc[-1], 
           momentum_fev=momentum_fev*10, 
           contango=contango-1.0,
           )
    if not (data.can_trade(context.xiv) and data.can_trade(context.tvix)):
        return
    cvxx = context.price_records[context.vxx]
    cxiv = context.price_records[context.xiv]
    ctvix = context.price_records[context.tvix]
    cvxx_p = cvxx['entry_price'].pct_change() # > 0.01
    ctvix_p = ctvix['entry_price'].pct_change()
    diff = ctvix['entry_price'].pct_change()+cxiv['entry_price'].pct_change()*2
    if len(ctvix_p) > 2 and \
        abs(cvxx_p.tail(1).ix[0]) > THRESHOLD and \
        abs(ctvix_p.tail(1).ix[0]) > THRESHOLD:
        #if contango > CONTANGO_THRESHOLD and 
        d = -1 #if fev.iloc[-1] < FEV_THRESHOLD and momentum_fev < MOMENTUM_THRESHOLD and contango > CONTANGO_MIN_THRESHOLD and contango < CONTANGO_MAX_THRESHOLD else 0 
        order_target_percent(context.xiv, d*UTILIZATION*1.0)
        order_target_percent(context.tvix, d*UTILIZATION*TVIX_MULTIPLIER*1.0)
    else:
        order_target_percent(context.xiv, 0)
        order_target_percent(context.tvix, 0)
    return


def add_price_records(context, df_entry):
    d = context.price_records
    for x in context.sids:
        df = pd.DataFrame([df_entry[x][0]],
                          index=df_entry.index, 
                          columns=['entry_price'])
        d[x] = d[x].append(df) if d[x] is not None else df
    return d



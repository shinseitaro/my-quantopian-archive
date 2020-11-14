from __future__ import division ## Python 3 系に実装されている Python 2 系 と互換性の無い機能をPython 2 系で使用できるようにする
import numpy as np
import pandas as pd

def get_TE(l, h, c, adf, t, sqrt_year):
    def func(h, l, last_close, adf, sqrt_year):
        return np.max((np.abs(np.log(h / last_close)),
                       np.abs(np.log(l / last_close)))) * sqrt_year * adf

    h, l, c = h[1:], l[1:], c[:-1]
    te = np.vectorize(func)(h, l, c, adf, sqrt_year) ## apply みたいなもの
    for i in range(1, len(te)):
        te[i] =  te[i] * 2 / t + te[i - 1] * (1 - 2 / t)
    te[:t + 1] = np.nan
    return te

def initialize(context):
    context.vxx = symbol('VXX')
    context.viix = symbol('VIIX')
    context.vixy = symbol('VIXY')
    context.vxz = symbol('VXZ')
    context.viiz = symbol('VIIZ')
    context.vixm = symbol('VIXM')
    context.spy = symbol('SPY')
    context.etns = [context.vxx, context.viix, context.vixy,
                    context.vxz, context.viiz, context.vixm]

    
    context.sqrt_year = np.sqrt(250)
    schedule_function(rebalance,
                      date_rules.week_start(),
                      time_rules.market_open())
    schedule_function(close_positions,
                      date_rules.every_day(),
                      time_rules.market_open())
    
def rebalance(context, data):
    l = data.history(context.spy, 'low', 60, '1d')[:-1]
    h = data.history(context.spy, 'high', 60, '1d')[:-1]
    c = data.history(context.spy, 'close', 60, '1d')[:-1]
    te = get_TE(l, h, c, 0.9, 11, context.sqrt_year)
    te = pd.Series(te)
    
    can_trade_count = np.sum([data.can_trade(x) for x in context.etns])
    
    open_price = [data.current(x, 'price') for x in context.etns]
    price_mean = np.mean(open_price) * 0.01
    
    momentum = te.rolling(40).mean().pct_change().iloc[-1] * 10
    record(third_eye=te.iloc[-1], momentum=momentum, price=price_mean)
    if can_trade_count == 6 and momentum < 0:
        for x in context.etns:
            order_target_percent(x, -0.15)
    elif can_trade_count == 6 and momentum >= 0:
        for x in context.etns:
            order_target_percent(x, 0)

def close_positions(context, data):
    l = data.history(context.spy, 'low', 60, '1d')[:-1]
    h = data.history(context.spy, 'high', 60, '1d')[:-1]
    c = data.history(context.spy, 'close', 60, '1d')[:-1]
    te = get_TE(l, h, c, 0.9, 11, context.sqrt_year)
    te = pd.Series(te)
    momentum = te.rolling(40).mean().pct_change().iloc[-1] * 10
    if momentum >= 0:
        for x in context.etns:
            order_target_percent(x, 0)
    else:
        etns_count = len(context.etns)
        can_trade_count = np.sum([data.can_trade(x) for x in context.etns])
        if can_trade_count == etns_count:
            for x in context.etns:
                order_target_percent(x, -1.0 / etns_count)
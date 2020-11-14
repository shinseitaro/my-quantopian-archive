## 2018/01/27 資料 "Ernie Chan's EWA/EWC pair trading" の書き直し

import numpy as np
import pandas as pd
from collections import deque

def initialize(context):
    context.window_length = 28 
    context.stocks = [sid(14516), sid(14517)]
    
    context.evec = [0.943, -0.822] #<=?
    context.unit_shares = 10000 #<=?
    
    schedule_function(process_data_and_order, date_rules.every_day(), time_rules.market_open())

    
def process_data_and_order(context, data):
    context.prices = data.history(context.stocks, fields="price", bar_count=context.window_length, frequency='1d')
    df_evec_prices = context.prices * context.evec
    meanPrice = np.mean(df_evec_prices.values)
    stdPrice = np.std(df_evec_prices.values)
    comb_price = sum(data.current(context.stocks, 'price') * context.evec)
    
    h = (comb_price - meanPrice) / stdPrice
    
    order_target_percent(context.stocks[0], 0.5 * -h * context.evec[0])
    order_target_percent(context.stocks[1], 0.5 * -h * context.evec[1])
## "Euan Sinclair's VXX/VXZ Strategy" のコピペ勉強

import datetime
import pytz
import pandas as pd 
import re

# from zipline.utils.tradingcalendar import get_early_closes # to detect if the market will close early
from zipline.utils import tradingcalendar

# 理由は知らんが，Quantopianでは指数データは提供されていない．SP500もない．
vixUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv'
vxstUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxstcurrent.csv'
vxvUrl = 'http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vxvdailyprices.csv'

# XIV benchmark
set_benchmark(sid(40516))

def initialize(context):
    # ポートフォリオの中身
    context.vxx = {sid(38054): 1.0}
    context.vxz = {sid(38055): 1.0}
    context.spy = sid(8554)
    
    fetch_csv(vixUrl, symbol='VIX', skiprows=1, date_column='Date', pre_func=addFieldVIX)
    fetch_csv(vxstUrl, symbol='VXST', skiprows=3, date_column='Date', pre_func=addFieldVXST)
    fetch_csv(vxvUrl, symbol='VXV', skiprows=2, date_column='Date', pre_func=addFieldVXV)
    
    start_date = context.spy.security_start_date
    end_date = context.spy.security_end_date
    
    # コストはとりあえず０
    set_slippage(slippage.FixedSlippage(spread=0.00))
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=None))
    
    # detect if the market will close early
    context.early_closes = tradingcalendar.get_early_closes(start_date, end_date).date
    context.slopes = pd.Series()
    context.vixprices = pd.Series()
    context.vivprices = pd.Series()
    
    schedule_function(func=ordering_logic,
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open(minutes=5))

def handle_data(context, data):
    pass

def factors(slopes, vixprice, vxvprice):
    vxxfactor = 0.0
    vxzfactor = 0.0
    if (len(slopes) >= 7):
        lastweek = slopes.iloc[-7]
        today = slopes.iloc[-2]
        if (today > 1.05):
            vxxfactor = -0.1
            vxzfactor = 0.9
        elif (today > 0.97):
            vxxfactor = -0.25
            vxzfactor = 0.75
        elif (today > 0.91):
            vxxfactor = -0.32
            vxzfactor = 0.68
        else:
            vxxfactor = -0.6
            vxzfactor = 0.4
    return (vxxfactor, vxzfactor) 

def ordering_logic(context, data):
    if 'Close' in data['VIX'] and 'Close' in data['VXV'] :
        vix = data['VIX']['Close']
        vxv = data['VXV']['Close']
        slope = (vix/vxv)
        record(slope=slope)
        
        exchange_time = pd.Timestamp(get_datetime()).tz_convert('US/Eastern')
        context.slopes = context.slopes.append(pd.Series(slope, index=[exchange_time]))
        context.vixprices = context.vixprices.append(pd.Series(vix, index=[exchange_time]))
        context.vxvprices = context.vxvprices.append(pd.Series(vxv, index=[exchange_time]))
        
        (vxxfactor, vxzfactor) = factors(context.slopes, context.vixprices, context.vxvprices)
        
        rebalance(context.vxx, data, vxxfactor)
        rebalance(context.vxz, data, vxzfactor)
        
        
def rebalance(sids, data, factor):
    for sid in sids:
        
        
            
            
            
    





























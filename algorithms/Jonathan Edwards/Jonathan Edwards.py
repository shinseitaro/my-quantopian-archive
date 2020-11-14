"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline,CustomFilter
from quantopian.pipeline.factors import CustomFactor, Latest
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters.morningstar import Q1500US

from zipline.utils import tradingcalendar
import numpy as np
import pandas as pd
import re


def initialize(context):
    context.symbols = symbols('TECS', 'TWM', 'TZA', 'YANG', 'DUST', 'DXD', 'FAZ', 'FXP', 'GASX',  'MIDZ', 'MZZ', 'QID', 'JDST', 'TVIX', 'BIS',  'UVXY', 'DGAZ', 'SOXS','RUSS', 'FAZ', 'MIDZ', 'SMDD', 'BZQ', 'DPK', 'SSG', 'ERY', 'DWT', 'SPXS', 'SCO', 'SRTY', 'TZA', 'SIJ', 'EDZ', 'DUG', 'SPXU', 'SMN', 'TECS', 'SKF', 'EEV', 'TWM', 'MZZ', 'SQQQ', 'SDP', 'SDOW', 'EPV', 'TTT', 'TMV', 'QID', 'EFU', 'EWV', 'SDS','TBT', 'DZZ', 'HDLV', 'EUO', 'TPS', 'TBZ',)
    context.symbols = symbols('DGAZ','TVIX','UVXY','DUST')
    context.sid_list = tuple([s.sid for s in context.symbols]) ##sid番号のtaple 必ずタプルでなくては行けない(37049, 47087, 47086, 45570, 40553, ．．．)
    attach_pipeline(make_pipeline(context), 'mypipe')
    context.df_long = pd.DataFrame()
    context.df_short = pd.DataFrame()    
    context.orders = list()
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open())

class SidInList(CustomFilter):
    """
    Filter returns True for any SID included in parameter tuple passed at creation.
    Usage: my_filter = SidInList(sid_list=(23911, 46631))
    """    
    inputs = []
    window_length = 1
    params = ('sid_list',)

    def compute(self, today, assets, out, sid_list):
        out[:] = np.in1d(assets, sid_list)
   
class RollingMax(CustomFactor):
    inputs = [USEquityPricing.high]
    def compute(self, today, asset_ids, out, values): 
        out[:] = np.nanmax(values,axis=0) 

class RollingMin(CustomFactor):
    inputs = [USEquityPricing.low]
    def compute(self, today, asset_ids, out, values): 
        out[:] = np.nanmin(values,axis=0) 
        
def make_pipeline(context):
    include_filter = SidInList(sid_list = context.sid_list )
    #base_universe = selection #Q1500US()
    yesterday_high = USEquityPricing.high.latest
    yesterday_low = USEquityPricing.low.latest
    
    rollingmax30 = RollingMax(window_length=30)
    rollingmin30 = RollingMin(window_length=30)
    is_max = rollingmax30.eq(yesterday_high)
    is_min = rollingmin30.eq(yesterday_low)
    
    pipe = Pipeline(
        screen = include_filter,
        columns = {
            'high': yesterday_high,
            'low':  yesterday_low,
            'rollingmax30': rollingmax30,
            'rollingmin30': rollingmin30,
            'is_max': is_max,
            'is_min': is_min,
        }
    )
    return pipe
 
def before_trading_start(context, data):
    context.longs = []
    context.shorts = []
    long_strategy(context, data)
    short_strategy(context, data)
    
def long_strategy(context, data):
    
    context.output = pipeline_output('mypipe')
    context.df_long = context.df_long.append(context.output['is_max'].T)
    threedays = context.df_long.tail(3).sum(axis=0)
    context.longs = [s for s in threedays.index if threedays[s] == 3]

def short_strategy(context, data):
    
    context.output = pipeline_output('mypipe')
    context.df_short = context.df_short.append(context.output['is_min'].T)
    threedays = context.df_short.tail(3).sum(axis=0)
    context.shorts = [s for s in threedays.index if threedays[s] == 3]
    
    
def my_rebalance(context,data):
    """
    Execute orders according to our schedule_function() timing. 
    """
    for s in context.longs:
        posi = context.portfolio.positions[s]
        if data.can_trade(s) and posi.amount == 0:
            print("OPEN LONG POSITION", s.symbol)
            order_target_percent(s, 1.0 / len(context.sid_list))

    for s in context.shorts:
        posi = context.portfolio.positions[s]
        if data.can_trade(s) and posi.amount == 0:
            print("OPEN SHORT POSITION", s.symbol)            
            order_target_percent(s, 1.0 / len(context.sid_list) * -1)

    my_rebalance_for_exit(context,data)
    
def my_rebalance_for_exit(context,data):                
    for s in context.portfolio.positions:
        posi = context.portfolio.positions[s]
        if data.can_trade(s) and posi.amount > 0: # long posion
            if (data.current(s, 'price') / posi.cost_basis - 1 > 0.05):# or (data.current(s, 'price') / posi.cost_basis - 1 < -0.025):
                print("LONG POSITION CLOSE:", s.symbol)
                order_target_percent(s, 0)
                
        if data.can_trade(s) and posi.amount < 0: # short posion
            if (posi.cost_basis / data.current(s, 'price')  - 1 > 0.05):# or (posi.cost_basis / data.current(s, 'price')  - 1 < -0.025):
                print("SHORT POSITION CLOSE:", s.symbol)                
                order_target_percent(s, 0)
            
      
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass 
    # my_rebalance_for_exit(context,data)

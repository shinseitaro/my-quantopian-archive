"""
amzn / xlk 
closeでホールド
4日後のcloseでクローズ
indicator: 
"""


from quantopian.pipeline import Pipeline, CustomFilter
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.factors import Latest
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data.psychsignal import aggregated_twitter_withretweets_stocktwits as st
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.filters import Q500US,StaticSids
from zipline.utils.tradingcalendar import trading_day  
#
import numpy as np
import pandas as pd

  
TIME_ZONE = 'US/Eastern'
PIPELINE = 'Custom_pipeline'
#
MSG_RATIO = 'msg_ratio'
MSG_RATIO_INDICATOR = 'msg_ratio_indicator'
EXIT_DATE = 'exit_date'
ASSET = 'asset'
ETF = 'etf'
TOTAL_SCANNED_MESSAGES = 'total_scanned_messages'
THRESHOLD = 'threshold'
#
HOLDING_PERIOD = 4


def initialize(context): 
    #set_commission(commission.PerShare(cost=0.0, min_trade_cost=0.0))
    #context.securities_in_results = []
    
    ## sid and threshold list 
    context.conditions = [
        {ETF:sid(19658), ASSET:sid(16841), THRESHOLD:2, }, # XLK / AMZN
        {ETF:sid(19662), ASSET:sid(16841), THRESHOLD:2, }, # XLY / AMZN        
        {ETF:sid(19920), ASSET:sid(16841), THRESHOLD:-1, }, # QQQ / AMZN
        {ETF:sid(19658), ASSET:sid(24), THRESHOLD:3, }, #XLK / AAPL 
        {ETF:sid(19656), ASSET:sid(25006), THRESHOLD:-0.5, }, #XLF / JPM 
        {ETF:sid(28073), ASSET:sid(47169), THRESHOLD:-2.0, }, #XBI / KITE         
        {ETF:sid(28073), ASSET:sid(21383), THRESHOLD:-2.0, }, #XBI / EXEL     
    ]
    m = {MSG_RATIO: None, MSG_RATIO_INDICATOR: False, EXIT_DATE: None}
    for x in context.conditions:
        x.update(m)
    #
    attach_pipeline(Custom_pipeline(context), PIPELINE) 
    schedule_function(rebalance, date_rules.every_day(), time_rules.market_close())
    
    
def Custom_pipeline(context):
    pipe = Pipeline()
    static_sids = sum([[x[ETF], x[ASSET]] for x in context.conditions], [])
    my_sids =  StaticSids(static_sids)
    
    # sma_10 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=10)
    # sma_50 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=50)
    # pipe.add(st.bull_scored_messages .latest, 'bull_scored_messages')
    # pipe.add(st.bear_scored_messages .latest, 'bear_scored_messages')
    # pipe.add(st.bull_bear_msg_ratio .latest, 'bull_bear_msg_ratio')
    pipe.add(st.total_scanned_messages.latest, TOTAL_SCANNED_MESSAGES)
    pipe.set_screen(
        my_sids
        # & (sma_10 > sma_50)
        # & 0.35*st.bull_scored_messages.latest > st.bear_scored_messages.latest
        # & (st.bull_bear_msg_ratio.latest > 1.0 / 0.35)
        # & (st.bear_scored_messages.latest > 10)
    )   
    return pipe


def today():
    return get_datetime(TIME_ZONE).date()


def calc_message_ratio(pipe, x):
    am = pipe.ix[x[ASSET]][TOTAL_SCANNED_MESSAGES]
    em = pipe.ix[x[ETF]][TOTAL_SCANNED_MESSAGES]
    return np.log(am)-np.log(em)


def before_trading_start(context, data):
    results = pipeline_output(PIPELINE)
    for x in context.conditions:
        msg_ratio = calc_message_ratio(results, x)
        x[MSG_RATIO] = msg_ratio
        x[MSG_RATIO_INDICATOR] = msg_ratio < x[THRESHOLD]
        if x[MSG_RATIO_INDICATOR]:
            dr = pd.date_range(today(), freq=trading_day, periods=HOLDING_PERIOD)
            x[EXIT_DATE] = dr[-1].date()

        
def rebalance(context,data):
    positions = context.portfolio.positions
    candidates = [x for x in context.conditions 
                  if x[MSG_RATIO_INDICATOR] or x[EXIT_DATE]]
    for x in candidates:
        asset = x[ASSET]
        if data.can_trade(asset):
            if x[MSG_RATIO_INDICATOR] and not asset in positions:
                order_target_percent(asset, 0.9 * 1/len(candidates))    
            elif x[EXIT_DATE] == today() and asset in positions:
                order_target(asset, 0)
                x[EXIT_DATE] = None
'''
GUGDX#1 Archived
このアルゴリズムは，変更禁止です！！！！！！
'''

import math
import re
#
import pandas as pd
import numpy as np
#
from quantopian.algorithm import attach_pipeline, pipeline_output
#
from quantopian.pipeline import Pipeline, CustomFactor
#
from quantopian.pipeline.data import morningstar
from quantopian.pipeline.data.builtin import USEquityPricing
#
from quantopian.pipeline.factors import AverageDollarVolume, RSI, Returns, SimpleMovingAverage, AnnualizedVolatility
""
from quantopian.pipeline.filters import Q1500US, Q500US, StaticAssets, StaticSids
from quantopian.pipeline.filters.morningstar import IsPrimaryShare
#
from quantopian.pipeline.classifiers.morningstar import Sector, SuperSector
from quantopian.pipeline.data import morningstar as ms 

#
from zipline.utils import tradingcalendar


# Log
def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    msgs = '\t%s\t%s:\t%s'%(dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)
    log.info(msgs)


# close price of the last business day
class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2

    def compute(self, today, assets, out, close):
        out[:] = close[-2]


# trade volume of the last business day
class PrevVolume(CustomFactor):
    inputs = [USEquityPricing.volume]
    window_length = 2

    def compute(self, today, assets, out, close):
        out[:] = close[-2]

# # volatility of the last business day
# class PrevDailyVolatility(CustomFactor):
#     inputs = [USEquityPricing.close]
#     window_length = 20
#     def compute(self, today, assets, out, close):
#         # [0:-1] is needed to remove last close since diff is one element shorter
#         daily_returns = np.diff(close, axis = 0) / close[0:-1]
#         out[:] = daily_returns.std(axis = 0) #* math.sqrt(252)

# initialization
def initialize(context):
    ## context variables
    # symbol ids
    context.sids = None
    context.gapdowns = []
    context.gapups = []
    # trading conditions
    context.observe_timing = 0
    context.entry_timing = 1
    context.exit_timing = 40
    #
    context.gapup_min_turnover_ratio = 0.0
    context.gapup_max_turnover_ratio = 1.0
    context.gapup_min_gap = 0.05
    context.gapup_max_gap = 1.0
    context.gapup_min_rsi = 20
    context.gapup_max_rsi = 100
    context.gapup_min_zscore = -500
    context.gapup_max_zscore = 1000 #25
    context.gapup_lowerband = 10 #8
    context.gapup_num_trade = 10 #5
    #
    context.gapdown_min_turnover_ratio = 0.0
    context.gapdown_max_turnover_ratio = 0.5
    context.gapdown_min_gap = -0.12
    context.gapdown_max_gap = -0.05
    context.gapdown_min_rsi = 0
    context.gapdown_max_rsi = 80
    context.gapdown_min_zscore = -1.0
    context.gapdown_max_zscore = -2.5
    context.gapdown_lowerband = 8
    context.gapdown_num_trade = 5
    
    context.special_sids = [sid(47208), sid(39840)]
    context.static_asset = False 
    
    context.MORNINGSTAR_SECTOR_CODES = {  
        -1: 'Misc',  
        101: 'Basic Materials',  
        102: 'Consumer Cyclical',  
        103: 'Financial Services',  
        104: 'Real Estate',  
        205: 'Consumer Defensive',  
        206: 'Healthcare',  
        207: 'Utilities',  
        308: 'Communication Services',  
        309: 'Energy',  
        310: 'Industrials',  
        311: 'Technology' ,  }

    # schedule functions
    schedule_function(find_gapups, date_rules.every_day(), time_rules.market_open(minutes=context.entry_timing))
    #schedule_function(find_gapdowns, date_rules.every_day(), time_rules.market_open(minutes=context.entry_timing))
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=context.entry_timing))
    schedule_function(close_orders, date_rules.every_day(), time_rules.market_open(minutes=context.exit_timing))
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_open(minutes=context.exit_timing))
    # pipeline
    attach_pipeline(make_pipeline(context), 'pipe')

    # external data retrieval
    fetch_csv('http://www.cboe.com/publish/scheduledtask/mktdata/datahouse/vixcurrent.csv',
              symbol='vix',
              skiprows=1,
              date_column='Date',
              pre_func=addFieldsVIX)

    #: Set commissions and slippage to 0 to determine pure alpha
    # set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    # set_slippage(slippage.FixedSlippage(spread=0))


# pipeline
def make_pipeline(context):
    ## symbol universe
    base_universe = Q500US() if False else Q1500US()

    ## filters
    # Filter for primary share equities. IsPrimaryShare is a built-in filter.
    primary_share = IsPrimaryShare()
    # Equities listed as common stock (as opposed to, say, preferred stock).
    # 'ST00000001' indicates common stock.
    common_stock = morningstar.share_class_reference.security_type.latest.eq('ST00000001')
    # Non-depositary receipts. Recall that the ~ operator inverts filters,
    # turning Trues into Falses and vice versa
    not_depositary = ~morningstar.share_class_reference.is_depositary_receipt.latest
    # Equities not trading over-the-counter.
    not_otc = ~morningstar.share_class_reference.exchange_id.latest.startswith('OTC')
    # Not when-issued equities.
    not_wi = ~morningstar.share_class_reference.symbol.latest.endswith('.WI')
    # Equities without LP in their name, .matches does a match using a regular expression
    not_lp_name = ~morningstar.company_reference.standard_name.latest.matches('.* L[. ]?P.?$')
    # Equities with a null value in the limited_partnership Morningstar fundamental field.
    not_lp_balance_sheet = morningstar.balance_sheet.limited_partnership.latest.isnull()
    # Equities whose most recent Morningstar market cap is not null have fundamental data and therefore are not ETFs.
    have_market_cap = morningstar.valuation.market_cap.latest.notnull()
    is_cyclical = SuperSector().eq(SuperSector.CYCLICAL)
    is_defensive = SuperSector().eq(SuperSector.DEFENSIVE)
    is_sensitive = SuperSector().eq(SuperSector.SENSITIVE)

    # Filter for stocks that pass all of our previous filters.
    tradeable_stocks = (
        primary_share
        &common_stock
        &not_depositary
        &not_otc
        &not_wi
        &not_lp_name
        &not_lp_balance_sheet
        &have_market_cap
        #&(is_cyclical)
        #&(is_defensive)
        #&(is_sensitive)
        &(is_cyclical | is_defensive | is_sensitive)
    )

    # ToDo この範囲を色々変えてみる．
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = dollar_volume.percentile_between(98, 100)
    daily_volatility = AnnualizedVolatility(window_length=20)/math.sqrt(252)
    sme20 = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=20)
    rsi = RSI(inputs=[USEquityPricing.close])
    #sector = ms.asset_classification.morningstar_sector_code
    sector = Sector()
    static_sectors = (sector.eq(311) | 
                      sector.eq(309) | 
                      sector.eq(103) | 
                      sector.eq(101) | 
                      sector.eq(308) | 
                      sector.eq(206) )

    if context.static_asset:
        myscreen = StaticSids(context.special_sids) #context.special_assets
    else: 
        myscreen = (base_universe & tradeable_stocks & high_dollar_volume ) # & static_sectors
        

    pipe = Pipeline(
        columns={
            'prev_close': PrevClose(),
            'prev_volume': PrevVolume(),
            'prev_turnover': PrevClose()*PrevVolume(),
            'dollar_volume': dollar_volume,
            'high_dollar_volume': high_dollar_volume,
            'daily_volatility': daily_volatility,
            'sma20': sme20,
            'rsi': rsi,
            'morningstar_sector_code': sector,
        },
        screen=myscreen,
    )
    return pipe


def before_trading_start(context, data):
    # 前日までのデータを pipeline から取得
    context.output = pipeline_output('pipe')
    context.sids = context.output.index
    context.vix = data.current('vix', 'Close')


def calc_gap(context, data):
    co = context.output
    sids = co.index
    timing = context.observe_timing
    df_pan = data.history(sids, ['price', 'volume'], timing+1, frequency='1m')
    df_latest_price = df_pan.price.ix[timing]
    df_latest_turnover = df_latest_price*df_pan.volume.ix[timing]
    #
    df_eligibles = pd.DataFrame({
        'gap': df_latest_price/co.prev_close-1.0,
        'turnover_ratio': df_latest_turnover/co.prev_turnover,
        'rsi': co.rsi,
        'zscore': (df_latest_price-co.sma20)/co.daily_volatility,
    })
    return df_eligibles


def find_gapups(context, data):
    df_eligibles = calc_gap(context, data)
    df_gapups = df_eligibles[
        (df_eligibles.turnover_ratio > context.gapup_min_turnover_ratio)
        &(df_eligibles.turnover_ratio < context.gapup_max_turnover_ratio)
        &(df_eligibles.gap > context.gapup_min_gap)
        &(df_eligibles.gap < context.gapup_max_gap)
        #&(df_eligibles.rsi > context.gapup_min_rsi)
        #&(df_eligibles.rsi < context.gapup_max_rsi)
        #&(df_eligibles.zscore > context.gapup_min_zscore)
        #&(df_eligibles.zscore < context.gapup_max_zscore)
        ].sort_values(by=['gap'], ascending=[True])
    index_gapups = df_gapups.tail(context.gapup_lowerband).head(context.gapup_num_trade).index
    if len(index_gapups) > 0:
        assert df_gapups.ix[index_gapups[0]].gap <= df_gapups.ix[index_gapups[-1]].gap
    #return index_gapups
    context.gapups = index_gapups


def find_gapdowns(context, data):
    df_eligibles = calc_gap(context, data)
    df_gapdowns = df_eligibles[
        (df_eligibles.turnover_ratio > context.gapdown_min_turnover_ratio)
        &(df_eligibles.turnover_ratio < context.gapdown_max_turnover_ratio)
        &(df_eligibles.gap > context.gapdown_min_gap)
        &(df_eligibles.gap < context.gapdown_max_gap)
        #&(df_eligibles.rsi > context.gapdown_min_rsi)
        #&(df_eligibles.rsi < context.gapdown_max_rsi)
        #&(df_eligibles.zscore > context.gapdown_min_zscore)
        #&(df_eligibles.zscore < context.gapdown_max_zscore)
        ].sort_values(by=['gap'], ascending=[False])
    index_gapdowns = df_gapdowns.tail(context.gapdown_lowerband).head(context.gapdown_num_trade).index
    if len(index_gapdowns) > 0:
        assert df_gapdowns.ix[index_gapdowns[0]].gap >= df_gapdowns.ix[index_gapdowns[-1]].gap
    #return index_gapdowns
    context.gapdowns = index_gapdowns


def my_assign_weights(price_data, sid):
    pass
    #
    # if price_data.describe().ix['std'][sid] < 0.1:
    #     print(sid.symbol,  price_data.describe().ix['std'][sid])
    #     return 1.0
    # else:
    #     return 0.0


def my_rebalance(context, data):
    cnt = len(context.gapdowns)+len(context.gapups)
    for sid in context.gapdowns:
        #logging("LONG: gapdown %s" % (sid.symbol))
        order_percent(sid, 1.0/cnt)
    for sid in context.gapups:
        #logging("SHORT: gapup %s"%(sid.symbol))
        order_percent(sid, -1.0/cnt)

def get_prices(context, data, sid):
    s = data.history(sid, fields="price", bar_count=context.exit_timing+1, frequency="1m")
    yesterday_close = 0
    today_open = context.observe_timing+1
    entry = today_open+1 #+2
    exit = -1
    assert s.index[yesterday_close].minute == 0   
    assert s.index[today_open].minute == 31   
    assert s.index[entry].minute == 32  
    assert s.index[exit].minute == 10 # 10+60-30=40 
    close_price = s[yesterday_close]
    open_price = s[today_open]
    entry_price = s[entry]
    exit_price = s[exit]
    return close_price, open_price, entry_price, exit_price

def return_at_long_position_closed(context, data, sid):
    close_price, open_price, entry_price, exit_price = get_prices(context, data, sid)
    return open_price/close_price-1, exit_price/entry_price-1, close_price


def return_at_short_position_closed(context, data, sid):
    close_price, open_price, entry_price, exit_price = get_prices(context, data, sid)
    return open_price/close_price-1, entry_price/exit_price-1, close_price


# def my_rebalance_close(context, data):
#     for sid in context.gapdowns:
#         order_percent(sid, 0)
#         logging("LONG exit: \t{0}\t{1}".format(sid.symbol, return_at_long_position_closed(context, data, sid)))
#     for sid in context.gapups:
#         order_percent(sid, 0)
#         logging("SHORT exit: \t{0}\t{1}".format(sid.symbol, return_at_short_position_closed(context, data, sid)))


def close_orders(context, data):
    for sid in context.portfolio.positions:
        amount = context.portfolio.positions[sid].amount
        sector = context.MORNINGSTAR_SECTOR_CODES[context.output.morningstar_sector_code.ix[sid]]
        pipeline_close_price = context.output.prev_close.ix[sid]
        order_target(sid, 0)
        if amount > 0:
            side = 'Long exit'
            gap, pl, close_price = return_at_long_position_closed(context, data, sid)
        elif amount < 0:
            side = 'Short exit'
            gap, pl, close_price = return_at_short_position_closed(context, data, sid)
        logging("{0}\t{1}\t{2: .5f}\t{3: .5f}\t{4}\t{5: .5f}\t{6: .5f}".format(side, sid.symbol, gap, pl, sector, close_price, pipeline_close_price))
        
        
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    spy = data.history(sid(8554), fields='price', bar_count=context.exit_timing, frequency='1m')
    record(spy_return=spy[-1]/spy[0]-1)
    record(vix=context.vix)


def handle_data(context, data):
    """
    Called every minute.
    """
    pass


def addFieldsVIX(df):
    # df.rename(columns={'Unnamed: 0': 'Date'}, inplace=True)
    df = reformat_quandl(df, 'VIX Close')
    return df


def reformat_quandl(df, closeField):
    df = df.rename(columns={closeField: 'Close'})
    dates = df.Date.apply(lambda dt: pd.Timestamp(re.sub('\*', '', dt), tz='US/Eastern'))
    df['Date'] = dates.apply(next_trading_day)
    df = df.sort(columns='Date', ascending=True)
    df.index = range(df.shape[0])
    return df


def next_trading_day(dt):
    tdays = tradingcalendar.trading_days
    normalized_dt = tradingcalendar.canonicalize_datetime(dt)
    idx = tdays.searchsorted(normalized_dt)
    return tdays[idx+1]



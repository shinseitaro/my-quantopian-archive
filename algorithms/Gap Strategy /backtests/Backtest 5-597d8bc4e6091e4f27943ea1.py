from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import StaticSids, Q1500US, Q500US, StaticAssets
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.filters.morningstar import IsPrimaryShare
from quantopian.pipeline.classifiers.morningstar import Sector, SuperSector
from quantopian.pipeline.data import morningstar
from quantopian.pipeline.factors import AverageDollarVolume

import pandas as pd

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

def initialize(context):
    attach_pipeline(make_pipeline(context), 'pipe')
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
        
    schedule_function(find_gapups, date_rules.every_day(), time_rules.market_open())
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open())
    schedule_function(close_orders, date_rules.every_day(), time_rules.market_open(minutes=40))

def before_trading_start(context, data):
    context.df_eligibles = None 
    context.output = pipeline_output('pipe')
    

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
    
    sector = Sector()
    close = USEquityPricing.close

    # For filter
    tradeable_stocks = (
        primary_share
        &common_stock
        &not_depositary
        &not_otc
        &not_wi
        &not_lp_name
        &not_lp_balance_sheet
        &have_market_cap
        &(is_cyclical | is_defensive | is_sensitive))    
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = dollar_volume.percentile_between(98, 100)

    myscreen = (base_universe & tradeable_stocks & high_dollar_volume )    

    # Pipeline 
    pipe = Pipeline(
        columns = {'yesterday_close': close.latest ,
                   'day_before_yesterday_close':  PrevClose(),
                   'day_before_yesterday_volume':  PrevVolume(),
                   'morningstar_sector_code': sector,
                  },
        screen = myscreen)
    return pipe 

def calc_gap(context, data):
    """
    calcuration gap of overnight (last close to today's open) 
    """
    sids = context.output.index
    
    # calc indicators
    pan_data = data.history(sids, ['price', 'volume'], 1, frequency='1m')
    pan_data["turnover"] = pan_data['price'] * pan_data['volume'] 
    price_at_0930 = pd.Series(pan_data['price'].iloc[0], name="price_at_0930")
    turnover_at_0930 = pd.Series(pan_data['turnover'].iloc[0], name="turnover_at_0930")

    df_eligibles = pd.concat([context.output, price_at_0930, turnover_at_0930, ] , axis=1)
    df_eligibles['gap'] = df_eligibles["price_at_0930"] / df_eligibles["day_before_yesterday_close"] - 1 
    df_eligibles['turnover_ratio'] = df_eligibles["turnover_at_0930"] / df_eligibles["day_before_yesterday_volume"]
    return df_eligibles
   
    
def find_gapups(context, data):
    """
    find gapup sids 
    """
    context.df_eligibles = calc_gap(context, data)
    df_gapups = context.df_eligibles[
        (context.df_eligibles.gap > 0.05)
        & (context.df_eligibles.gap < 1.0)
        & (context.df_eligibles.turnover_ratio > 0.0)
        & (context.df_eligibles.turnover_ratio < 1.0)
        ].sort_values(by=['gap'], ascending=[True])
    # remove top and bottom 10 assets to avoid noise. (I should reconsider this threshold) 
    index_gapups = df_gapups.tail(10).head(10).index
    if len(index_gapups) > 0:
        assert df_gapups.ix[index_gapups[0]].gap <= df_gapups.ix[index_gapups[-1]].gap
    #return index_gapups
    context.gapups = index_gapups


def my_rebalance(context, data):
    cnt = len(context.gapups)
    for sid in context.gapups:
        order_percent(sid, -1.0/cnt)

# for logging
   
def get_prices(context, data, sid):
    # from yeasterday's last price to 10:10AM 
    data = data.history(sid, fields="price", bar_count=40, frequency="1m")
    open_price = data[0]
    entry_price = data[0]
    exit_price = data[-1]
    return entry_price, exit_price

def close_orders(context, data):
    """
    close all position at 10:10am everyday if I have. 
    """
    for sid in context.portfolio.positions:
        try:
            entry_price = context.portfolio.positions[sid].cost_basis
            sector = context.MORNINGSTAR_SECTOR_CODES[context.output.morningstar_sector_code.ix[sid]]
            day_before_yesterday_close = context.output["day_before_yesterday_close"].ix[sid]
            order_target(sid, 0)
            side = 'Short Position Exit'
            entry_price, exit_price = get_prices(context, data, sid)
            gap = context.df_eligibles.ix[sid, 'gap']
            pl = exit_price / entry_price - 1
            
            logging("{0}\t{1}\t{2: .5f}\t{3: .5f}\t{4}\t{5: .5f}\t{6: .5f}\t{7: .5f}".format(
                side, sid.symbol, gap, pl, sector, entry_price, exit_price, day_before_yesterday_close))
            
        except:
            print("Unexpected error:", sid)
            
            
        
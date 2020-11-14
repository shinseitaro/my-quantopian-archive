from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume,RSI
from quantopian.pipeline.filters.morningstar import Q1500US, Q500US

from quantopian.pipeline.data import morningstar
from quantopian.pipeline.classifiers.morningstar import Sector, SuperSector

from zipline import TradingAlgorithm  
from sklearn.ensemble import RandomForestRegressor

import pandas as pd
import numpy as np
import pytz
tz_ny = pytz.timezone("US/Eastern")


# Log
def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    msgs = '\t%s\t%s:\t%s'%(dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)
    log.info(msgs)


class FinancialFactor(CustomFactor):
    window_length = 2
    def compute(self, today, assets, out, v): 
        out[:] = v[0]
        
class MarketCap(FinancialFactor):
    inputs = [morningstar.valuation.market_cap]
    def compute(self, today, assets, out, v): 
        out[:] = np.log(v[0])
    
class ROA(FinancialFactor):
    inputs = [morningstar.operation_ratios.roa]
     
class ROE(FinancialFactor):
    inputs = [morningstar.operation_ratios.roe]

class NormalizedBasicEps(FinancialFactor):
    inputs = [morningstar.earnings_report.normalized_basic_eps]

class NetIncomeGrowth(FinancialFactor):
    inputs = [morningstar.operation_ratios.net_income_growth]

class PE(FinancialFactor):
    inputs = [morningstar.valuation_ratios.pe_ratio]

class BookValueYield(FinancialFactor):
    inputs = [morningstar.valuation_ratios.book_value_yield]

class DividendYield(FinancialFactor):
    inputs = [morningstar.valuation_ratios.dividend_yield]

class PeriodEndingDate(FinancialFactor):
    inputs = [morningstar.financial_statement_filing.period_ending_date]
    
def initialize(context):
    context.sids = None
    context.observe_timing = 0
    context.high_dollar_volume_thresh_min = 95
    context.high_dollar_volume_thresh_max = 100 
    context.spy = sid(8554)
    context.model = None 

    context.observe_timing = 1
    context.entry_timing = context.observe_timing + 1 
    context.exit_timing = 40
    
    schedule_function(trade, date_rules.every_day(), time_rules.market_open(minutes=context.observe_timing))
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=context.entry_timing))   
    schedule_function(close_orders, date_rules.every_day(), time_rules.market_open(minutes=context.exit_timing))
    
    # Create our dynamic stock selector.
    attach_pipeline(make_pipeline(context), 'mypipe')
    
        
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
    
         
def make_pipeline(context):
    base_universe = Q500US()
    # 昨日の終値
    yesterday_close = USEquityPricing.close.latest
    yesterday_volume = USEquityPricing.volume.latest
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = dollar_volume.percentile_between(context.high_dollar_volume_thresh_min, context.high_dollar_volume_thresh_max)
    sector = Sector()
    rsi = RSI(inputs=[USEquityPricing.close])
    
    pipe = Pipeline(
        screen = base_universe & high_dollar_volume,
        columns = {'high_dollar_volume': high_dollar_volume,
                   'sector': sector,
                   'rsi': rsi,
                   'roa': ROA(),
                   'roe': ROE(),
                   'normalized_basic_eps': NormalizedBasicEps(),
                   'net_income_growth': NetIncomeGrowth(),
                   'pe': PE(),
                   'book_value_yield': BookValueYield(),
                   'dividend_yield': DividendYield(),
                   'period_ending_date': PeriodEndingDate(),
                   'prev_close': yesterday_close,
                   
                   })
    return pipe
 
def before_trading_start(context, data):
    context.output = pipeline_output('mypipe')
    context.sids = context.output.index
    
    context.gapup_min_turnover_ratio = 0.00
    context.gapup_max_turnover_ratio = 1.0
    context.gapup_min_gap = -1.0
    context.gapup_max_gap = 1.0
    context.history_range = 30 * 390 
    
    context.cnt = 0 

    context.short_candidates = list()
    context.long_candidates = list()
    context.df_prediction = pd.DataFrame()
    
    # schedule function では after market のスケジュールは出来ないので，月曜のbefore_trading_startにモデルを洗い替え    
    dt = get_datetime('US/Eastern')
    youbi = dt.weekday()
   
    if youbi == 1:
        logging("today is monday")
        create_model(context, data)
        


def calc_gap(context, data):
    co = context.output
    sids = co.index
    
    pan_1d_history = data.history(sids, ['price', 'volume'], bar_count=2, frequency='1d')
    # pan_1d_history.major_axis = pan_1d_history.major_axis.tz_convert(tz_ny)
    
    s_gap = pan_1d_history['price'].pct_change().ix[1]
    df_turnover = pan_1d_history['price'] * pan_1d_history['volume'] 
    s_turnover_ratio = df_turnover.ix[-1] / df_turnover.ix[0] 
    s_latest_turnover = df_turnover.ix[-1] 

    # 今後，フィルターをかける事があるかもしれないので，消さずにとっとく．
    df_eligibles = pd.DataFrame({
            'gap': s_gap,
            'turnover_ratio': s_turnover_ratio, 
        })
    df_eligibles = df_eligibles[(df_eligibles.turnover_ratio > context.gapup_min_turnover_ratio)&
                                (df_eligibles.turnover_ratio < context.gapup_max_turnover_ratio)]
    
    df_eligibles = df_eligibles[(df_eligibles.gap > context.gapup_min_gap)&
                                (df_eligibles.gap < context.gapup_max_gap)]
    return df_eligibles

def at_two_times(df, time1, time2):
    idx = np.sort(np.append(df.index.indexer_at_time(time1) , df.index.indexer_at_time(time2)))
    return df.ix[idx]
    

def create_model_data(context, data, bar_count, train=True):
    co = context.output
    sids = co.index.tolist() + [context.spy]
    
    logging("start model data creat")
    
    pan_historical_data = data.history(sids,['open','price', 'volume'], bar_count = bar_count, frequency='1m')
    pan_historical_data.major_axis = pan_historical_data.major_axis.tz_convert(tz_ny)
    
    df_price_btw_1600_0931 = pan_historical_data['price'].fillna(method='ffill').between_time("16:00", "09:31")
    df_volume_btw_1600_0931 = pan_historical_data['volume'].between_time("16:00", "09:31")
    df_turnover_btw_1600_0931 = df_price_btw_1600_0931 * df_volume_btw_1600_0931
    
    df_gap = df_price_btw_1600_0931.pct_change().at_time("09:31")
    df_spy_gap_diff = df_gap.sub(df_gap[context.spy],axis=0)

    
    df_turnover_ratio = df_turnover_btw_1600_0931 / df_turnover_btw_1600_0931.shift(1) 
    df_turnover_ratio = df_turnover_ratio.at_time("09:31")
    
   
    idx = df_gap.index
    clm = df_gap.columns
    df_roe = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_roa = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_normalized_basic_eps = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_net_income_growth = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_pe = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_book_value_yield = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_dividend_yield = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)
    df_period_ending_date = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)  
    df_return = pd.DataFrame(np.zeros_like(df_gap.values), index = idx, columns=clm)  
    
    if train:
        ## 0931のCloseでGAPを調べて，0932にポジションを持つ
        ## 0932-1010 のデータを取得
        df_price_from_0932_to_1010 = pan_historical_data['price'].fillna(method='ffill').between_time("09:32", "10:10")
        ## そこから0932と1010のデータを取得
        ## そうすると，0932が必ず先頭にくるデータを取得できる
        df_price_btw_0932_1010 = at_two_times(df_price_from_0932_to_1010, "09:32", "10:10")
        df_return = df_price_btw_0932_1010.pct_change().at_time("10:10")

    for s in sids:
        if s !=context.spy:
            df_roe[s] = co.ix[s]['roe']
            df_roa[s] = co.ix[s]['roa']
            df_normalized_basic_eps[s] = co.ix[s]['normalized_basic_eps']
            df_net_income_growth[s] = co.ix[s]['net_income_growth']
            df_pe[s] = co.ix[s]['pe']
            df_book_value_yield[s] = co.ix[s]['book_value_yield']
            df_dividend_yield[s] = co.ix[s]['dividend_yield']
            df_period_ending_date[s] = co.ix[s]['period_ending_date']
    

    df_return.index = df_return.index.strftime("%Y-%m-%d")
    df_turnover_ratio.index = df_turnover_ratio.index.strftime("%Y-%m-%d")
    df_gap.index = df_gap.index.strftime("%Y-%m-%d")
    df_spy_gap_diff.index = df_spy_gap_diff.index.strftime("%Y-%m-%d")
    df_roe.index = df_roe.index.strftime("%Y-%m-%d")
    df_roa.index = df_roa.index.strftime("%Y-%m-%d")
    df_normalized_basic_eps.index = df_normalized_basic_eps.index.strftime("%Y-%m-%d")
    df_net_income_growth.index = df_net_income_growth.index.strftime("%Y-%m-%d")
    df_pe.index = df_pe.index.strftime("%Y-%m-%d")
    df_book_value_yield.index = df_book_value_yield.index.strftime("%Y-%m-%d")
    df_dividend_yield.index = df_dividend_yield.index.strftime("%Y-%m-%d")
    df_period_ending_date.index = df_period_ending_date.index.strftime("%Y-%m-%d")
        
    
    # 時間データは消しつつ，マージ
    pan  = pd.Panel({"return": df_return, 
                     "turnover_ratio": df_turnover_ratio, 
                     "gap":df_gap,
                     "spy_gap_diff": df_spy_gap_diff, 
                     "roe": df_roe,
                     "roa": df_roa, 
                     "normalized_basic_eps": df_normalized_basic_eps,
                     "net_income_growth": df_net_income_growth,
                     "pe": df_pe, 
                     "book_value_yield": df_book_value_yield, 
                     "dividend_yield": df_dividend_yield, 
                     "period_ending_date": df_period_ending_date, 
             })
    pan = pan.transpose(1,2,0)
    #print pan.items 
    df_list = list()
    for item in pan.items: 
        df_list.append(pan[item])
    df = pd.concat(df_list)
    
    # spy_gap_diff が1%以上のデータだけフィルタ
    # df = df[(df["spy_gap_diff"] > 0.01)|(df["spy_gap_diff"] < -0.01)]
    
    # GAPUP/Downだけのモデル
    df = df[df["spy_gap_diff"] > 0.005]
    
    df = df.replace([np.inf, -np.inf], np.nan)
    
    print len(df)
    print len(df.dropna())
    
    return df.dropna() 

def create_model(context, data):
    logging("start create model")
    df = create_model_data(context, data, context.history_range)
    logging(df.isnull().values.any())
    
    X = df.ix[:, df.columns != "return"].values
    Y = df["return"].values
    
    context.model = RandomForestRegressor(100) 
    context.model.fit(X,Y)
    
def trade(context, data):
    if context.model:
        df = create_model_data(context, data, 10, train=False)
        sids = df.index
        
        test_data = df.ix[:, df.columns != "return"]
        X = test_data.values
        
        prediction = context.model.predict(X)
        context.df_prediction = pd.DataFrame(prediction, index=sids, columns=["return"]).sort_values(by="return")
        
        # gap > 0 だけLong， gap < 0 だけShort
        context.short_candidates = context.df_prediction.head(5).index.values
        #context.long_candidates = context.df_prediction.tail(5).index.values
        #context.short_candidates = context.df_prediction[df['gap'] > 0].head(5).index.values
        #context.long_candidates = context.df_prediction[df['gap'] < 0].tail(5).index.values
        
    else:
        print "model has not been created yet."
    

    
def my_assign_weights(context, data):
    pass


def get_prices(context, data, sid):
    s = data.history(sid, fields="price", bar_count=context.exit_timing+1, frequency="1m")
    yesterday_close = 0
    today_open = context.observe_timing+1
    #entry = today_open+1 #+2
    entry = context.entry_timing
    exit = -1
    assert s.index[yesterday_close].minute == 0   
    # assert s.index[today_open].minute != 31   
    # assert s.index[entry].minute == 32  
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


def my_rebalance(context, data):
    if (len(context.long_candidates) > 0) or (len(context.short_candidates) > 0):
        cnt = len(context.long_candidates)+len(context.short_candidates)
        for sid in context.long_candidates:
            order_percent(sid, 1.0/cnt)
        for sid in context.short_candidates:
            order_percent(sid, -1.0/cnt)

def close_orders(context, data):
    for sid in context.portfolio.positions:
        amount = context.portfolio.positions[sid].amount
        sector = context.MORNINGSTAR_SECTOR_CODES[context.output.sector.ix[sid]]
        pipeline_close_price = context.output.prev_close.ix[sid]
        opentime = context.portfolio.positions[sid].last_sale_date.astimezone(pytz.timezone('US/Eastern'))
        openprice = context.portfolio.positions[sid].cost_basis
        currentprice = context.portfolio.positions[sid].last_sale_price
        prediction = context.df_prediction.ix[sid]['return']
        

        order_target(sid, 0)
        if amount > 0:
            side = 'Long exit'
            gap, pl, close_price = return_at_long_position_closed(context, data, sid)
            result = currentprice / openprice - 1
        elif amount < 0:
            side = 'Short exit'
            gap, pl, close_price = return_at_short_position_closed(context, data, sid)
            result = openprice / currentprice - 1
            
        logging("{0}\t{1}\t{2: .5f}\t{3: .5f}\t{4}\t{5: .5f}\t{6: .5f}\t{7}\t{8: .5f}\t{9: .5f}\t{10: .5f}\t{11: .5f}\t{12: .5f}".format(side, sid.symbol, gap, pl, sector, close_price, pipeline_close_price, opentime,amount, openprice, currentprice, prediction, result))
        
        
        
def my_record_vars(context, data):
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass 

    # if context.cnt <= 0:
    #     context.cnt += 1 
    #     trade(context,data)
        
        
        
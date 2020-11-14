"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import Q1500US, QTradableStocksUS
import pandas as pd 

def initialize(context):
    """
    Called once at the start of the algorithm.
    """
    # Rebalance every day, 1 hour after market open.
    algo.schedule_function(
        get_gapups,
        algo.date_rules.every_day(),
        algo.time_rules.market_open( minutes=1),
    )

    algo.schedule_function(
        get_price_1000,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=30),
    )  
    
    algo.schedule_function(
        rebalance,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=31),
    ) 
    
    algo.schedule_function(
        get_price_1040,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=70),
    )    
    algo.schedule_function(
        close_all,
        algo.date_rules.every_day(),
        algo.time_rules.market_open(minutes=71),
    )    

   
    # Create our dynamic stock selector.
    algo.attach_pipeline(make_pipeline(), 'pipeline')
    context.threshold = 5


def make_pipeline():

    # Base universe set to the Q1500US
    base_universe = QTradableStocksUS()

    # Factor of yesterday's close price.
    yesterday_close = USEquityPricing.close.latest

    pipe = Pipeline(
        screen=base_universe,
        columns={
            'close': yesterday_close,
        }
    )
    return pipe


def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = algo.pipeline_output('pipeline')
    context.security_list = context.output.index

def get_gapups(context, data):
    prices = data.current(context.security_list,"price")
    df = pd.concat([prices, context.output], axis=1)
    df["gap"] = df["price"]/df["close"]-1
    df["gap up over 5%"] = df["gap"] > 0.05
    context.df_tickers = pd.Series()
    if len(df[df["gap up over 5%"]]) > context.threshold:
        log.info(len(df[df["gap up over 5%"]]))
        # GAPUP５％以上が160以上あった場合（：100はだいたい160以上だったので）
        # Open３０分で，６％以上上がった銘柄と５％下がった銘柄は，トレンド通りポジションを持って
        # Open７０分後にクローズ
        context.df_tickers = df[df["gap up over 5%"]]
        # log.info(context.df_tickers)
   

def get_price_1000(context, data):
    if not context.df_tickers.empty:
        price_1000 = data.current(context.df_tickers.index, 'price')
        price_1000.name = "price_1000"
        context.df_tickers = pd.concat([context.df_tickers, price_1000], axis=1)
        context.df_tickers["change 0931 to 1000"] = context.df_tickers["price"]/context.df_tickers["price_1000"]-1
        # log.info(context.df_tickers)
        
        
def get_price_1040(context, data):
    if not context.df_tickers.empty:
        price_1040 = data.current(context.df_tickers.index, 'price')
        price_1040.name = "price_1040"
        context.df_tickers = pd.concat([context.df_tickers, price_1040], axis=1)  
        # log.info(context.df_tickers)
        
def rebalance(context, data):
    if not context.df_tickers.empty:
        longs = context.df_tickers[context.df_tickers["change 0931 to 1000"] > 0].index
        shorts = context.df_tickers[context.df_tickers["change 0931 to 1000"] < 0].index
        log.info("longs")
        log.info(longs)
        log.info("shorts")        
        log.info(shorts)
        # longs = [symbol for symbol in longs if data.can_trade(symbol)]
        # shorts = [symbol for symbol in shorts if data.can_trade(symbol)]
        
        cnt = len(longs) + len(shorts)
        log.info(cnt)
        
        for s in longs: 
            if data.can_trade(s):
                order_target_percent(s, 1/cnt*0.9)
            else:
                log.info("Cannot place order {}".format(s.symbol))
               
        for s in shorts: 
            if data.can_trade(s):
                order_target_percent(s, 1/cnt*0.9*-1)
            else: 
                log.info("Cannot place order {}".format(s.symbol))
                
def close_all(context, data):
    for s in context.portfolio.positions:
        if data.can_trade(s):
            order_target(s, 0)
        else:
            log.info("Cannot place order {}".format(s.symbol))
        

        
        
def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass


def handle_data(context, data):
    """
    Called every minute.
    """
    pass
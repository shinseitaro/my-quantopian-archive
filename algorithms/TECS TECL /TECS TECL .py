"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline, CustomFilter
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import QTradableStocksUS, StaticAssets

def logging(msgs):
    dt = get_datetime('US/Eastern').strftime("%Y/%m/%d %H:%M")
    msgs = '\n%s: %s' % (dt, msgs)  
    log.info(msgs)

def initialize(context):
    
    algo.schedule_function(
        rebalance,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(minutes=11),
    )

    algo.schedule_function(
        position_close,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(),
    )
    
    # Create our dynamic stock selector.
    algo.attach_pipeline(make_pipeline(), 'pipeline')



def make_pipeline():
    mysymbols = StaticAssets(symbols('soxs', 'soxl'))
    yesterday_close = USEquityPricing.close.latest

    pipe = Pipeline(
        columns={
            'close': yesterday_close,
        },
        screen=mysymbols
    )
    return pipe


def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = algo.pipeline_output('pipeline')

    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index



def rebalance(context, data):
    df = context.output
    df["current"] = data.current(df.index,'price')
    df["change"] = df["current"] / df["close"] - 1
    
    candidates = df[df["change"] > 0.05]
    if not candidates.empty:
        for stock in candidates.index:
            if data.can_trade(stock):
                order_target_percent(stock, 0.5)
                logging("ORDER: {} PRICE: {} CHANGE: {}".format(stock.symbol, candidates["current"][stock], candidates["change"][stock]))
                            
def position_close(context, data):
    for stock in context.portfolio.positions:
        if data.can_trade(stock):
            order_target_percent(stock, 0)
            logging("CLOSE: {}".format(stock.symbol))
            
        


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
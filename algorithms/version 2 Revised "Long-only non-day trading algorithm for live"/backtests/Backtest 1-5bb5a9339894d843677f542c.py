from quantopian.pipeline import Pipeline
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar
from quantopian.pipeline.factors import SimpleMovingAverage, AverageDollarVolume
from quantopian.pipeline.filters.morningstar import IsPrimaryShare
from quantopian.pipeline.filters import QTradableStocksUS


import numpy as np  # needed for NaN handling
import math  # ceil and floor are useful for rounding

from itertools import cycle


def initialize(context):
    # set_commission(commission.PerShare(cost=0.01, min_trade_cost=1.50))
#    set_slippage(
#        slippage.VolumeShareSlippage(
#            volume_limit=.20,
#            price_impact=0.0))
    # set_slippage(slippage.FixedSlippage(spread=0.00))
#    set_commission(commission.PerTrade(cost=0.00))
    # set_slippage(slippage.FixedSlippage(spread=0.00))
    set_long_only()

    context.MaxCandidates = 100 #
    context.MaxBuyOrdersAtOnce = 30 #30
    context.MyLeastPrice = 3 #3.00
    context.MyMostPrice = 12 #25 #25.00
    context.MyFireSalePrice = context.MyLeastPrice
    context.MyFireSaleAge = 6
    context.LowerFilter = 6
    context.UpperFilter = 15 # 20 #40
    context.ShortSmaTerm = 3
    context.LongSmaTerm = 45
    context.BuyFactor = 0.98 #0.99
    context.SellFactor = 1.01
    context.PriceJumpUpThreshold = 1.25
    context.FireSaleMultiplier = 0.95
    RebalanceIntervalMinutes = 10 #2＃10

    # over simplistic tracking of position age
    context.age = {}
    #print len(context.portfolio.positions)

    # Rebalance
    TradingHours = 6.5
    TradingMinutes = int(TradingHours*60)
    for m in xrange(
        1,
        TradingMinutes,
        RebalanceIntervalMinutes):
        schedule_function(
            my_rebalance,
            date_rules.every_day(),
            time_rules.market_open(minutes=m))

    # Prevent excessive logging of canceled orders at market close.
    schedule_function(
        cancel_open_orders,
        date_rules.every_day(),
        time_rules.market_close(hours=0, minutes=1))

    # Record variables at the end of each day.
    schedule_function(
        my_record_vars,
        date_rules.every_day(),
        time_rules.market_close())

    # Create our pipeline and attach it to our algorithm.
    my_pipe = make_pipeline(context)
    attach_pipeline(my_pipe, 'my_pipeline')


def make_pipeline(context):
    
    # At least a certain price
    price = USEquityPricing.close.latest
    AtLeastPrice = (price >= context.MyLeastPrice)
    AtMostPrice = (price <= context.MyMostPrice)

    # Filter for stocks that pass all of our previous filters.
    tradeable_stocks = (
        QTradableStocksUS() 
        & AtLeastPrice
        & AtMostPrice
    )

    log.info(
        '''
Algorithm initialized variables:
 context.MaxCandidates %s
 LowVar %s
 HighVar %s''' %
        (context.MaxCandidates, context.LowerFilter, context.UpperFilter))

    # High dollar volume filter.
    base_universe = AverageDollarVolume(
        window_length=20,
        mask=tradeable_stocks
    ).percentile_between(context.LowerFilter, context.UpperFilter)

    # Short close price average.
    ShortSMA = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=context.ShortSmaTerm,
        mask=base_universe)

    # Long close price average.
    LongSMA = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=context.LongSmaTerm,
        mask=base_universe)

    percent_difference = (ShortSMA - LongSMA) / LongSMA

    # Filter to select securities to long.
    stocks_worst = percent_difference.bottom(context.MaxCandidates)

    return Pipeline(
        columns={
            'stocks_worst': stocks_worst
        },
        screen=stocks_worst, 
    )


def my_compute_weights(context):
    """
    Compute ordering weights.
    """
    # Compute even target weights for our long positions and short positions.
    stocks_worst_weight = 1.00 / len(context.stocks_worst)
    return stocks_worst_weight

def print_position(context):
    log.info([(sid.symbol, 
               context.portfolio.positions[sid].amount) 
              for sid in context.portfolio.positions])
    

def before_trading_start(context, data):
    # Gets our pipeline output every day.
    context.output = pipeline_output('my_pipeline')
    stocks_worst = context.output['stocks_worst']
    context.stocks_worst = context.output[stocks_worst].index.tolist()
    context.stocks_worst_weight = my_compute_weights(context)
    context.MyCandidate = cycle(context.stocks_worst)
    context.MyCandidateMean = {}
    context.LowestPrice = context.MyLeastPrice  # reset beginning of day
    positions = context.portfolio.positions
    
    #print_position(context)
    #print 'beggining positions', len(positions)
    
    for stock in positions:
        CurrPrice = float(data.current(stock, 'price'))
        if CurrPrice < context.LowestPrice:
            context.LowestPrice = CurrPrice
        if stock in context.age:
            context.age[stock] += 1
        else:
            context.age[stock] = 1
    for stock in context.age.keys():
        if stock not in positions:
            del context.age[stock]
        else:
            message = 'stock.symbol:{}  age:{}'
            #log.info(message.format(stock.symbol,  context.age[stock]))
    for stock in context.stocks_worst:
        PH_Avg = data.history(stock, 'price', 20, '1d').mean()
        context.MyCandidateMean[stock] = PH_Avg       

           
def my_rebalance(context, data):
    cancel_open_buy_orders(context, data)
    
    #print_position(context)
    # Order sell at profit target in hope that somebody actually buys it
    positions = context.portfolio.positions
    for stock in positions:
        age = context.age.get(stock, -1)
        if not get_open_orders(stock):
            StockShares = positions[stock].amount
            CurrPrice = float(data.current(stock, 'price'))
            CostBasis = float(positions[stock].cost_basis)

            if np.isnan(CostBasis) or age == 1:
                pass  # probably best to wait until nan goes away
            elif age == -1:
                # 新規購入銘柄
                context.age[stock] = 1
            else:
                sell_order(context, age, stock, StockShares, CurrPrice, CostBasis)

    for ThisBuyOrder in range(context.MaxBuyOrdersAtOnce):
        stock = context.MyCandidate.next()
        CurrPrice = float(data.current(stock, 'price'))
        if np.isnan(CurrPrice):
            pass  # probably best to wait until nan goes away
        else:
            buy_prder(context, data, stock, CurrPrice)
            

def sell_order(context, age, stock, StockShares, CurrPrice, CostBasis):
    if (context.MyFireSaleAge <= age
    and (context.MyFireSalePrice > CurrPrice or CostBasis > CurrPrice)):
        SellPrice = float(make_div_by_05(context.FireSaleMultiplier*CurrPrice, buy=False))
    else:
        SellPrice = float(make_div_by_05(                           CostBasis*context.SellFactor, buy=False))
    #order(stock, -StockShares, style=LimitOrder(SellPrice))
    order_target(stock, 0, style=LimitOrder(SellPrice))
    

    
def buy_prder(context, data, stock, CurrPrice):
    PH_Avg = context.MyCandidateMean.get(stock)
    if CurrPrice > float(context.PriceJumpUpThreshold * PH_Avg):
        BuyPrice = float(CurrPrice)
    else:
        BuyPrice = float(CurrPrice * context.BuyFactor)
    WeightThisBuyOrder = float(1.00 / context.MaxBuyOrdersAtOnce)
    cash = context.portfolio.cash
    StockShares = int(WeightThisBuyOrder*cash/BuyPrice)
    BuyPrice = float(make_div_by_05(BuyPrice, buy=True))
    order(stock, StockShares, style=LimitOrder(BuyPrice))

 
# if cents not divisible by .05, round down if buy, round up if sell
def make_div_by_05(s, buy=False):
    s *= 20.00
    s = math.floor(s) if buy else math.ceil(s)
    s /= 20.00
    return s


def cancel_open_buy_orders(context, data):
    oo = get_open_orders()
    if len(oo) == 0:
        return
    for stock, orders in oo.iteritems():
        for o in orders:
            # message = 'Canceling order of {amount} shares in {stock}'
            # log.info(message.format(amount=o.amount, stock=stock))
            if 0 < o.amount:  # it is a buy order
                cancel_order(o)


def cancel_open_orders(context, data):
    oo = get_open_orders()
    if len(oo) == 0:
        return
    for stock, orders in oo.iteritems():
        for o in orders:
            # message = 'Canceling order of {amount} shares in {stock}'
            # log.info(message.format(amount=o.amount, stock=stock))
            cancel_order(o)
            

def my_record_vars(context, data):
    """
    Record variables at the end of each day.
    """

    # Record our variables.
    record(leverage=context.account.leverage)
    record(positions=len(context.portfolio.positions))
    if 0 < len(context.age):
        MaxAge = context.age[max(
            context.age.keys(), key=(lambda k: context.age[k]))]
        print MaxAge
        record(MaxAge=MaxAge)
    record(LowestPrice=context.LowestPrice)


def log_open_order(StockToLog):
    oo = get_open_orders()
    if len(oo) == 0:
        return
    for stock, orders in oo.iteritems():
        if stock == StockToLog:
            for o in orders:
                message = 'Found open order for {amount} shares in {stock}'
                log.info(message.format(amount=o.amount, stock=stock))


def log_open_orders():
    oo = get_open_orders()
    if len(oo) == 0:
        return
    for stock, orders in oo.iteritems():
        for o in orders:
            message = 'Found open order for {amount} shares in {stock}'
            log.info(message.format(amount=o.amount, stock=stock))


# This is the every minute stuff
def handle_data(context, data):
    pass
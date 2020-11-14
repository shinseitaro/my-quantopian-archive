"""
アルパカに紹介してあったコードを書き直してみる
"""
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline

from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import QTradableStocksUS
from quantopian.pipeline.factors import SimpleMovingAverage, AverageDollarVolume

import numpy as np 
import math 


from quantopian.pipeline.data import morningstar
from quantopian.pipeline.filters.morningstar import IsPrimaryShare

def initialize(context):
    set_long_only()
    context.MaxCandidates = 100
    context.MaxBuyOrdersAtOnce = 30
    context.MyLeastPrice = 3.00
    context.MyMostPrice = 25.00
    context.MyFireSalePrice = context.MyLeastPrice
    context.MyFireSaleAge = 6    
    
    # hold 期間を確認するための辞書
    context.age = {}
    
    # rebalance schedule 
    start_min = 1
    end_min = int(6.5 * 60) # =取引時間6.5時間*60分
    everyminute = 10
    
    # 毎10分ごとにリバランス。
    for m in range(start_min, end_min, everyminute):
        schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(minutes=m))
        
    # 描画        
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    
    my_pipe = make_pipeline(context)
    algo.attach_pipeline(my_pipe, 'pipeline')
    


def make_pipeline(context):
    """
    Create our pipeline.
    """

    # Filter for primary share equities. IsPrimaryShare is a built-in filter.
    primary_share = IsPrimaryShare()

    # Equities listed as common stock (as opposed to, say, preferred stock).
    # 'ST00000001' indicates common stock.
    common_stock = morningstar.share_class_reference.security_type.latest.eq(
        'ST00000001')

    # Non-depositary receipts. Recall that the ~ operator inverts filters,
    # turning Trues into Falses and vice versa
    not_depositary = ~morningstar.share_class_reference.is_depositary_receipt.latest

    # Equities not trading over-the-counter.
    not_otc = ~morningstar.share_class_reference.exchange_id.latest.startswith(
        'OTC')

    # Not when-issued equities.
    not_wi = ~morningstar.share_class_reference.symbol.latest.endswith('.WI')

    # Equities without LP in their name, .matches does a match using a regular
    # expression
    not_lp_name = ~morningstar.company_reference.standard_name.latest.matches(
        '.* L[. ]?P.?$')

    # Equities with a null value in the limited_partnership Morningstar
    # fundamental field.
    not_lp_balance_sheet = morningstar.balance_sheet.limited_partnership.latest.isnull()

    # Equities whose most recent Morningstar market cap is not null have
    # fundamental data and therefore are not ETFs.
    have_market_cap = morningstar.valuation.market_cap.latest.notnull()

    # At least a certain price
    price = USEquityPricing.close.latest
    AtLeastPrice = (price >= context.MyLeastPrice)
    AtMostPrice = (price <= context.MyMostPrice)

    # Filter for stocks that pass all of our previous filters.
    tradeable_stocks = (
        primary_share
        & common_stock
        & not_depositary
        & not_otc
        & not_wi
        & not_lp_name
        & not_lp_balance_sheet
        & have_market_cap
        & AtLeastPrice
        & AtMostPrice
    )

    LowVar = 6
    HighVar = 40

    log.info(
        '''
Algorithm initialized variables:
 context.MaxCandidates %s
 LowVar %s
 HighVar %s''' %
        (context.MaxCandidates, LowVar, HighVar))

    # High dollar volume filter.
    # LowVar ~ HighVar の間の20日出来高平均．
    # 出来高平均が低いものだけ取得
    base_universe = AverageDollarVolume(
        window_length=20,
        mask=tradeable_stocks
    ).percentile_between(LowVar, HighVar)

    # Short close price average.
    # 期間3日のSMA
    ShortAvg = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=3,
        mask=base_universe
    )

    # Long close price average.
    # 期間45日のSMA
    LongAvg = SimpleMovingAverage(
        inputs=[USEquityPricing.close],
        window_length=45,
        mask=base_universe
    )

    # （SMA3-SMA45）をSMA45から見てどのくらい差があるか
    # つまり，この差がポジティブに大きければ，過去45日間で大きく値が上がったと言う意味
    percent_difference = (ShortAvg - LongAvg) / LongAvg

    # Filter to select securities to long.
    # percent_differenceが小さい銘柄を下から100銘柄
    # つまり，過去の値動きが小さい．もしくはネガティブに大きいものを拾ってくる．
    stocks_worst = percent_difference.bottom(context.MaxCandidates)
    securities_to_trade = (stocks_worst)

    return Pipeline(
        columns={
            'stocks_worst': stocks_worst
        },
        screen=(securities_to_trade),
    )


def before_trading_start(context, data):
    
    context.output = algo.pipeline_output('pipeline')
    context.security_list = context.output.index
    log.debug("context.security_list {}".format(sorted([s.symbol for s in context.security_list])))
    
    # hold している銘柄で価格が一番低いもの（context.MyLeastPriceよりも低い場合のみ）を表示
    # しているのだが必要性がわからないのでコメントアウト
    # for stock in context.portfolio.positions:
    #     current_price = data.current(stock, 'price')
    #     if current_price < context.MyLeastPrice:
    #         context.MyLeastPrice = current_price
    #         s = stock
    # msg = 'symbol: {symbol}, price: {price}'          
    # log.info(msg.format(symbol=stock.symbol, price=context.LowestPrice))

    # 何日ホールドしているのか確認               
    for stock in context.portfolio.positions:
        if stock in context.age:
            context.age[stock] += 1
        else:
            context.age[stock] = 1

    # クローズした銘柄を外す          
    syms = set(context.age.keys())
    pos = set([s for s in context.portfolio.positions])
    diff = syms.difference(pos)
    
    for stock in list(diff):
        del context.age[stock]

    for stock in context.portfolio.positions:
        msg = 'stock.symbol: {symbol}, age: {age}'
        #log.info(msg.format(symbol=stock.symbol, age=context.age[stock]))
        
    #log.info("Num of current position: {}".format(len(context.portfolio.positions)))

    
def my_rebalance(context, data):
    buy_factor = 0.99 
    sell_factor = 1.01 
    
    ## position close
    positions = context.portfolio.positions
    log.info("before rebalance {}".format(len(positions)))
    for stock in positions:
        if not stock in context.age:
           context.age[stock] = 1 
        # 注文を出してない場合に限る
        if not get_open_orders(stock): 
            # 取得(平均)価格
            average_price = float(positions[stock].cost_basis)
            # 現在価格
            current_price = float(data.current(stock, 'price'))
            # 1％のせた価格
            sell_price = math.floor(average_price * sell_factor)
            
            # 何らかの理由でNaNになっている場合。    
            if not data.can_trade(stock):
                msg = "cannot trade for some reasons. stock:{symbol}"    
                log.error(msg.format(symbol=stock.symbol))
                continue
            
            # ポジションホールド一日目は何もしない           
            if (stock in context.age and context.age[stock] < 2):
                continue
        
            # ２日以上５日以内
            elif (stock in context.age and context.age[stock] < 6):
                # 評価価格にかかわらず、1％乗せて益出し注文
                order_percent(stock, 0, style=LimitOrder(sell_price))
                msg = "ProfitTake: stock:{symbol}, price:{price}, average price:{average_price}, current_price:{current_price}, age:{age}"
                
            # ６日以上の場合
            else:
                if (
                    # 現在価格が３ドル以下
                    context.MyFireSalePrice > current_price 
                    # もしくは評価損が出ている（現在価格が取得価格より安い）場合                        
                    or average_price > current_price                    
                    ):
                    # 現在価格より5％低いところで損切り注文
                    sell_price = math.ceil(current_price * 0.95)
                    order_percent(stock, 0, style=LimitOrder(sell_price))
                    msg = "LossCut: stock:{symbol}, price:{price}, average price:{average_price}, current_price:{current_price}, age:{age}"
                    
                else:
                    # そうでなければ益出し注文
                    order_percent(stock, 0, style=LimitOrder(sell_price))
                    msg = "ProfitTake: stock:{symbol}, price:{price}, average price:{average_price}, current_price:{current_price}, age:{age}"
                    
            log.info(msg.format(symbol=stock.symbol, price=sell_price, average_price=average_price, current_price=current_price, age = context.age[stock]))
                    
    log.info("after rebalance {}".format(len(positions)))                    
    
    ## position open 
    weight = 1.00 / context.MaxBuyOrdersAtOnce
    cash = context.portfolio.cash 
    
    for stock in context.security_list:
        average_20 = data.history(stock, 'price', 20, '1d').mean()
        current_price = data.current(stock, 'price')
        
        if not data.can_trade(stock):
            log.error("stock {} can NOT be tradable for some reasons".format(stock.symbol))
        else:
            ## 購入株数
            share = math.floor(cash / current_price * weight)
            # log.info("share: {cash}, {current_price}, {weight}, {share}".format(
            #          cash=cash, current_price=current_price, weight=weight, share=share))
            
            if current_price > average_20 * 1.25:
                order_target(stock, share)
            else:
                buy_price = current_price * buy_factor
                order_target(stock, share, style=LimitOrder(buy_price))
            
            # オーダーしたらcontext.age に入れる
            # if stock not in context.age:
            #     context.age[stock] = 0
          
        
    
    


def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass


def handle_data(context, data):
    """
    Called every minute.
    """
    pass
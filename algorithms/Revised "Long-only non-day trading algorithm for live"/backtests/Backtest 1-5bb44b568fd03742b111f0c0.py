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

def initialize(context):
    #set_long_only()
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
    # ベースユニバース
    base_universe = QTradableStocksUS()
    # make_pipelineを実行するのは before_trading_start（08：45ET）
    # 最新のプライスは前日の終値。
    yesterday_close = USEquityPricing.close.latest
    min_price = yesterday_close >= context.MyLeastPrice
    max_price = yesterday_close <= context.MyMostPrice
    
    tradeable_stocks = base_universe & min_price & max_price
    base_universe = AverageDollarVolume(window_length=20, mask=tradeable_stocks).percentile_between(6,40)
    
    short_sma = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=3, mask=base_universe)
    long_sma = SimpleMovingAverage(inputs=[USEquityPricing.close], window_length=45, mask=base_universe)
    
    percent_difference = (short_sma - long_sma) / long_sma 
    
    #stocks_worst = percent_difference.bottom(context.MaxCandidates) 
    stocks_worst = percent_difference.bottom(context.MaxBuyOrdersAtOnce) 
    
    pipe = Pipeline(
        columns={
            'percent_difference': percent_difference,
            'close': yesterday_close, 
        },     
        screen=stocks_worst)
    
    return pipe


def before_trading_start(context, data):
    
    context.output = algo.pipeline_output('pipeline')
    context.security_list = context.output.index
    
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
        
    log.info("Num of current position: {}".format(len(context.portfolio.positions)))
            

   
    
def my_rebalance(context, data):
    buy_factor = 0.99 
    sell_factor = 1.01 
    
    ## position close
    positions = context.portfolio.positions
    for stock in positions:
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
                msg = "ProfitTake: stock:{symbol}, price:{price}, average price:{average_price}"
                
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
                    msg = "LossCut: stock:{symbol}, price:{price}, average price:{average_price}"
                    
                else:
                    # そうでなければ益出し注文
                    order_percent(stock, 0, style=LimitOrder(sell_price))
                    msg = "ProfitTake: stock:{symbol}, price:{price}, average price:{average_price}"
                    
            #log.info(msg.format(symbol=stock.symbol, price=sell_price, average_price=average_price))
                    
                    
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
            
            if current_price > average_20 * 1.25:
                order_target_value(stock, share)
            else:
                buy_price = current_price * buy_factor
                order_target_percent(stock, weight, style=LimitOrder(buy_price))
            
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
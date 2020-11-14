from quantopian.pipeline import Pipeline, CustomFilter
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline.factors import Latest
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data.psychsignal import aggregated_twitter_withretweets_stocktwits as st
#from sklearn.ensemble import RandomForestClassifier
from quantopian.pipeline.factors import SimpleMovingAverage
from quantopian.pipeline.filters import Q500US
import numpy as np

def initialize(context): 
    #I use robinhood when long only
    set_commission(commission.PerShare(cost=0.0, min_trade_cost=0.0))
    
    #ADDED TO MONITOR LEVERAGE MINUTELY.
    context.minLeverage = [0]
    context.maxLeverage = [0]
    
    context.securities_in_results = []
    attach_pipeline(Custom_pipeline(context), 'Custom_pipeline') 
    
    #PREFFERED CLASSIFIER
    #context.model = RandomForestClassifier()
    #YOU WANT A HIGH NUMBER OF ESTIMATORS AND SAMPLES TO ENSURE CONSISTENT BACKTEST PERFROMANCE.
    #context.model.n_estimators = 500
    #context.model.min_samples_leaf = 100
    context.lookback = 3
    context.history_range = 5
    
    #find the stocks we want to buy/sell
    schedule_function(evaluate, date_rules.every_day(), time_rules.market_open())
    #close positions 
    schedule_function(sell, date_rules.every_day(), time_rules.market_open())
    #open positions
    schedule_function(buy, date_rules.every_day(), time_rules.market_open(minutes = 5))

def Custom_pipeline(context):
    pipe = Pipeline()
    sma_10 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=10)
    sma_50 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=50)
    pipe.add(st.bull_scored_messages .latest, 'bull_scored_messages')
    pipe.add(st.bear_scored_messages .latest, 'bear_scored_messages')
    
    #changed to be easier to read.
    pipe.set_screen(Q500US() & (sma_10 > sma_50) & ( (0.35*st.bull_scored_messages.latest) >( st.bear_scored_messages.latest) ) & (st.bear_scored_messages.latest > 10) ) 
    return pipe


def before_trading_start(context, data):
    context.longs = []
    
    #For hedgeing...

    context.shorts = []

    
    results = pipeline_output('Custom_pipeline')
    context.securities_in_results = []
    
    for s in results.index:
        context.securities_in_results.append(s) 
    
    #DEBUG
    """
    if len(context.securities_in_results) > 0.0:                
        log.info(results)
    """
        
def evaluate (context, data):
    if len(context.securities_in_results) > 0.0:                    
        print context.securities_in_results
        for sec in context.securities_in_results:
            
            # 5日分のPriceとVolumeを取得. 
            # recent_prices[0]が5日前，-1が直前
            recent_prices = data.history(sec, 'price', context.history_range, '1d').values
            recent_volumes = data.history(sec, 'volume', context.history_range, '1d').values
            
            # np.diff は，一つ前との引き算で元のリストよりひとつ少ない要素のリストを返す．
            # >>> l = [5,3,89,41,5]
            # >>> np.diff(l)
            # array([ -2,  86, -48, -36])
            price_changes = np.diff(recent_prices).tolist()
            volume_changes = np.diff(recent_volumes).tolist()

            X,Y = [],[]
            
            # context.history_range-context.lookback-1 = 5-3-1 ということは，1
            # range(1)= range(0,1) = [0]
            for i in range(context.history_range-context.lookback-1): 
                # price_changes の4日前ー5日前の値のみを Yにアペンド
                Y.append(price_changes[i+context.lookback])
                
            #context.model.fit(X, Y) 
            # 4日分のPriceとVolumeを取得
            recent_prices = data.history(sec, 'price', context.lookback+1, '1d').values
            recent_volumes = data.history(sec, 'volume', context.lookback+1, '1d').values
            price_changes =  np.diff(recent_prices).tolist()
            volume_changes = np.diff(recent_volumes).tolist()
            #prediction = context.model.predict(price_changes + volume_changes)
            
            #
            if Y[0] > -0.5: 
                # print(str(sec.symbol) +  " | " + str(Y[0]))
                if sec not in context.portfolio.positions:
                    context.longs.append(sec)
            
            #For hedging...

            if Y[0] < -1.0: 
                if sec not in context.portfolio.positions:
                    context.shorts.append(sec)
            
    #if you arent a fan of puting all of your eggs in one basket:

    if len(context.shorts) < 2:
        context.shorts = []
#Theoretical losses with shorts are infinite (although that probably will never happen, it CAN happen)
    
def sell (context,data):
    for sec in context.portfolio.positions:
        if sec not in context.longs:
            print "CLOSE %s" % sec
            order_target_percent(sec, 0.0)
            
def buy (context,data):
    for sec in context.longs:
        print "LONG %s" % sec
        order_target_percent(sec, 1.0 / (len(context.longs) + len(context.portfolio.positions)) )
    for sec in context.shorts:
        print "SHORT %s" % sec
        order_target_percent(sec,-1.0/ (len(context.shorts)+ len(context.portfolio.positions)) )
        
def handle_data(context,data):
    #if the current leverage is greater than the value in MaxLeverage, clear max leverage then append the current leverage. a similar method is used for minLeverage
    
    #max leverage is set up as an array so that one can more quickly log all leverages  find the mean leverage if they want. 
    for L in context.maxLeverage: #ADDED BY JACOB SHRUM
        if context.account.leverage > L: #ADDED BY JACOB SHRUM
            context.maxLeverage = [] #ADDED BY JACOB SHRUM
            context.maxLeverage.append(context.account.leverage) #ADDED BY JACOB SHRUM
    for L in context.minLeverage: #ADDED BY JACOB SHRUM
        if context.account.leverage < L: #ADDED BY JACOB SHRUM
            context.minLeverage = [] #ADDED BY JACOB SHRUM
            context.minLeverage.append(context.account.leverage) #ADDED BY JACOB
    record(pos=len(context.portfolio.positions), resutls=len(context.securities_in_results), Min_Leverage = context.minLeverage[0], Max_Leverage = context.maxLeverage[0],Instantaneous_Leverage = context.account.leverage)
    
    
    
    
    
    
    
                
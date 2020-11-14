
"""
PsychSignal & Machine Learning Models V2 | UPDATE: Now Tradable With Robinhood Instant | Added Notebook That Explains Reasoning - https://www.quantopian.com/posts/psychsignal-and-machine-learning-models-v2-update-now-tradable-with-robinhood-instant-added-notebook-that-explains-reasoning

直近にUpdateされているもので書きなおしています
https://www.quantopian.com/posts/psychsignal-and-machine-learning-models-v2-update-now-tradable-with-robinhood-instant-added-notebook-that-explains-reasoning#59860b0398cb7501f6e898d0

"""

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
    context.minLeverage = [0]
    context.maxLeverage = [0]
    
    context.securities_in_results = []
    attache_pipeline(Custom_pipeline(context), 'Custom_pipeline')
    
    

def Custom_pipeline(context):
    pipe = Pipeline()
    sma_10 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=10)
    sma_50 = SimpleMovingAverage(inputs = [USEquityPricing.close], window_length=50)
    
    pipe.add(st.bull_scored_messages .latest, 'bull_scored_messages')
    pipe.add(st.bear_scored_messages .latest, 'bear_scored_messages')
    pipe.add(sma_10, 'sma_10')
    pipe.add(sma_50, 'sma_50')
    
    pipe.set_screen(Q500US() 
                    & (sma_10 > sma_50) 
                    & ((st.bull_scored_messages.latest * 0.35) > st.bear_scored_messages.latest)
                    & (st.bear_scored_messages.latest > 10)
                   )
    
    return pipe

def before_trading_start(context, data):
    context.output = pipeline_output('Custom_pipeline')
    
    record(Leverage=context.account.leverage, 
           pos=len(context.portfolio.positions), 
           results=len(context.output.index))
    
    print context.output 

def trade(context, data):
    shorts = []
    longs = []
    
    if len(context.output.index ):
        for sec in context.output.index:
            recent_price = data.history(sec, 'price', context.history_range, '1d').values
            recent_vol = data.history(sec, 'volume', context.history_range, '1d').values
            # np.diff
            # >>> x = np.array([1, 2, 4, 7, 0])
            # >>> np.diff(x)
            # array([ 1,  2,  3, -7])
            price_changes = np.diff(recent_price).tolist()
            volume_changes = np.diff(recent_vol).tolist()
            
            X, Y = [], []
            
            for i in range(context.history_range-context.lookback-1): 
                X.append(price_changes[i:i+context.lookback] + volume_changes[i:i+context.lookback])
                Y.append(price_changes[i+context.lookback])
            #print X
            #print Y
            
            context.model.fit(X, Y)
            recent_prices = data.history(sec, 'price', context.lookback + 1, '1d').values
            recent_volumes = data.history(sec, 'volume', context.lookback + 1, '1d').values
            price_changes = np.diff(recent_prices).tolist()
            volume_changes = np.diff(recent_volumes).tolist()
            prediction = context.model.predict(price_changes + volume_changes) 
            
            print "symbol\t{0}\tprediction{1}".format(sec.symbol, prediction) 
            if sec not in context.portfolio.positions:
                if prediction > 0.0:
                    longs.append(sec)
                elif prediction < -0.1:
                    shorts.append(sec)
                    
    for sec in longs:
        order_target_percent(sec, 1.5 / len(longs))
        print "LONG\t{0}".format(sec.symbol)
        
    for sec in shorts:
        order_target_percent(sec, 0)
        print "Closed\t{0}".format(sec.symbol)
        
    for sec in context.portfolio.positions:
        if sec not in longs:
            order_target_percent(sec, 0) 
            print "Closed\t{0}".format(sec.symbol)
            
                        
                
                
                
                
                
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
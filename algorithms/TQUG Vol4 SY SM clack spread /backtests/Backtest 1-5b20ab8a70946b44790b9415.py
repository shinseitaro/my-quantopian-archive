"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
import numpy as np 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):
    context.soybean = continuous_future('SY', offset=1, roll='volume', adjustment='mul')
    context.soymeal = continuous_future('SM', offset=1, roll='volume', adjustment='mul')
    
    
    thread = 0.006363
    c = 1.8
    context.thread = thread * c 

    schedule_function(func=rebalance_pairs, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(minutes=30)) # minutes=30
        
    schedule_function(record_price, 
                      date_rules.every_day(), 
                      time_rules.market_open())

def rebalance_pairs(context, data):
    target_weights = dict()
    sy_contract, sm_contract = data.current([context.soybean, context.soymeal], 'contract')
    
    df_price = data.history([context.soybean,context.soymeal], 'price', 2, '1d')
    df_change = df_price.pct_change()
    
    
    ratio = df_change[context.soymeal].iloc[1] /  df_change[context.soybean].iloc[1]
    log.info(ratio)
    
    if ratio > context.thread: 
        target_weights[sy_contract] = -1 * 0.5
        target_weights[sm_contract] = 1 * 0.5
        
    if target_weights:
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[]
        )
    if ratio in [np.inf, -np.inf]:
        ratio = 0 
    record(ratio=ratio,)
        

def record_price(context, data):
    pass 

    
    
    
    
    
    
    
    
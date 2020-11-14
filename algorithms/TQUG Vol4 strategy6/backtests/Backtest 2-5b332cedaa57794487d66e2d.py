"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその6：クラックスプレッド
https://github.com/drillan/quantopian/blob/master/driller/Crack_spread-Oil01.ipynb

"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):
    sym1 = 'HO'
    sym2 = 'XB'
    
    context.sym1_1 = continuous_future(sym1, roll='calendar', offset=0)
    context.sym1_2 = continuous_future(sym1, roll='calendar', offset=1)
    context.sym1_3 = continuous_future(sym1, roll='calendar', offset=2)
    context.sym1_4 = continuous_future(sym1, roll='calendar', offset=3)
    context.sym1_5 = continuous_future(sym1, roll='calendar', offset=4)

    context.sym2_1 = continuous_future(sym2, roll='calendar', offset=0)
    context.sym2_2 = continuous_future(sym2, roll='calendar', offset=1)
    context.sym2_3 = continuous_future(sym2, roll='calendar', offset=2)
    context.sym2_4 = continuous_future(sym2, roll='calendar', offset=3)
    context.sym2_5 = continuous_future(sym2, roll='calendar', offset=4)
   
    context.sym1_list = [ context.sym1_5] #  context.sym1_1, context.sym1_2,context.sym1_3, context.sym1_4,
    context.sym2_list = [context.sym2_5] #  context.sym2_1, context.sym2_2,context.sym2_3, context.sym2_4, 
    
    context.max_hold_term = 10 
    context.upper_band = 1.09
    context.lower_band = 0.96
    context.long_spread = dict()
    context.short_spread = dict() 
    
    schedule_function(my_rebalance)
    
    
def my_rebalance(context, data):
    msg = "" 
    contract_sym1 = data.current(context.sym1_list, 'contract')
    contract_sym2 = data.current(context.sym2_list, 'contract')
    
    price_sym1 = data.current(contract_sym1, 'price')
    price_sym2 = data.current(contract_sym2, 'price')
    
    ratio = price_sym1.as_matrix() / price_sym2.as_matrix()
    #log.info([ratio, context.long_spread, context.short_spread])
    # ratio が 1以上の場合、sym1をショート、sym2をロング
    target_weight = {}
    
    for r, sym1, sym2 in zip(ratio, contract_sym1, contract_sym2):
        if not sym1 in context.long_spread.keys(): context.long_spread[sym1] = False
        if not sym2 in context.long_spread.keys(): context.long_spread[sym1] = False
        if not sym1 in context.short_spread.keys(): context.short_spread[sym1] = False
        if not sym2 in context.short_spread.keys(): context.short_spread[sym1] = False
            
        if r > context.upper_band:
            target_weight[sym1] = -0.1
            target_weight[sym2] = 0.1
            context.long_spread[sym1] = True 
            msg = "Hold long spread"
        elif r < context.lower_band:
            target_weight[sym1] = 0.1
            target_weight[sym2] = -0.1
            context.short_spread[sym1] = True 
            msg = msg + " Hold short spread"
        elif context.long_spread[sym1] and r < 1:
            target_weight[sym1] = 0
            target_weight[sym2] = 0
            context.long_spread[sym1] = False
            msg = msg + " Close long spread"
            
        elif context.short_spread[sym1] and r > 1:
            target_weight[sym1] = 0
            target_weight[sym2] = 0
            context.short_spread[sym1] = False 
            msg = msg + " Close short spread"
                
    if target_weight:
        log.info(target_weight)
        order_optimal_portfolio(
            opt.TargetWeights(target_weight),
            constraints=[]
        )
        if msg:
            log.info(msg)
    for i,r in enumerate(ratio):
        record(i=r)
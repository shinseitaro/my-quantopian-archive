"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその5：クラックスプレッド
どりらーさんの 
https://github.com/drillan/quantopian/blob/master/driller/Crack_spread-Oil01.ipynb
をベースにしたアルゴリズム

HO/XBで、1以上であればHOロングXBショート
５限月だけではなく、３，４，５限月をトレード

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
   
    context.sym1_list = [ context.sym1_3, context.sym1_4, context.sym1_5] #  context.sym1_1, context.sym1_2,
    context.sym2_list = [ context.sym2_3, context.sym2_4, context.sym2_5] #  context.sym2_1, context.sym2_2,

    schedule_function(my_rebalance)
    
    
def my_rebalance(context, data):
    contract_sym1 = data.current(context.sym1_list, 'contract')
    contract_sym2 = data.current(context.sym2_list, 'contract')
    
    price_sym1 = data.current(contract_sym1, 'price')
    price_sym2 = data.current(contract_sym2, 'price')
    
    ratio = price_sym1.as_matrix() / price_sym2.as_matrix()

    # ratio が 1以上の場合、sym1をショート、sym2をロング
    target_weight = {}
    for r, sym1, sym2 in zip(ratio, contract_sym1, contract_sym2):
        if r > 1:
            target_weight[sym1] = -0.1
            target_weight[sym2] = 0.1
        else:
            target_weight[sym1] = 0
            target_weight[sym2] = 0
    if target_weight:
        order_optimal_portfolio(
            opt.TargetWeights(target_weight),
            constraints=[]
        )
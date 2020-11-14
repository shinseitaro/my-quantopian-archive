"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその7：クラックスプレッド
https://github.com/drillan/quantopian/blob/master/driller/Crack_spread-Oil01.ipynb

ho_xb_5_ratio.std()のところだけ，
過去n日化


"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar


def initialize(context):
    sym1 = 'HO'
    sym2 = 'XB'
    
    context.sym1 = continuous_future(sym1, roll='calendar', offset=3)
    context.sym2 = continuous_future(sym2, roll='calendar', offset=3)
    
    # 標準偏差をはかる日数
    context.std_term = 20
    # ホールドする日数（アルゴリズムでは使っていない，カウントだけして，利用出来るようにしておく）
    context.holding_days = 0
    # 満期日までの残存期間を指定（これもアルゴリズムでは使っていない）
    context.n_days_before_expired = 5
    # フラグ
    context.long_spread = False
    context.short_spread = False
    
    schedule_function(my_rebalance)
    schedule_function(my_record)
    
def get_ratio(context, data):
    hist = data.history([context.sym1, context.sym2],
                        fields ='price', 
                        bar_count = context.std_term, 
                        frequency = '1d')
    
    ratio = hist[context.sym1] / hist[context.sym2] 
    std = ratio.std()
    return ratio[-1] + std 

def is_near_expiration(contract, n):
    return (contract.expiration_date - get_datetime()).days < n

def my_rebalance(context, data):
    target_weight = {}
    
    context.ratio = get_ratio(context, data)
    contract_sym1 = data.current(context.sym1, 'contract')
    contract_sym2 = data.current(context.sym2, 'contract')

    if (context.ratio < 1.0) and context.long_spread:
        target_weight[contract_sym1] = 0
        target_weight[contract_sym2] = 0
        context.holding_days = 0 
        context.long_spread = False
        
    elif (context.ratio > 1) and context.short_spread:
        target_weight[contract_sym1] = 0
        target_weight[contract_sym2] = 0
        context.holding_days = 0 
        context.short_spread = False
        
    elif context.ratio > 1.1: 
        target_weight[contract_sym1] = -0.5
        target_weight[contract_sym2] = 0.5
        context.long_spread = True
        context.holding_days = context.holding_days + 1 

    # elif context.ratio < 0.96: 
    #     target_weight[contract_sym1] = 0.5
    #     target_weight[contract_sym2] = -0.5
    #     context.short_spread = True
    #     context.holding_days = context.holding_days + 1         

    if target_weight:
        order_optimal_portfolio(
            opt.TargetWeights(target_weight),
            constraints=[]
        )

def my_record(context, data):
    record(ratio=context.ratio)
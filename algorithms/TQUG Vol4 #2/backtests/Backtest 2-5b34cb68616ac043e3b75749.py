"""
Tokyo Quantopian User Group handson Vol4
クラックスプレッド
2015/1/1−2018/6/1

"""
import pandas as pd 
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
    # .expiration_date このコントラクトの満期日を取得
    return (contract.expiration_date - get_datetime()).days < n

def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {'symbol': k.symbol, 
             'amount': v.amount,
             'average value': v.cost_basis,
             'last_sale_price': v.last_sale_price, 
             'current value': v.last_sale_price*v.amount*k.multiplier, 
             'multiplier':k.multiplier,
             'PL': (v.last_sale_price/v.cost_basis-1)*v.amount*k.multiplier, 
            # 'exp date': k.expiration_date.strftime("%Y%m%d")
            }
        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index('symbol')
    log.info(df)
    return df 

def my_rebalance(context, data):
    
    # もしポジションを持っている場合は，ログ出力．（ここはアルゴリズムには不要）
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
    else:
        log.info("No position")

    # target_weight
    target_weight = {}
    
    # 今日のコントラクトを取得
    contract_sym1 = data.current(context.sym1, 'contract')
    contract_sym2 = data.current(context.sym2, 'contract')
    # 今日のRatioを取得
    context.ratio = get_ratio(context, data)

    # ポジションクローズ１
    if (context.ratio < 1.0) and context.long_spread:
        target_weight[contract_sym1] = 0
        target_weight[contract_sym2] = 0
        context.holding_days = 0 
        context.long_spread = False

    # ポジションクローズ2        
    elif (context.ratio > 1) and context.short_spread:
        target_weight[contract_sym1] = 0
        target_weight[contract_sym2] = 0
        context.holding_days = 0 
        context.short_spread = False

    # ショートポジション注文        
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
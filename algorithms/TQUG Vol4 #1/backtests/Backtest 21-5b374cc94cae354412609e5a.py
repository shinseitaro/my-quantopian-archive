"""
Tokyo Quantopian User Group handson Vol4
基本編
"""
import pandas as pd 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):
    
    ## 原油２０１７年１月限 (10/01/2016~12/20/2016)
    # context.my_future = future_symbol("CLF17")
    # 原油期近つなぎ足
    context.my_future = continuous_future(
        'CL', 
        offset=0, # 限月．期近＝0，2番限＝1，3番限=2，・・・
        roll='calendar', # ロールするタイミング
        adjustment=None # アジャスト方法
    )
    schedule_function(my_rebalance2, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(hours=1))
    schedule_function(my_record, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(hours=1))    
    
    context.ratio = None 

def get_ratio(context, data):
    """
    過去2日間の価格を取得. 前日比を返す←間違い
    最新の価格と昨日の価格を取得．前日比を返す．
    """
    price = data.history(context.my_future, 
                         fields ='price', 
                         bar_count = 2, 
                         frequency = '1d')
    
    ratio = price.pct_change()[1]
    return ratio 
    
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

def my_rebalance1(context, data):
    """
    order_target を使って，枚数で注文する．
    """
    # もしポジションを持っている場合は，ログ出力．
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
    else:
        log.info("No position")    
        
    context.ratio = get_ratio(context, data)
    # コントラクト
    current_contract = data.current(context.my_future, 'contract') 
    
    if context.ratio < -0.01: 
        log.info("order short %s" % context.ratio )
        order_target(current_contract, -1)
    elif context.ratio > 0.01: 
        log.info("order long %s" % context.ratio )
        order_target(current_contract, 1)
    else:
        order_target(current_contract, 0)

def my_rebalance2(context, data):
    """
    order_optimal_portfolio で資金の〜％を注文するという注文を行う．
    """
    # もしポジションを持っている場合は，ログ出力．
    cpp = context.portfolio.positions  
    if cpp:
        df = get_my_position(cpp)
        log.info('PL: {}'.format(df['PL'].sum()))
    else:
        log.info("No position")
        
    target_weights = dict()
    context.ratio = get_ratio(context, data)
    
    current_contract = data.current(context.my_future, 'contract') 
    
    if context.ratio < -0.01:
        target_weights[current_contract] = -1.0 
    elif context.ratio > -0.01:
        target_weights[current_contract] = 1.0
    else:
        target_weights[current_contract] = 0 # 1 になってた0に書き換え．

    if target_weights: 
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[])


def my_record(context, data):
    record(ratio=context.ratio )
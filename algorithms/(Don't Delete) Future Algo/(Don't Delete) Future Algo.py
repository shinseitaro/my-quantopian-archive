import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.experimental.optimize as opt 

def initialize(context):
    # 引数説明　https://www.evernote.com/Home.action#b=177d468e-bf46-408c-8f29-97655b654be5&st=p&x=continuous_future&n=f550d745-8e58-44fd-80c9-e7a17110a9b6
    context.crude_oil = continuous_future('CL', offset=0, roll='calendar', adjustment='mul')
    context.gasoline = continuous_future('XB', offset=1, roll='calendar', adjustment='mul')
    
    context.long_ma = 65
    context.short_ma = 5
    
    # Trueであれば，スプレッドに対してロングポジションを持っている,つまりここでは，平衡よりも，CLが低く，ガソリンが高い状態なので，CLをロング，ガソリンをショートするという意味．
    context.currently_long_the_spread = False
    # Trueであれば，スプレッドに対してショートポジションを持っている．上参照
    context.currently_short_the_spread = False
    
    schedule_function(func=rebalance_pairs, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open(minutes=30))
    
    schedule_function(record_price,
                      date_rules.every_day(),
                      time_rules.market_open())
    
def rebalance_pairs(context, data):
    # equilibrium(平衡) から現在のスプレッドが離れているか計算
    zscore = calc_spread_zscore(context, data)
    # weightを計算
    target_weights = get_target_weight(context, data, zscore) 
    
    if target_weights:
        # TargetPortfolioWeights https://www.evernote.com/Home.action#b=177d468e-bf46-408c-8f29-97655b654be5&st=p&x=TargetPortfolioWeights&n=b9413a7e-db9e-4a8b-81c7-cb3929d925f2
        order_optimal_portfolio(
            opt.TargetPortfolioWeights(target_weights),
            constraints=[])
        
def calc_spread_zscore(context, data): 
    prices = data.history([context.crude_oil,
                           context.gasoline],
                          'price',
                          context.long_ma,
                          '1d')
    
    cl_price = prices[context.crude_oil]
    xb_price = prices[context.gasoline]
    
    cl_returns = cl_price.pct_change()[1:]
    xb_returns = xb_price.pct_change()[1:]
    
    # python のスライスを使うと，最後から数えれば，l[-5:]もl[1:][-5:]も同じ出力    
    # >>> l = [0,1,2,3,4,5,6,7,8,9]
    # >>> l
    # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    # >>> l[-5:]
    # [5, 6, 7, 8, 9]
    # >>> l[1:]
    # [1, 2, 3, 4, 5, 6, 7, 8, 9]
    # >>> l[1:][-5:]
    # [5, 6, 7, 8, 9]
    
    # spread 計算
    regression = sp.stats.linregress(
        xb_returns[-context.long_ma:], # -65: つまり，後ろから65番目以降
        cl_returns[-context.long_ma:],
        )
    # 傾きにxをかける事て，yからの差を出すことで．実際の傾きからどのくらい離れているかを，各点で出力
    spreads = cl_returns - (regression.slope * xb_returns)  # regression.slope 単回帰直線の傾き．
    
    # zscore 出力 !!!!!!!!これ多分間違いで，spreads[-context.short_ma：]にしなくては行けないのではないかと思う
    # print spreads[-context.short_ma]
    # print np.mean(spreads[-context.short_ma])
    zscore = (np.mean(spreads[-context.short_ma:]) - np.mean(spreads)) / np.std(spreads, ddof=1)
    print zscore
    
    return zscore 

def get_target_weight(context, data, zscore):
    cl_contract, xb_contract = data.current(
        [context.crude_oil, context.gasoline], 
        'contract'
        )
    
    target_weights = {}
    
    if context.currently_short_the_spread and zscore < 0.0: 
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0
        context.currently_long_the_spread = False
        context.currently_short_the_spread = False
        
    elif context.currently_long_the_spread and zscore > 0.0:
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0
        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore > -1.0 and (not context.currently_long_the_spread):
        target_weights[cl_contract] = 0.5
        target_weights[xb_contract] = -0.5
        context.currently_long_the_spread = True
        context.currently_short_the_spread = False

    elif zscore < 1.0 and (not context.currently_short_the_spread):
        target_weights[cl_contract] = -0.5
        target_weights[xb_contract] = 0.5
        context.currently_long_the_spread = False
        context.currently_short_the_spread = True
        
    return target_weights 

def record_price(context, data):
    crude_oil_price = data.current(context.crude_oil, 'price') 
    gasoline_price = data.current(context.gasoline, 'price') 
    record(Crude_Oil=crude_oil_price, Gasoline=gasoline_price*42)
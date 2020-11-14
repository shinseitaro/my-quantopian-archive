import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 
from zipline.utils.calendars import get_calendar

"""
カレンダースプレッドストラテジー
SoyBeansの２〜３限月と４〜５限月を比較して，取引する．
(context.future_symbol を変更すれば他の商品に変更できます．)

具体的には
(3限月/2限月) > 0 且つ (5限月/4限月) < 0 の場合，3限月をショート，５限月をロング
(3限月/2限月) < 0 且つ (5限月/4限月) > 0 の場合，5限月をショート，3限月をロング
それ以外は，ポジションを持たない

注意：
このストラテジーは取引の書き方を説明するものであり，戦略になんの根拠もありません．
"""
    
def initialize(context):
    
    # slippage モデル
    # set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    # set_slippage(slippage.FixedSlippage(spread=0))
    
    # auto_close_day まであと何日残っているかを計算するためのカレンダー
    context.futures_calendar = get_calendar('us_futures')
    
    # ３限月の残存期間を格納するための変数．
    context.distance = None
    
    # レバレッジ
    context.levarage = 1.0
    
    context.future_symbol = 'SY' # SoyBeans
    
    # continuous_future コントラクトオブジェクト．
    # このオブジェクトで，現在やヒストリカルの価格等にアクセスする．
    context.f_1 = continuous_future(context.future_symbol, offset=0, roll='calendar')
    context.f_2 = continuous_future(context.future_symbol, offset=1, roll='calendar')
    context.f_3 = continuous_future(context.future_symbol, offset=2, roll='calendar')
    context.f_4 = continuous_future(context.future_symbol, offset=3, roll='calendar')
    context.f_5 = continuous_future(context.future_symbol, offset=4, roll='calendar')
    
    context.near = context.f_3
    context.far = context.f_5
    
    context.near_price = None
    context.far_price = None
    
    context.near_short_far_long = False
    context.near_long_far_short = False
    
    # market_open() = 6:31 AM ET 
    # market_close() = 16:59 PM ET
    schedule_function(my_rebalance,
                      date_rules.every_day(),
                      time_rules.market_open())
    
    schedule_function(my_record,
                      date_rules.every_day(),
                      time_rules.market_open())

def get_entry_flag(context, data):
    
    # 最新価格を取得
    context.price = data.current([context.f_1, context.f_2, context.f_3, context.f_4, context.f_5],fields='price', )
    
    # f_2/f_1, f_3/f_2, f_4/f_3, f_5/f_4, の pct_change を出す
    contango = context.price.pct_change()
    
    context.near_price_contango = contango[context.near]
    context.far_price_contango = contango[context.far]
    
    # それぞれの 符号を取得
    sign_near = np.sign(context.near_price_contango)
    sign_far = np.sign(context.far_price_contango)
    
    log.info([context.near_price_contango, context.far_price_contango, sign_near != sign_far])
    
    # 符号と，符号が同じかどうかの boolean を返す
    return sign_near, sign_far, sign_near != sign_far 

def my_rebalance(context, data):
    ## 現在の期近と５限月のコントラクトを取得
    near = data.current(context.near, 'contract')
    far = data.current(context.far, 'contract')
    target_weights = {}
    sign_near, sign_far, entry_flag = get_entry_flag(context, data)

    # nearの満期まであと何日（営業日ベース）残っているか出力(ストラテジーには使っていない. )
    todays_date = get_datetime('US/Eastern')
    context.distance = context.futures_calendar.session_distance(todays_date, near.auto_close_date)
    log.info(context.distance)        
    #log.info(context.futures_calendar.session_distance(near.auto_close_date, far.auto_close_date))        
   
    # entry_flag がFalseのとき，もし，ポジションを持っている場合は，クローズ
    if not entry_flag:
        if context.near_short_far_long or context.near_long_far_short:
            context.near_short_far_long = False 
            context.near_long_far_short = False
            target_weights[near] = 0.0
            target_weights[far] = 0.0
            
    # entry_flag が True, つまり sign_nearとsign_farのフラグが逆の場合．
    else:
        # 2と3限月がコンタンゴ，４と５限月がバックワーデーション
        if sign_near > 0:
            target_weights[near] = 0.5 * context.levarage
            target_weights[far] = -0.5 * context.levarage
            context.near_short_far_long = True
            
            # if context.near_short_far_long:
            #     # 既にポジションを持っているので
            #     pass 
            # else: 
            #     target_weights[near] = 0.5
            #     target_weights[far] = -0.5
                
        else: # つまり sign_near < 0
            target_weights[near] = -0.5 * context.levarage
            target_weights[far] = 0.5 * context.levarage
            context.near_long_far_short = True 
            
            # if context.near_long_far_short:
            #     pass 
            # else:
            #     target_weights[near] = -0.5
            #     target_weights[far] = 0.5

    if target_weights:
        order_optimal_portfolio(
            objective=opt.TargetWeights(target_weights),
            constraints=[
                opt.MaxGrossExposure(context.levarage)
            ]
        )     
    
def my_record(context, data):
    record(#distance = context.distance,
          near_price_congango=context.near_price_contango,
          far_price_congango=context.far_price_contango)
import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 
from zipline.utils.calendars import get_calendar

"""
カレンダースプレッドストラテジー
どりらーさんの note を元につくっています．
ターゲットが1-2限月

"""

def initialize(context):
    future = 'SY'
    context.future_symbol = 'SY' # SoyBeans
    
    # continuous_future コントラクトオブジェクト．
    # このオブジェクトで，現在やヒストリカルの価格等にアクセスする．
    context.f1 = continuous_future(context.future_symbol, offset=0, roll='calendar')
    context.f2 = continuous_future(context.future_symbol, offset=1, roll='calendar')
    context.f3 = continuous_future(context.future_symbol, offset=2, roll='calendar')
    context.f4 = continuous_future(context.future_symbol, offset=3, roll='calendar')
    context.f5 = continuous_future(context.future_symbol, offset=4, roll='calendar')
    
    # 1-2限月と比較する限月
    context.fx = context.f4 #x＝near
    context.fy = context.f5 #y=far
    
    context.x_short_y_long = False
    context.x_long_y_short = False 
    
    # レバレッジ
    context.levarage = 1.0
    
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
    context.price = data.current([context.f1, context.f2, context.f3, context.f4, context.f5],fields='price')
    context.f1_f2 = context.price[context.f2] / context.price[context.f1] - 1 
    context.fx_fy = context.price[context.fy] / context.price[context.fx] - 1 
    sign_f1_f2 = np.sign(context.f1_f2)
    sign_fx_fy = np.sign(context.fx_fy)
    
    return sign_f1_f2, sign_fx_fy, sign_f1_f2==sign_fx_fy

def my_rebalance(context, data): 
    fx_contract = data.current(context.fx, 'contract')
    fy_contract = data.current(context.fy, 'contract')
    
    target_weights = {}
    sign_f1_f2, sign_fx_fy, entry_flag= get_entry_flag(context, data)
    
    if entry_flag: # 符号が同じなのでトレードしない．
        context.x_short_y_long = False
        context.x_long_y_short = False 
        order_target(fx_contract, 0)
        order_target(fy_contract, 0)
        
    else:
        if sign_fx_fy > 0:
            context.x_long_y_short = True 
            order_target(fx_contract, 1)
            order_target(fy_contract, -1)

            
        else: # sign_fx_fy < 0
            context.x_short_y_long = True
            order_target(fx_contract, -1)
            order_target(fy_contract, 1)
            
            
def my_record(context, data):
    record(f1_2=context.f1_f2,fx_y=context.fx_fy )
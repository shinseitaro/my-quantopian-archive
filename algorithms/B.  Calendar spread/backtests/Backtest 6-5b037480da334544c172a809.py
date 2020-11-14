import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 

from zipline.utils.calendars import get_calendar
    
def initialize(context):
    # SoyBeans
    context.future_symbol = 'SY'
    context.f_1 = continuous_future(context.future_symbol, offset=0, roll='calendar')
    context.f_2 = continuous_future(context.future_symbol, offset=1, roll='calendar')
    context.f_3 = continuous_future(context.future_symbol, offset=2, roll='calendar')
    context.f_4 = continuous_future(context.future_symbol, offset=3, roll='calendar')
    context.f_5 = continuous_future(context.future_symbol, offset=4, roll='calendar')
    
    context.near_short_far_long = False
    context.near_long_far_short = False

    
    schedule_function(get_entry_flag,
                      date_rules.every_day(),
                      time_rules.market_open()
                     )
    schedule_function(my_rebalance,
                     date_rules.every_day(),
                      time_rules.market_open())
    
    schedule_function(my_record,
                      date_rules.every_day(),
                      time_rules.market_open())

def get_entry_flag(context, data):

    context.price = data.current(
        [context.f_1, context.f_2, context.f_3, context.f_4, context.f_5],
        fields='price', )
    contango = context.price.pct_change()
    sign3 = np.sign(contango[context.f_3])
    sign5 = np.sign(contango[context.f_5])
    
    # context.f_3_price = hist[context.context.f_3]
    # context.f_5_price = hist[context.context.f_5]
    # regression = sp.stats.linregress(range(0,4), hist.pct_change()[1:])
    # log.info(regression.slope)
    # hist_change = hist.pct_change()
    # ## f3とf5のサインを確認して返す
    # sign3 = np.sign(hist_change[context.f_3].iloc[-1])
    # sign5 = np.sign(hist_change[context.f_5].iloc[-1])
    
    log.info([contango[context.f_3], contango[context.f_5], sign3 != sign5])
    
    return sign3, sign5, sign3 != sign5
    

def my_rebalance(context, data):
    ## 現在の期近と５限月のコントラクトを取得
    f3_contract = data.current(context.f_3, 'contract')
    f5_contract = data.current(context.f_5, 'contract')
    target_weights = {}
    
    sign3, sign5, entry_flag = get_entry_flag(context, data)
    
   
    # entry_flag がFalseのとき，もし，ポジションを持っている場合は，クローズ
    if not entry_flag:
        if context.near_short_far_long or context.near_long_far_short:
            context.near_short_far_long = False 
            context.near_long_far_short = False
            target_weights[f3_contract] = 0.0
            target_weights[f5_contract] = 0.0
            
    else:
        # 2と3限月がコンタンゴ，４と５限月がバックワーデーション
        if sign3 > 0:
            if context.near_short_far_long:
                # 既にポジションを持っているので
                pass 
            else: 
                target_weights[f3_contract] = 0.5
                target_weights[f5_contract] = -0.5
                
        else: # つまりsign3 < 0
            if context.near_long_far_short:
                pass 
            else:
                target_weights[f3_contract] = -0.5
                target_weights[f5_contract] = 0.5

    if target_weights:
        order_optimal_portfolio(objective=opt.TargetWeights(target_weights),
                                constraints=[])     
    
#     if context.my_slope > context.target_slope:
#         if not context.short_spread:
#             context.short_spread = True
#             target_weights[sy_1_contract] = 0.5
#             target_weights[sy_5_contract] = -0.5
#         else:
#             pass 
#     elif context.my_slope < -context.target_slope:
#         if not context.long_spread:
#             context.long_spread = True
#             target_weights[sy_1_contract] = -0.5
#             target_weights[sy_5_contract] = 0.5
#         else:
#             pass 
#     elif context.short_spread or context.long_spread:
#         if (-0.005 < context.my_slope) and (context.my_slope < 0.005):
#             context.short_spread = False 
#             context.long_spread = False
#             target_weights[sy_1_contract] = 0.0
#             target_weights[sy_5_contract] = 0.0
    
#     log.info(context.short_spread)
#     #log.info("context.long_spread:", context.long_spread)
    
#     if target_weights:
#         order_optimal_portfolio(objective=opt.TargetWeights(target_weights),
#                                 constraints=[])
        
    
def my_record(context, data):
    record(f3 = context.price[context.f_3],
           f5 = context.price[context.f_5],
          )
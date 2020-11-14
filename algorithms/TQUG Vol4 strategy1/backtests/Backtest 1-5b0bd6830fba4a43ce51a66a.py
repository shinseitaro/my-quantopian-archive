"""
Tokyo Quantopian User Group handson Vol1 
アルゴリズムその１：単純な先物ロング
"""

import numpy as np
import scipy as sp 
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt 
from zipline.utils.calendars import get_calendar

def initialize(context):
    """
    context: Python の 辞書オブジェクトを拡張したオブジェクト．
    backtestを実行している間，プログラムの状態を保持．
    
    Quantopian では，context の属性として値をセットすることで値を保持します．
    """
    ## 原油２０１７年１月限 (10/01/2016~12/20/2016)
    context.my_future = future_symbol("CLF17")
    schedule_function(my_rebalance, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(hours=1))

def my_rebalance(context, data):
    """
    過去2日間の価格を取得して，前日比マイナスであればショート
    """
    
    cl_price = data.history(context.my_future, 
                            fields ='price', 
                            bar_count = 2, 
                            frequency = '1d')
    
    log.info(cl_price.pct_change()[1])
    
    if cl_price.pct_change()[1] < 0: 
        log.info("order short %s" % cl_price.pct_change()[1])
        #order_value(context.my_future, -1) 
        order_target_percent(context.my_future, -1) 
    else:
        order_value(context.my_future, 0) 
        
        
        
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
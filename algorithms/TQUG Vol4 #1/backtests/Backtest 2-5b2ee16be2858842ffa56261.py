"""
Tokyo Quantopian User Group handson Vol1 
アルゴリズムその2：単純な先物の取引
continuous_future つなぎ足 を使って取引
"""

def initialize(context):
    # 原油期近つなぎ足
    context.my_future = continuous_future('CL', 
                                          offset=0, # 限月．期近＝0，2番限＝1，3番限=2，・・・
                                          roll='calendar', # ロールするタイミング
                                          adjustment='mul' # アジャスト方法
                                         )
    schedule_function(my_rebalance, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(hours=1))
    
    log.info(context.my_future.to_dict())
    

def my_rebalance(context, data):
    """
    過去2日間の価格を取得して，前日比マイナスであればショート
    """
    cl_price = data.history(context.my_future, 
                            fields ='price', 
                            bar_count = 2, 
                            frequency = '1d')
    
    # コントラクト
    cl_contract = data.current(context.my_future, 'contract')
    log.info(cl_price.pct_change()[1])
    
    if cl_price.pct_change()[1] < 0: 
        log.info("order short %s" % cl_price.pct_change()[1])
        order_target_percent(cl_contract, -1) 
        
    else:
        order_value(cl_contract, 0)
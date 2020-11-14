"""
Tokyo Quantopian User Group handson Vol4
基本編
"""

def initialize(context):
    
    ## 原油２０１７年１月限 (10/01/2016~12/20/2016)
    # context.my_future = future_symbol("CLF17")
    # 原油期近つなぎ足
    context.my_future = continuous_future('CL', 
                                          offset=0, # 限月．期近＝0，2番限＝1，3番限=2，・・・
                                          roll='calendar', # ロールするタイミング
                                          adjustment='mul' # アジャスト方法
                                         )
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
    # コントラクト
    cl_contract = data.current(context.my_future, 'contract')
    current_price = data.current(cl_contract, 'price') 
    
    log.info(current_price)
    
    if cl_price.pct_change()[1] < 0: 
        log.info("order short %s" % cl_price.pct_change()[1])
        order_target(cl_contract, -1)
    elif cl_price.pct_change()[1] > 0: 
        log.info("order short %s" % cl_price.pct_change()[1])
        order_target(cl_contract, 1)
    else:
        order_target(cl_contract, 0)
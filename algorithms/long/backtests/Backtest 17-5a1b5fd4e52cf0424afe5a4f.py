def initialize(context):
    # PM を取引対象に設定
    context.my_security = sid(35902)
    # 取引株数を設定
    context.noofstocks = 10
    
    # スケジュール
    schedule_function(my_order, date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open())
    
    
def handle_data(context, data):
    # 毎分実行される
    pass 
    
def before_trading_start(context, data):
    # 毎朝，08：45に実行
    pass 

def my_order(context, data): 
    if data.can_trade(context.my_security): 
        order_value(context.my_security, 
                    10000)
        
        
    
                      
    
    
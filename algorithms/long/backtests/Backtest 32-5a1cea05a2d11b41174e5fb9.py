def initialize(context):
    # PM を取引対象に設定
    context.my_security = sid(35902)
    context.ratio = 1.0
    # 取引株数を設定
    context.noofstocks = 1000
    context.my_target = 0.1 
    context.my_flag = False 
    
    
    # スケジュール
    schedule_function(my_order, date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_open())
    
    
def handle_data(context, data):
    # 毎分実行される
    pass 
    
def before_trading_start(context, data):
    # 毎朝，08：45に実行
    # ログを出力してみましょう
    
    # 外で使わない変数なので
    cost_basis = context.portfolio.positions[context.my_security].cost_basis
    last_sale_price = context.portfolio.positions[context.my_security].last_sale_price
    if 0 not in [cost_basis, last_sale_price]:
        log.info("%s, %s, %s" % (cost_basis, last_sale_price,  last_sale_price / cost_basis - 1))
        if  last_sale_price / cost_basis - 1 > context.my_target :
            context.my_flag = True 
        
def my_order(context, data): 
    # if context.my_flag:
    #     log.info("We've won 10%+ yeeeaaaahhh") 
    #     order_target(context.my_security, 0) 
    #     context.my_flag = False 
        
    # if data.can_trade(context.my_security): 
    #     order_target(context.my_security, 
    #                   100)
    if data.can_trade(sid(24)):
        order_target_percent(sid(24), 1)
    if data.can_trade(sid(46631)):
        order_target_percent(sid(46631), -1)
        
        
    
                      
    
    
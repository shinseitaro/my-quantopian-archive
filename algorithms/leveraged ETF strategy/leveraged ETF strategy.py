 
def initialize(context):
    context.labd = sid(49072)
    context.threshold = 0.10

    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close(minutes=15))
    schedule_function(my_close, date_rules.every_day(), time_rules.market_close())
    

def lastprice_to_1545(context, data):
    yeseterday_close = data.history(context.labd, 'price', 2, '1d')[-2]
    current_price = data.current(context.labd, 'price')
    context.diff =  current_price / yeseterday_close - 1
    

def my_rebalance(context,data):
    lastprice_to_1545(context, data)
    print context.diff
    
    if context.diff >= context.threshold:
        order_percent(context.labd, 0.9)
    elif context.diff <= context.threshold * -1:
        order_percent(context.labd, -0.9)
    else:
        pass 

def my_close(context, data):
    order_target(context.labd, 0)
    

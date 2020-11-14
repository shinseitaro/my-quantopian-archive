import quantopian.algorithm as algo

def initialize(context):
    context.x = sid(14516)
    context.y = sid(14529)
    context.term = 90
    context.threshold = 5

    
    # 取引終了時にリバランス
    algo.schedule_function(
        rebalance,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(),
    )
    algo.schedule_function(
        record_vars,
        algo.date_rules.every_day(),
        algo.time_rules.market_close(),
    )

    
def rebalance(context, data):
    pricex = data.history(context.x, fields="price", bar_count=context.term, frequency="1d")
    pricey = data.history(context.y, fields="price", bar_count=context.term, frequency="1d")
    pricex_mean = pricex.mean() 
    pricey_mean = pricey.mean() 
    
    beta = pricex_mean / pricey_mean
    context.spread = pricex[-1] - pricey[-1] * beta 
    
    if (-context.threshold <= context.spread) and (context.spread <= context.threshold):
        order_target(context.x, 0)
        order_target(context.y, 0)
        
    elif context.spread > context.threshold:
        if data.can_trade(context.x) and data.can_trade(context.y):
            order_percent(context.x, -0.5)
            order_percent(context.y, 0.5)
    elif context.spread < -context.threshold:
        if data.can_trade(context.x) and data.can_trade(context.y):
            order_percent(context.x, 0.5)
            order_percent(context.y, -0.5)
            
    else:
        pass 
    
def record_vars(context, data):
    record(spread=context.spread)


def handle_data(context, data):
    pass
def initialize (context):
    context.aapl = sid(24)
    set_benchmark(sid(46631))
    schedule_function(ma_crossover, date_rules.every_day(), time_rules.market_open(hours=1))
    
def ma_crossover(context,data):  

    hist = data.history(context.aapl, 'price', 50, '1d')
    #log.info(hist.head())
    sma_50 = hist.mean()
    sma_20 = hist[-20:].mean()
    
    open_orders = get_open_orders()
    
    if sma_20 > sma_50:
        if context.aapl not in open_orders:
            order_target_percent(context.aapl, 1.0)
    elif sma_20 < sma_50:
        if context.aapl not in open_orders:
            order_target_percent(context.aapl, -1.0)
       
    record(leverage=context.account.leverage)    
    
def handle_data(context, data):
    pass
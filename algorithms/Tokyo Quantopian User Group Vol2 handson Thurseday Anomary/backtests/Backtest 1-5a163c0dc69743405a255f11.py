def initialize(context):
    """
    
    """   
    #
    
    context.amzn = sid(16841)
    set_benchmark(context.amzn)
    ## if monday is holiday, this is incorrect. 
    schedule_function(my_wednesday_trade, date_rules.week_start(days_offset=2), time_rules.market_close())
    schedule_function(my_thurseday_trade, date_rules.week_start(days_offset=3), time_rules.market_close())
    
    schedule_function(my_log, date_rules.week_start(days_offset=2), time_rules.market_close())
         

def before_trading_start(context, data):
    pass 

def handle_data(context,data):
    pass 

def my_wednesday_trade(context, data):
    if data.can_trade(context.amzn):
        order_percent(context.amzn, 0.5)
    else:
        log.info("cannot trade")
        
def my_thurseday_trade(context, data):
    log.info("Close")
    if data.can_trade(context.amzn):
        order_target(context.amzn, 0)

def my_log(context, data): 
    log.info("Hold Amount {0} stocks.  {1}".format(context.portfolio.positions[context.amzn].amount,
                                                  context.portfolio.positions[context.amzn].amount * 
                                                   context.portfolio.positions[context.amzn].cost_basis
                                                 ))
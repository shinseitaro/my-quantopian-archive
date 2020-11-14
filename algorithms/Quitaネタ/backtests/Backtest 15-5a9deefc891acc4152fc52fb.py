def initialize(context):
    context.security = sid(24)
    schedule_function(rebalance, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(minutes = 1))

def rebalance(context, data):
    price_history = data.history(
        context.security,
        fields='price',
        bar_count=5,
        frequency='1d'
    )
    average_price = price_history.mean()
    current_price = data.current(context.security, 'price') 
    if data.can_trade(context.security):
        if current_price > (1.01 * average_price):
            
            order_target_percent(context.security, 1)
            log.info("Buying %s" % (context.security.symbol))
    
    record(current_price=current_price, average_price=average_price)
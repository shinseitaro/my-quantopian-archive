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
            # 成り行きで現在のポートフォリオ価格に対して100％分のアップル株を買う
            order_target(context.security, 100)
            log.info("Buying %s" % (context.security.symbol))
        elif current_price < average_price:
            order(context.security, 0)
            log.info("Selling %s" % (context.security.symbol))
    
    record(current_price=current_price, average_price=average_price)
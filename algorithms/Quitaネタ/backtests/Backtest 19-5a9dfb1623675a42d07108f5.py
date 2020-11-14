def initialize(context):
    context.security = sid(35902)
    schedule_function(rebalance, 
                      date_rule=date_rules.every_day(),
                      time_rule=time_rules.market_close(minutes = 1))

def rebalance(context, data):
    current_price = data.current(context.security, 'price') 
    if data.can_trade(context.security):
            order_target_percent(context.security, 1)
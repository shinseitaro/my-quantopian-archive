def initialize(context):
    context.aapl = sid(24)
    context.spy = sid(8554)

def before_trading_start(context, data):
    pass

def handle_data(context, data):
    if data.can_trade(context.aapl):
        order_target_percent(context.aapl, 0.5)
        
    if data.can_trade(context.spy):
        order_target_percent(context.spy, -0.5)
        
        

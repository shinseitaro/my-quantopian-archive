def initialize(context):
    context.message = "hello"


def before_trading_start(context, data):
    pass

def handle_data(context, data):
    print context.message

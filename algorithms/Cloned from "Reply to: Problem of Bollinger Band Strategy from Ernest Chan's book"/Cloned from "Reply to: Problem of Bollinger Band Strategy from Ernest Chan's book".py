# Put any initialization logic here.  The context object will be passed to
# the other methods in your algorithm.

import pandas as pd
import numpy as np
import statsmodels.api as sm

def initialize(context):
    context.stocks = [sid(28320), sid(26807)]
    context.lookback = 20
    context.entry_zscore = 1
    context.exit_zscore = 0
    context.port_values = []

    
def get_hedge_ratio(context, data):
    prices = history(bar_count = 20, frequency = '1d', field = 'price')
    price1 = prices[context.stocks[0]].values
    price2 = sm.add_constant(prices[context.stocks[1]].values)
    hedge_ratio = sm.OLS(price1, price2).fit().params[1]
    return hedge_ratio

# Will be called on every trade event for the securities you specify. 
def handle_data(context, data):
    # Implement your algorithm logic here.
    hedge_ratio = get_hedge_ratio(context, data)
    symbol1 = context.stocks[0]
    symbol2 = context.stocks[1]
    port_value = data[symbol1].price - hedge_ratio * data[symbol2].price
    context.port_values.append(port_value)
    
    if len(context.port_values) > context.lookback:
        mean = np.mean(context.port_values[-context.lookback:])
        std = np.std(context.port_values[-context.lookback:])
        zscore = (port_value - mean) / std
        
        longsEntry =  zscore < -context.entry_zscore
        longsExit = zscore >= -context.exit_zscore
        shortsEntry = zscore > context.entry_zscore
        shortsExit = zscore <= context.exit_zscore
    
        log.info(zscore)
        if longsExit and context.portfolio.positions[symbol1].amount > 0:
            order_target(symbol1, 0)
            order_target(symbol2, 0)
            msg = 'longsExit: exit USO at {px}, GLD at {py}'
            log.info(msg.format(px = data[symbol1].price, py = data[symbol2].price))
    
        if shortsExit and context.portfolio.positions[symbol1].amount < 0:
            order_target(symbol1, 0)
            order_target(symbol2, 0)
            msg = 'shortsExit: exit USO at {px}, GLD at {py}'
            log.info(msg.format(px = data[symbol1].price, py = data[symbol2].price))
        
        if longsEntry and context.portfolio.positions[symbol1].amount == 0:
            order(symbol1, +100)
            order(symbol2, -100 * hedge_ratio)
            msg = 'longsEntry: buy {x} shares USO at {px}, {y} shares GLD at {py}'
            log.info(msg.format(x = 100, px = data[symbol1].price, y = -100 * hedge_ratio, py = data[symbol2].price))
    
        if shortsEntry and context.portfolio.positions[symbol1].amount == 0:
            order(symbol1, -100)
            order(symbol2, +100 * hedge_ratio)
            msg = 'shortsEntry: buy {x} shares USO at {px}, {y} shares GLD at {py}'
            log.info(msg.format(x = -100, px = data[symbol1].price, y = 100 * hedge_ratio, py = data[symbol2].price))
    

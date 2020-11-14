import pandas as pd
import numpy as np
import statsmodels.api as sm 

def initialize(context):
    context.uso = sid(28320)
    context.gld = sid(26807)
    context.stocks = [context.uso, context.gld]
    context.lookback = 20
    context.entry_zscore = 1
    context.exit_zcore = 0 
    context.port_values = []
    schedule_function(rebalance, date_rule=date_rules.every_day(),time_rule=time_rules.market_close())
    
    
def get_hedge_ratio(context, data):
    # USOとGLDの過去二十日間の最小二乗法で傾きを取得
    prices = data.history(context.stocks, fields='price', bar_count=20, frequency='1d')
    price1 = prices[context.uso].values
    price2 = sm.add_constant(prices[context.gld].values)
    hedge_ratio = sm.OLS(price1, price2).fit().params[1]
    return hedge_ratio 

def before_trading_start(context, data):
    
    for x in context.portfolio.positions:  
        posi = context.portfolio.positions[x]
        msg = 'position: {symbol}, {amount}, {cost_basis}, {allamount}'
        log.info(msg.format(symbol=posi.sid.symbol,
                            amount=posi.amount,
                            cost_basis=posi.cost_basis,
                            allamount=posi.amount*posi.cost_basis ))
                 

                
def rebalance(context, data):
    # 取得した傾きをGLDにかけて，期待値よりもどのくらい外れているかを port_value に格納
    hedge_ratio = get_hedge_ratio(context, data)
    port_value = data.current(context.uso, 'price')- hedge_ratio * data.current(context.gld, 'price')
    context.port_values.append(port_value)
    
    # 期待値よりもGLDがどのくらい外れているか，それを過去20日分集めて，zscoreを出す．
    if len(context.port_values) > context.lookback:
        mean = np.mean(context.port_values[-context.lookback:])
        std =  np.std(context.port_values[-context.lookback:])
        zscore = (port_value - mean) / std
        
        #-1 < zscore < 1 であればNo Position
        #zscore < -1 であれば，Long Spread（Long USO, Short GLD) 
        #1 < zscore であれば，Short Spread（Long GLD, Short USO) 
        longsEntry = zscore < -context.entry_zscore
        longsExit = zscore >= -context.entry_zscore
        shortsEntry = zscore > context.entry_zscore 
        shortsExit = zscore <= context.entry_zscore 
        
        log.info(zscore)
        
        if longsExit and context.portfolio.positions[context.uso].amount > 0:
            order_target(context.uso, 0) 
            order_target(context.gld, 0) 
            msg = 'long Exit: USO at {px}, GLD at {py}'
            log.info(msg .format(px = data.current(context.uso, 'price'), 
                                 py = data.current(context.gld, 'price'), ))
            
        if shortsExit and context.portfolio.positions[context.uso].amount < 0:
            order_target(context.uso, 0) 
            order_target(context.gld, 0) 
            msg = 'short Exit: USO at {px}, GLD at {py}'
            log.info(msg .format(px = data.current(context.uso, 'price'), 
                                 py = data.current(context.gld, 'price')))
        if longsEntry and context.portfolio.positions[context.uso].amount == 0:
            order_target_percent(context.uso, 0.5)
            order_target_percent(context.gld, -0.5)
            # order_target_percent(context.gld, -0.5 * hedge_ratio)            
           
            msg = 'longsExntry: buy {x} USO at {px}, sell {y} GLD at {yx}'
            log.info(msg.format(x = 0.5, px = data.current(context.uso, 'price'),
                                y = -0.5, yx = data.current(context.gld, 'price')))
        if shortsEntry and context.portfolio.positions[context.uso].amount == 0:
            order_target_percent(context.uso, -0.5)
            order_target_percent(context.gld, 0.5)
            # order_target_percent(context.gld, 0.5 * hedge_ratio)            
            msg = 'shortsExntry: sell {x} USO at {px}, buy {y} GLD at {yx}'
            log.info(msg.format(x = 0.5, px = data.current(context.uso, 'price'),
                                y = -0.5, yx = data.current(context.gld, 'price')))
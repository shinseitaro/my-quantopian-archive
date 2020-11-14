def initialize(context):

    context.sym1 = sid(28320)
    context.sym2 = sid(26807)
    context.term = 20
    context.zscore_thres = 2
    context.zscore_prevday = None 
    context.hold = 0
    
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close())
 
def before_trading_start(context, data):
    pass 

def get_zscore(context, df):
    ratio = df[context.sym1] / df[context.sym2]
    mean = ratio.mean()
    std =  ratio.std()
    zscore = (ratio[-1] - mean) / std 
    print(ratio[-1], mean, zscore)
    return ratio[-1], mean, zscore 

def my_rebalance(context,data):
    
    df = data.history([context.sym1, context.sym2], fields="price", bar_count=context.term + 1, frequency="1d")
    
    ratio, mean, zscore = get_zscore(context, df.iloc[1:])
    ratio_prev, mean_prev, zscore_prev = get_zscore(context, df.iloc[:-1])
    
    log.info(zscore)
    log.info(zscore_prev)
    
    # upper_flag = zscore > context.zscore_thres
    # lower_flag = zscore < -context.zscore_thres
    upper_flag = zscore < zscore_prev and zscore_prev > context.zscore_thres
    lower_flag = zscore > zscore_prev and zscore_prev < -context.zscore_thres
    if sorted([ ratio_prev, mean, ratio])[1] == mean:
        order_target(context.sym1, 0) 
        order_target(context.sym2, 0)     
    
    if upper_flag + lower_flag == 0:
        context.hold +=1 
        # order_target(context.ewa, 0) 
        # order_target(context.ewc, 0) 
        
    elif upper_flag:
        context.hold = 0
        ## EWA short / EWC long
        order_target_percent(context.sym1, -0.5)
        order_target_percent(context.sym2, 0.5)
    elif lower_flag:
        context.hold = 0
        order_target_percent(context.sym1, 0.5)
        order_target_percent(context.sym2, -0.5)
        
    record( hold=context.hold)
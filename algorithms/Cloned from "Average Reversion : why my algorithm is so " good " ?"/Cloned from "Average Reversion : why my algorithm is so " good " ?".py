def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    # Rebalance every day, 1 hour 30 min after market open.
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
     
    # Record tracking variables at the end of each day.
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    # The choosen equities (apple, microsoft,tesla, pharmaceutical company)
    context.security_list=[sid(24),sid(5061),sid(39840)]
    
   
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    hist=data.history(context.security_list,'price',30,'1d')
    average7=hist[-7:].mean()
    average30=hist.mean()
    
    ecart_relat=((average7 - average30)/average30)
    poids=ecart_relat/ecart_relat.abs().sum()
    return(poids)
    
 
def my_rebalance(context,data):
    """
    Execute orders according to our schedule_function() timing. 
    """
    poids=my_assign_weights(context,data)
    
    for securities in context.security_list :
        if data.can_trade(securities) and poids[securities]*100>=20:
            order_target_percent(securities,poids[securities])
 
        elif abs(poids[securities])*100<=20 and data.can_trade(securities) and (securities in context.portfolio.positions):
            #If the weight is not enough strong than we cut the current position
            order_target_percent(securities,0)
            print("ok")
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    (longs,shorts)=(0,0)
    for position in context.portfolio.positions.itervalues():
        if position.amount > 0:
            longs += 1
        elif position.amount < 0:
            shorts += 1

    # Record our variables.
    record(leverage=context.account.leverage, long_count=longs, short_count=shorts)
 


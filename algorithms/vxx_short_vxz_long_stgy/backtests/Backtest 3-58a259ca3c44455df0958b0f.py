def initialize(context):
    # instance data for vxx and vxz
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.bought = False
    
    schedule_function(rebalance, 
                      date_rules.every_day(),
                      time_rules.market_close())
    
    schedule_function(record_vars, 
                      date_rules.every_day(),
                      time_rules.market_close())
    
def rebalance(context, data):
    if not context.bought:
        log.info('long vxz')
        order_percent(context.vxz, 0.5)
        log.info('short vxx')
        order_percent(context.vxx, -0.5)
        context.bought = True
        
        
def record_vars(context, data):
    record(vxx = data.current(context.vxx, 'price'), 
           vxz = data.current(context.vxz, 'price'), )
    
    
    
    
    
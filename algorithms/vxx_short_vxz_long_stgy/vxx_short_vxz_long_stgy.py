"""
This algorithm is simple long short model of VXZ(long) and VXX (short)
The idea is that VXX, which is short term VIX ETF, tends to go back to normal quicker than VXZ, long term VIX ETF. Vix Contango of near futures is steeper than further futures. 

"""
def initialize(context):
    # instance data for vxx and vxz
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.bought = False
    
    # trade at closing time
    schedule_function(rebalance, 
                      date_rules.every_day(),
                      time_rules.market_close())
    
    # plot every day 
    schedule_function(record_vars, 
                      date_rules.every_day(),
                      time_rules.market_close())
    
def rebalance(context, data):
    # trade only on the first day.
    if not context.bought:
        log.info('long vxz')
        order_percent(context.vxz, 0.5)
        log.info('short vxx')
        order_percent(context.vxx, -0.5)
        context.bought = True
        
       
def record_vars(context, data):
    record(vxx = data.current(context.vxx, 'price'), 
           vxz = data.current(context.vxz, 'price'), )
    
    
    
    
    
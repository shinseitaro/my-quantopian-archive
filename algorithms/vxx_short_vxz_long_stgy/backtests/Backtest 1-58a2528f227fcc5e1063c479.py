def initialize(context):
    # instance data for vxx and vxz
    context.vxx = sid(38054)
    context.vxz = sid(38055)
    context.bought = False
    
def rebalance(context, data):
    if not context.bought:
        log.info('long vxz')
        order_percent(context.vxz, 0.5)
        log.info('short vxx')
        order_percent(context.vxx, -0.5)
        context.bought = True
        
        
    
    
    
    
    
    
"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
 
def initialize(context):
    context.vxx = sid(38054)
    context.hmm = None 
    context.order_id = None 
    
    fetch_csv("https://dl.dropboxusercontent.com/u/264353/hmm.csv",
             symbol='hmm', date_column='Date', date_format='%y-%m-%d')
    
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close())

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0:"Sun", 1:"Mon", 2:"Tue", 3:"Wed", 4:"Thu", 5:"Fri", 6:"Sat"}
    msgs = '%s\t%s:\t%s' % (dt, youbidict[int(youbi)], msgs)  
    log.info(msgs)
    
def before_trading_start(context, data):
    if context.order_id != None:
        positionvalue = get_order(context.order_id).amount * data.current(context.vxx, 'price')
        logging("Before trading Position: VXX %s\t%s" % (data.current(context.vxx, 'price'), positionvalue))
    else:
        logging("Before trading Position: VXX %s\t%s" % (data.current(context.vxx, 'price'), 0.0))
     
def my_rebalance(context,data):
    context.hmm = data.current('hmm', 'HMM')
    amount = context.portfolio.positions[context.vxx].amount
    if context.order_id != None:
        positionvalue = get_order(context.order_id).amount * data.current(context.vxx, 'price')
        
    threshold = 0.5
    
    if context.hmm >= threshold:
        if context.order_id == None:
            logging("Open VXX Short Position: HMM %s" % context.hmm) 
            context.order_id = order_value(context.vxx, -5000)
            amount = get_order(context.order_id).amount
            price = data.current(context.vxx, 'price')
            positionvalue = get_order(context.order_id).amount * data.current(context.vxx, 'price')
            
            logging('VXX Short Position Opened: %s @ %s' % (amount, price))
            logging("Hold VXX Short Position Values:\t%s" % positionvalue)
            
        else:
            logging("Hold VXX Short Position Shares:%s / Position Values:\t%s" % (amount, positionvalue))
            # logging("Hold VXX Short Position Shares:%s / pnl:\t%s" % (amount, context.portfolio.pnl))
    elif context.hmm < threshold:
        if  context.order_id != None:
            logging("VXX Short Position Closed Position Values:\t%s" % positionvalue)             
            order_percent(context.vxx, 0)
            
            context.order_id = None
        else:
            logging("No position No Life")
    
def my_record_vars(context, data):
    pass
 
def handle_data(context,data):
    record(hmm=data.current('hmm', 'HMM'))

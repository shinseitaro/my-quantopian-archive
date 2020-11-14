"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, CustomFactor, Returns
from quantopian.pipeline.filters import StaticAssets
from quantopian.pipeline.filters.morningstar import Q1500US 

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0:"Sun", 1:"Mon", 2:"Tue", 3:"Wed", 4:"Thu", 5:"Fri", 6:"Sat"}
    msgs = '\t%s\t%s:\t%s' % (dt.strftime('%Y/%m/%d %H:%M'), youbidict[int(youbi)], msgs) 
    log.info(msgs)

def initialize(context):
    """
    Called once at the start of the algorithm.
    """   
    context.vxx = sid(38054)
    context.tvix = sid(40515)
    context.xiv = sid(40516)
    context.forward = sid(8554)
    context.inverse = sid(32382)
    
    
    # Rebalance every day, 1 hour after market open.
    schedule_function(my_rebalance_open, date_rules.every_day(), time_rules.market_open(minutes=60))    
    
    schedule_function(my_rebalance_close, date_rules.every_day(), time_rules.market_close())

    
    set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    set_slippage(slippage.FixedSlippage(spread=0))
    # Record tracking variables at the end of each day.
    #schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
     
    # Create our dynamic stock selector.
    attach_pipeline(make_pipeline(), 'my_pipeline')

class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]
        
def make_pipeline():
    """
    A function to create our dynamic stock selector (pipeline). Documentation on
    pipeline can be found here: https://www.quantopian.com/help#pipeline-title
    """
    
    sids = StaticAssets(symbols('VXX', 'XIV', 'TVIX'))
    base_universe = sids 

    # Factor of yesterday's close price.
    yesterday_close = PrevClose()
    close_to_close = Returns(window_length=2)
    
    
    pipe = Pipeline(
        screen = base_universe,
        columns = {
            'yesterday_close': yesterday_close,
            'close_to_close': close_to_close, 
            
        }
    )
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
    context.go = False 
    if abs(context.output.ix[context.vxx]['close_to_close']) > 0.01:
        logging("VXX Return: %s" % context.output.ix[context.vxx]['close_to_close'] )
        context.go = True
  
    # These are the securities that we are interested in trading each day.
    #context.security_list = context.output.index
     
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def my_rebalance_close(context,data):
    if context.portfolio.positions[context.vxx]:
        if data.can_trade(context.vxx):
            order_target(context.vxx, 0)
    if context.portfolio.positions[context.xiv]:
        if data.can_trade(context.xiv):
            order_target(context.xiv, 0)
            
    if context.portfolio.positions[context.tvix]:
        if data.can_trade(context.tvix):
            order_target(context.tvix, 0)
            
def my_rebalance_open(context,data):

    if context.go and data.can_trade(context.vxx) and data.can_trade(context.tvix):
    #if data.can_trade(context.xiv) and data.can_trade(context.tvix):        
        order_percent(context.vxx, 0.6)
        order_percent(context.tvix,-0.3) 
        
        #order_percent(context.xiv,-0.6)         
        
 
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    track_orders(context, data)


def track_orders(context, data):  
    '''  Show orders when made and filled.  
           Info: https://www.quantopian.com/posts/track-orders  
    '''  
    c = context  
    if 'trac' not in c:  
        c.t_options = {           # __________    O P T I O N S    __________  
            'log_neg_cash': 1,    # Show cash only when negative.  
            'log_cash'    : 0,    # Show cash values in logging window or not.  
            'log_ids'     : 0,    # Include order id's in logging window or not.  
            'log_unfilled': 1,    # When orders are unfilled. (stop & limit excluded).  
        }    # Move these to initialize() for better efficiency.  
        c.trac = {}  
        c.t_dates  = {  # To not overwhelm the log window, start/stop dates can be entered.  
            'active': 0,  
            'start' : [],   # Start dates, option like ['2007-05-07', '2010-04-26']  
            'stop'  : []    # Stop  dates, option like ['2008-02-13', '2010-11-15']  
        }  
    from pytz import timezone     # Python only does once, makes this portable.  
                                  #   Move to top of algo for better efficiency.  
    # If 'start' or 'stop' lists have something in them, triggers ...  
    if c.t_dates['start'] or c.t_dates['stop']:  
        date = str(get_datetime().date())  
        if   date in c.t_dates['start']:    # See if there's a match to start  
            c.t_dates['active'] = 1  
        elif date in c.t_dates['stop']:     #   ... or to stop  
            c.t_dates['active'] = 0  
    else: c.t_dates['active'] = 1           # Set to active b/c no conditions.  
    if c.t_dates['active'] == 0: return     # Skip if not active.  
    def _minute():   # To preface each line with the minute of the day.  
        bar_dt = get_datetime().astimezone(timezone('US/Eastern'))  
        return str((bar_dt.hour * 60) + bar_dt.minute - 570).rjust(3) # (-570 = 9:31a)  
    def _trac(to_log):      # So all logging comes from the same line number,  
        log.info(to_log)    #   for vertical alignment in the logging window.

    for oid in c.trac.copy():               # Existing known orders  
      o = get_order(oid)  
      c.trac[o.id]['cb'] = c.portfolio.positions[o.sid].cost_basis if c.portfolio.positions[o.sid].cost_basis else c.trac[o.id]['cb']  
      if o.dt == o.created: continue        # No chance of fill yet.  
      cash = ''  
      if (c.t_options['log_neg_cash'] and c.portfolio.cash < 0) or c.t_options['log_cash']:  
        cash = 'cash {}'.format(int(c.portfolio.cash))  
      if o.status == 2:                     # Canceled  
        prc = '%.2f' % data.current(o.sid, 'price') if data.can_trade(o.sid) else 'unknwn'  
        do  = 'Buy' if o.amount > 0 else 'Sell' ; style = ''  
        if o.stop:  
          style = ' stop {}'.format(o.stop)  
          if o.limit: style = ' stop {} limit {}'.format(o.stop, o.limit)  
        elif o.limit: style = ' limit {}'.format(o.limit)  
        _trac(' {}     Canceled {} {} {}{} at {}   {}  {}'.format(_minute(), do, o.amount,  
           o.sid.symbol, style, prc, cash, o.id[-4:] if c.t_options['log_ids'] else ''))  
        del c.trac[o.id]  
      elif o.filled:                        # Filled at least some.  
        filled = '{}'.format(o.amount)  
        filled_amt = 0  
        if o.filled == o.amount:            # Complete  
          if 0 < c.trac[o.id]['amnt'] < o.amount:  
            filled   = 'all {}/{}'.format(o.filled - c.trac[o.id]['amnt'], o.amount)  
          filled_amt = o.filled  
        else:                               # ['amnt'] is previously filled total  
          filled_amt = o.filled - c.trac[o.id]['amnt']   # filled this time, can be 0  
          c.trac[o.id]['amnt'] = o.filled                # save for increments math  
          filled = '{}/{}'.format(filled_amt, o.amount)  
        if filled_amt:  
          prc = c.portfolio.positions[o.sid].last_sale_price if o.sid in c.portfolio.positions else 'unknwn'  
          prc = data.history(o.sid, 'price', 1, '1d')[-1] if prc is 'unknwn' else prc  
          now = ' ({})'.format(c.portfolio.positions[o.sid].amount) if c.portfolio.positions[o.sid].amount else ' _'  
          pnl = ''  # for the trade only  
          amt = c.portfolio.positions[o.sid].amount ; style = ''  
          if (amt - o.filled) * o.filled < 0:  # Profit-taking scenario including short-buyback  
            if c.trac[o.id]['cb']:  
              pnl  = -filled_amt * (prc - c.trac[o.id]['cb'])  
              sign = '+' if pnl > 0 else '-'  
              pnl  = '  ({}{})'.format(sign, '%.0f' % abs(pnl))  
          if o.stop:  
            style = ' stop {}'.format(o.stop)  
            if o.limit: style = ' stop () limit {}'.format(o.stop, o.limit)  
          elif o.limit: style = ' limit {}'.format(o.limit)  
          if o.filled == o.amount: del c.trac[o.id]  
          _trac(' {}      {} {} {}{} at {}{}{}'.format(_minute(),  
            'Bot' if o.amount > 0 else 'Sold', filled, o.sid.symbol, now,  
            '%.2f' % prc, pnl, style).ljust(52) + '  {}  {}'.format(cash, o.id[-4:] if c.t_options['log_ids'] else ''))  
      elif c.t_options['log_unfilled'] and not (o.stop or o.limit):  
        _trac(' {}         {} {}{} unfilled  {}'.format(_minute(), o.sid.symbol, o.amount,  
         ' limit' if o.limit else '', o.id[-4:] if c.t_options['log_ids'] else ''))

    oo = get_open_orders().values()  
    if not oo: return                       # Handle new orders  
    cash = ''  
    if (c.t_options['log_neg_cash'] and c.portfolio.cash < 0) or c.t_options['log_cash']:  
      cash = 'cash {}'.format(int(c.portfolio.cash))  
    for oo_list in oo:  
      for o in oo_list:  
        if o.id in c.trac: continue         # Only new orders beyond this point  
        prc  = '%.2f' % data.current(o.sid, 'price') if data.can_trade(o.sid) else 'unknwn'  
        c.trac[o.id] = {'amnt': 0, 'cb': 0} ; style = ''  
        now  = ' ({})'.format(c.portfolio.positions[o.sid].amount) if c.portfolio.positions[o.sid].amount else ' _'  
        if o.stop:  
          style = ' stop {}'.format(o.stop)  
          if o.limit: style = ' stop {} limit {}'.format(o.stop, o.limit)  
        elif o.limit: style = ' limit {}'.format(o.limit)  
        _trac(' {}   {} {} {}{} at {}{}'.format(_minute(), 'Buy' if o.amount > 0 else 'Sell',  
          o.amount, o.sid.symbol, now, prc, style).ljust(52) + '  {}  {}'.format(cash, o.id[-4:] if c.t_options['log_ids'] else ''))  

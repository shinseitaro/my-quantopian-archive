import quantopian.experimental.optimize as opt
import quantopian.algorithm as algo

import numpy as np
import pandas as pd
import math
 
def initialize(context):
    """
    Called once at the start of the algorithm.
    """
    # # Initializing the StopLoss-Manager
    #context.SL_Manager = StopLoss_Manager()    
    #schedule_function(context.SL_Manager.manage_orders, date_rules.every_day(), time_rules.market_open())

    
    # Save the futures contracts we'll be trading and the corresponding proxies for the underlying's spot price.
    context.ng1 = continuous_future("NG", offset=0, roll="calendar", adjustment=None)
    context.proxy = sid(33837)
    
    context.peak_port_val = 0.0
    context.max_dd = 0.0    
    context.last_dd = 0.0
    
    # Create empty keys that will later contain our window of cost of carry data.
    context.cost_of_carry_data = []
    context.cost_of_carry_quantiles = []
    
    # Rebalance every day, 1 hour after market open.
    algo.schedule_function(train_algorithm, date_rules.every_day(), time_rules.market_open(hours=1))
    algo.schedule_function(daily_rebalance, date_rules.every_day(), time_rules.market_open(hours=1))
    algo.schedule_function(record_vars, date_rules.every_day(), time_rules.market_open())
    
def train_algorithm(context, data):
    """
    Before executing any trades, we must collect at least 30 days of data. After this, keep sliding the 30 day window
    to remove the oldest data point while adding the newest point.
    """
    ng_contract = data.current(context.ng1, "contract")
    ng_etf = data.current(context.proxy, "price")
    
    if len(context.cost_of_carry_data) < 30:
        calc_cost_of_carry(context, data, ng_contract, ng_etf)
    else:
        calc_cost_of_carry(context, data, ng_contract, ng_etf)
        # After collecting 30 days worth of data, group the data points into 5 quantiles.
        context.cost_of_carry_quantiles = pd.qcut(context.cost_of_carry_data, 5, labels=False) + 1
        context.cost_of_carry_data.pop(0)
        context.cost_of_carry_quantiles_labels = pd.qcut(context.cost_of_carry_data, 5, retbins=True)[-1]
        
   #     print(1/context.cost_of_carry_quantiles_labels[0])

def daily_rebalance(context, data):
    """
    Execute orders according to our schedule_function() timing. 
    """
    
    weights = {}
    
    # After collecting 30 days worth of data, execute our ordering logic by buying low cost of carry contracts.
    contract = data.current(context.ng1, "contract")
    
    stop = (1-.025)*data.history(contract, 'price', 1, '1m')[0]  
    
 #   open_orders = get_open_orders()  
    
    if len(context.cost_of_carry_data) >= 30:
        if len(context.cost_of_carry_quantiles) >= 30:
            if context.cost_of_carry_quantiles[-1] >= 5 and (contract.expiration_date - get_datetime()).days > 19:
#                cancel_order(order for order in open_orders)
                order_target_percent(contract, -1)
#                order_target_percent(contract, 1* percent, style=StopOrder(stop))
            elif context.cost_of_carry_quantiles[-1] <= 1 and (contract.expiration_date - get_datetime()).days > 19:
 #               cancel_order(order for order in open_orders)
                order_target_percent(contract, 1)
#                order_target_percent(contract, -1* percent, style=StopOrder(stop))                  
    
    for security in context.portfolio.positions:         
        if (contract.expiration_date - get_datetime()).days <= 19:
 #           cancel_order(order for order in open_orders)
            order_target_percent(contract, 0)
    

    

def record_vars(context, data):
    """
    This function is called at the end of each day and plots
    the number of long and short positions we are holding.
    """
    contract = data.current(context.ng1, "contract")
    # Check how many long and short positions we have.
    longs = shorts = 0
    for position in context.portfolio.positions.itervalues():
        if position.amount > 0:
            longs += 1
        elif position.amount < 0:
            shorts += 1

    # Record our variables.
    record(long_count=longs*.1, short_count=shorts*.1)
    record(current_drawdown=drawdown(context,data))
    
    
    if context.account.leverage == 0:
        context.last_dd = drawdown(context,data)
    
def calc_cost_of_carry(context, data, contract, spot_price):
    """
    Calculate cost of carry using the following formula:
        F(t, T) = S(t) * e^c(T - t)
    where F(t, T) is the futures price at time t for maturity date T, S(t) is the spot price at time t, and c is
    the cost of carry.
    """
    current_date = get_datetime()
    current_price = data.current(contract, "price")
    maturity_date = contract.expiration_date
    spot_price = spot_price
    cost_of_carry = np.log(current_price / spot_price) / (maturity_date - current_date).days
    context.cost_of_carry_data.append(cost_of_carry)
    
    
def drawdown(context, data):
    port_val = context.portfolio.portfolio_value
    dd = 0.0
    if (port_val > context.peak_port_val):
        dd = 0.0
        context.peak_port_val = port_val
    else:
        dd = 1.0 - port_val / context.peak_port_val 
        context.max_dd = max(dd, context.max_dd)
    return dd

class StopLoss_Manager:
    """
    Class to manage to stop-orders for any open position or open (non-stop)-order. This will be done for long- and short-positions.
    
    Parameters:  
        pct_init (optional),
        pct_trail (optional),
        (a detailed description can be found in the set_params function)
              
    Example Usage:
        context.SL = StopLoss_Manager(pct_init=0.005, pct_trail=0.03)
        context.SL.manage_orders(context, data)
    """
                
    def set_params(self, **params):
        """
        Set values of parameters:
        
        pct_init (optional float between 0 and 1):
            - After opening a new position, this value 
              is the percentage above or below price, 
              where the first stop will be place. 
        pct_trail (optional float between 0 and 1):
            - For any existing position the price of the stop 
              will be trailed by this percentage.
        """
        additionals = set(params.keys()).difference(set(self.params.keys()))
        if len(additionals)>1:
            log.warn('Got additional parameter, which will be ignored!')
            del params[additionals]
        self.params.update(params)
       
    def manage_orders(self, context, data):
        """
        This will:
            - identify any open positions and orders with no stop
            - create new stop levels
            - manage existing stop levels
            - create StopOrders with appropriate price and amount
        """        
        self._refresh_amounts(context)
                
        for sec in self.stops.index:
            cancel_order(self.stops['id'][sec])
            if self._np.isnan(self.stops['price'][sec]):
                stop = (1-self.params['pct_init'])*data.history(sec, 'price', 1, '1m')[0]
            else:
                o = self._np.sign(self.stops['amount'][sec])
                new_stop = (1-o*self.params['pct_trail'])*data.history(sec, 'price', 1, '1m')[0]
                stop = o*max(o*self.stops['price'][sec], o*new_stop)
            
      #      print(data.current(sec,'close'))
      #      print(data.history(sec, 'price', 1, '1m')[0])
            #print(stop)
            self.stops.loc[sec, 'price'] = stop           
            self.stops.loc[sec, 'id'] = order(sec, -self.stops['amount'][sec], style=StopOrder(stop))

    def __init__(self, **params):
        """
        Creatin new StopLoss-Manager object.
        """
        self._import()
        self.params = {'pct_init': 1, 'pct_trail': 1}
        self.stops = self._pd.DataFrame(columns=['amount', 'price', 'id'])        
        self.set_params(**params)        
    
    def _refresh_amounts(self, context):
        """
        Identify open positions and orders.
        """
        
        # Reset position amounts
        self.stops.loc[:, 'amount'] = 0.
        
        # Get open orders and remember amounts for any order with no defined stop.
        open_orders = get_open_orders()
        new_amounts = []
        for sec in open_orders:
            for order in open_orders[sec]:
                if order.stop is None:
                    new_amounts.append((sec, order.amount))                
            
        # Get amounts from portfolio positions.
        for sec in context.portfolio.positions:
            new_amounts.append((sec, context.portfolio.positions[sec].amount))
            
        # Sum amounts up.
        for (sec, amount) in new_amounts:
            if not sec in self.stops.index:
                self.stops.loc[sec, 'amount'] = amount
            else:
                self.stops.loc[sec, 'amount'] = +amount
            
        # Drop securities, with no position/order any more. 
        drop = self.stops['amount'] == 0.
        self.stops.drop(self.stops.index[drop], inplace=True)
        
    def _import(self):
        """
        Import of needed packages.
        """
        import numpy
        self._np = numpy
        
        import pandas
        self._pd = pandas


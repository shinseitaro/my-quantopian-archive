"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US
 
def initialize(context):

    schedule_function(close_positions, date_rules.every_day(), time_rules.market_open(hours=1))
    # schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    
    context.symbol_list = [[sid(40516), sid(40515)], [sid(22445), sid(49173)], [sid(27737), sid(50837)],]
    context.sids = [e for inner_list in context.symbol_list for e in inner_list]
    context.symbol_map = [
        {'base': sid(19656), 'leveraged': sid(43180), 'threshold': {'period': '1200_1545', 'p-min': 0.003, 'm-max': -0.003,}}, #'XLF' 'FINU'
        {'base': sid(23134), 'leveraged': sid(39018), 'threshold': {'period': '1500_1545', 'p-min': 0.003, 'm-max': -0.003,}}, #'ILF',  'LHB'
    ]
    context.portfolio_count = len(context.symbol_map) 
        
     
def before_trading_start(context, data):
    context.cnt = 0 
    for map in context.symbol_map:
        map["base_price_prevclose"] = data.current(map["base"], 'price')
        map["leveraged_price_prevclose"] = data.current(map["leveraged"], 'price')

            
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def close_positions(context, data): 
    for sid in context.portfolio.positions:
        order_target(sid, 0)
    
    
def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
 
def handle_data(context,data):
    """
    Called every minute.
    """
    context.cnt += 1
    
    if context.cnt == 1:
        print get_datetime('US/Eastern')
        for map in context.symbol_map:
            map["0931"] = data.current(map["base"], 'price')
    elif context.cnt == 150:
        print get_datetime('US/Eastern')        
        for map in context.symbol_map:
            map["1200"] = data.current(map["base"], 'price')
    elif context.cnt == 330:
        print get_datetime('US/Eastern')        
        for map in context.symbol_map:
            map["1500"] = data.current(map["base"], 'price')
    elif context.cnt == 375:
        print get_datetime('US/Eastern')        
        for map in context.symbol_map:
            map["1545"] = data.current(map["base"], 'price')
            
        for map in context.symbol_map:        
            t1, t2 = map['threshold']['period'].split('_')
            d1 = map[t1] 
            d2 = map[t2] 
            if d2 / d1 - 1 > map['threshold']['m-max'] and data.can_trade(map['leveraged']) : 
                order_percent(map['leveraged'], -0.9 / context.portfolio_count)
            elif d2 / d1 - 1 < map['threshold']['p-min'] and data.can_trade(map['leveraged']) : 
                order_percent(map['leveraged'], 0.9 / context.portfolio_count)

        
            
        

"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US

import numpy as np
from operator import add

 
def initialize(context):
    # set_commission(commission.PerShare(cost=0, min_trade_cost=0))
    #set_slippage(slippage.FixedSlippage(spread=0))
    # set_slippage(slippage.VolumeShareSlippage(volume_limit=0.5, price_impact=0.5))
    	
    schedule_function(close_positions, date_rules.every_day(), time_rules.market_close())
    # schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
    
        
     
def before_trading_start(context, data):
    context.cnt = 0 
    ## 毎日reflesh するためにbefore_trading_startに置く
    context.symbol_map = [{'base': sid(33837), # 'FCG',
                           'leveraged': sid(49639), # 'GASX',
                           'direction': False,
                           'threshold': [{'period': 'prevclose_1545',
                                          'p-min': 0.02,
                                          'm-max': -0.02,}]},
                          # {'base': sid(19656), #'XLF', 
                          #  'leveraged': sid(43180), #'FINU', ##この銘柄はほっとんど流動性がないので，却下
                          #  'direction': True,
                          #  'threshold': [{'period': '1200_1545',
                          #                 'p-min': 0.003,
                          #                 'm-max': -0.003,}]},
                          {'base': sid(22445), # 'IBB',
                           'leveraged': sid(49073), #'LABU',
                           'direction': True,  
                           'threshold': [{'period': 'prevclose_1545',
                                          'p-min': 0.012,
                                          'm-max': -0.012,}]},  
                          {'base': sid(35854), # 'PIN',
                           'leveraged': sid(39342), # 'INDL',
                           'direction': True,  
                           'threshold': [{'period': 'prevclose_1545',
                                          'p-min': 0.01,
                                          'm-max': -0.01,}]},  
                          {'base': sid(23134), #'ILF',
                           'leveraged': sid(39018), #'LHB',
                           'direction': False,  
                           'threshold': [{'period': '1500_1545',
                                          'p-min': 0.003,
                                          'm-max': -0.003,}]},  
                          {'base': sid(24705), #'EEM',
                           'leveraged': sid(38454), #'EET',
                           'direction': True,    
                           'threshold': [{'period': '1530_1545',
                                          'p-min': 0.02,
                                          'm-max': -0.03,}]},  
                          # {'base': sid(21757), #'EWZ',
                          #  'leveraged': sid(39548), #'UBR',
                          #  'direction': True,    
                          #  'threshold': [{'period': '1500_1545',
                          #                 'p-min': 0.006,
                          #                 'm-max': -0.005, }]},  
                          {'base': sid(33748), #'RSX',
                           'leveraged': sid(41490), #'RUSL',
                           'direction': True,    
                           'threshold': [{'period': 'prevclose_1545',
                                          'p-min': 0.017,
                                          'm-max': -0.017,}]},  
                          {'base': sid(14520), #'EWJ',
                           'leveraged': sid(44996), #'JPNL',
                           'direction': True,    
                           'threshold': [{'period': '1530_1545',
                                          'p-min': 0.002,
                                          'm-max': -0.002,}]},  
                          ]
    

    
    for map in context.symbol_map:
        map["prevclose"] = data.current(map["base"], 'price')
            
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
        for map in context.symbol_map:
            map["0931"] = data.current(map["base"], 'price')
    elif context.cnt == 150:
        for map in context.symbol_map:
            map["1200"] = data.current(map["base"], 'price')
    elif context.cnt == 330:
        for map in context.symbol_map:
            map["1500"] = data.current(map["base"], 'price')
    elif context.cnt == 360:
        for map in context.symbol_map:
            map["1530"] = data.current(map["base"], 'price')
            
    elif context.cnt == 375:
        for map in context.symbol_map:
            map["1545"] = data.current(map["base"], 'price')
            
        for map in context.symbol_map:
            for thread_map in map['threshold']:
                t1, t2 = thread_map['period'].split('_')
                d1 = map[t1] 
                d2 = map[t2]
                thread_map['change'] = d2 /d1 - 1

        for map in context.symbol_map:
            pmin = [x['change'] > x['p-min'] for x in map['threshold']]
            mmax = [x['change'] < x['m-max'] for x in map['threshold']]
            map['orderid'] = -1

            if np.all(pmin) and map['direction']:
                map['position'] = 1
            elif np.all(mmax) and map['direction']:
                map['position'] = -1
            elif np.all(pmin) and not map['direction']:
                map['position'] = -1
            elif np.all(mmax) and not map['direction']:
                map['position'] = 1
            else:
                map['position'] = 0 
        
        context.portfolio_count = np.count_nonzero([map['position'] for map in context.symbol_map])
        
        if context.portfolio_count > 0:
            for map in context.symbol_map:
                if data.can_trade(map['leveraged']):
                    id = order_target_percent(map['leveraged'], 0.5 / context.portfolio_count * map['position'])
                    map['orderid'] = id
                     
        
        for map in context.symbol_map:
            msgs = '\t{0}\t{1}\t{2}\t{3}\t{4}'.format(map['base'].symbol, map['leveraged'].symbol,map['direction'], map['position'], map['orderid'])
            msgs =  msgs + reduce(add,['\t{0}\t{1:.5f}\t{2:.5f}\t{3:.5f}'.format( x['period'],x['change'],x['p-min'],x['m-max']) for x in map['threshold']])
            logging(msgs)
            
		
        
def logging(msgs):
    TIME_ZONE = 'US/Eastern'
    DAY_NAME_DIC = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
    now = get_datetime(TIME_ZONE)
    msgs = '\t{0}\t{1}:\t{2}'.format(now.strftime('%Y-%m-%d %H:%M'), DAY_NAME_DIC[now.weekday()], msgs)
    log.info(msgs)
    
                        
                        
                    
                    
                    
            
		

"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその3：クラックスプレッド
continuous_future つなぎ足 を使って取引
"""

def initialize(context):
    context.soybeans = continuous_future('SY', offset=1, roll='volume', adjustment='mul')
    context.beanoil = continuous_future('BO', offset=1, roll='volume', adjustment='mul')
    context.soymeal = continuous_future('SM', offset=1, roll='volume', adjustment='mul')
    
    schedule_function(my_rebalance, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(hours=1))
    

def get_spread(context, data): 
    pass
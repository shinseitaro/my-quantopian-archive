"""
https://www.quantopian.com/research/notebooks/studies/After%20large%20price%20change.ipynb
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume, Returns
from quantopian.pipeline.filters.morningstar import Q1500US, Q500US
 
import pandas as pd 
from zipline.utils.tradingcalendar import trading_day  


def initialize(context):
    schedule_function(my_rebalance, date_rules.every_day(), time_rules.market_close())
    attach_pipeline(make_pipeline(), 'my_pipeline')
    # 現在のポジションを管理するDataFrame
    context.df_positions = pd.DataFrame(columns=["sid", "exit date"]) 

        
def make_pipeline():
    base_universe = Q500US()
    yesterday_close = USEquityPricing.close.latest
    returns = Returns(window_length=2)
    returns_over_5p = returns > 0.05 
     
    pipe = Pipeline(
        screen = base_universe & returns_over_5p,
        columns = {
            'close': yesterday_close,
            'return':returns
        }
    )
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.dt_today = get_datetime('US/Eastern').date()
    context.output = pipeline_output('my_pipeline')
    context.security_list = context.output.index
    context.position_priod = 5
    
    exit_date = pd.date_range(context.dt_today, periods=context.position_priod, freq=trading_day)[-1].date()
    context.df_positions = context.df_positions.append(pd.DataFrame({"sid":context.output.index, "exit date": exit_date},))
    context.df_positions = context.df_positions.drop_duplicates(subset="sid", keep='first')
    
    #print context.df_positions.merge(context.output, right_index=True, left_on='sid')
    

def my_close(context, data):
    
    exits = context.portfolio.positions
    for sid in exits:
        now = data.current(sid, 'price')
        pos = context.portfolio.positions[sid].cost_basis

        if (now / pos - 1) > 0.05:
            order_percent(sid, 0)
            print "exit for profit %s %s" % (sid, (now / pos - 1))
            context.df_positions = context.df_positions[context.df_positions["sid"]!=sid]
    
    exits = context.df_positions[context.df_positions["exit date"]==context.dt_today ]["sid"]
    for sid in exits:
        order_percent(sid, 0)
        print "exit for profit %s"  % (sid)
    context.df_positions = context.df_positions[context.df_positions["exit date"]!=context.dt_today ]

    
    
def my_open_position(context, data):
    cnt = len(context.security_list)
    for sid in context.security_list:
        order_percent(sid, 1.0/cnt/context.position_priod)
    
    
def my_rebalance(context,data):
    my_close(context, data)
    my_open_position(context, data)
 
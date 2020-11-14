"""
https://www.quantopian.com/research/notebooks/studies/After%20large%20price%20change.ipynb

1. マーケットオープン前に，pipeline で前日のReturnを取得して，５％以上上がった銘柄だけを取得
2. マーケットクローズのタイミングで1.の銘柄をロングする．
3. ５％以上上がった銘柄はポジションクローズ．その他は5日後に自動クローズ

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
    context.df_positions = pd.DataFrame(columns=["sid", "exit date", "return"]) 
        
def make_pipeline():
    base_universe = Q500US()
    yesterday_close = USEquityPricing.close.latest
    returns = Returns(window_length=2)
    returns_over_5p = returns > 0.05 
     
    pipe = Pipeline(
        screen = base_universe,
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

   
def my_close(context, data):
    
    
    exits = context.portfolio.positions.keys()
    
    for sid in exits:
        now = data.current(sid, 'price')
        pos = context.portfolio.positions[sid].cost_basis
        
        if (now / pos - 1) > 0.05:
            order_target(sid, 0)
            # print len(context.df_positions)
            # print context.df_positions
            print "exit for profit\t%s\t%s" % (sid, (now / pos - 1))
            context.df_positions = context.df_positions[context.df_positions["sid"]!=sid]
            # print context.df_positions[context.df_positions["sid"]!=sid]
            # print len(context.df_positions)
    
    exits = context.df_positions[context.df_positions["exit date"]==context.dt_today ]["sid"]
    
    for sid in exits:
        now = data.current(sid, 'price')
        pos = context.portfolio.positions[sid].cost_basis
        order_target(sid, 0)
        if pos != 0:
            print "exit for expiry\t%s\t%s\t%s" % (sid, (now / pos - 1), context.df_positions[context.df_positions["sid"] == sid]['return'].tolist()[0])
        else:
            print "exit for expiry\t%s\t%s\t%s" % (sid, now, pos)
            
    context.df_positions = context.df_positions[context.df_positions["exit date"]!=context.dt_today ]

    
def get_return(context, data):
    hist = data.history(context.security_list, 'price', 2, '1d')
    s_return = hist.pct_change().ix[1]
    context.target_sids = s_return[(s_return > 0.05) & (s_return < 0.07) ]

    
    
def my_open_position(context, data):
    get_return(context, data)

    target_sids = context.target_sids.index
    returns = context.target_sids.tolist()
    
    exit_date = pd.date_range(context.dt_today, periods=context.position_priod, freq=trading_day)[-1].date()
    
    context.df_positions = context.df_positions.append(pd.DataFrame({"sid":target_sids, "exit date": exit_date, "return": returns},))
    context.df_positions = context.df_positions.drop_duplicates(subset="sid", keep='first')
    
    cnt = len(target_sids)
    for sid in target_sids:
        
        if (sid not in context.df_positions["sid"]) and (data.can_trade(sid)):
            order_percent(sid, 1.0/cnt/context.position_priod)
        else:
            context.df_positions = context.df_positions[context.df_positions["sid"]!=sid]
            
    
def my_rebalance(context,data):
    my_close(context, data)
    my_open_position(context, data)
 
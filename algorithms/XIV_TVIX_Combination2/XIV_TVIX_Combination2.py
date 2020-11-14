"""
This is a template algorithm on Quantopian for you to adapt and fill in.
"""
from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US

def calc_contango(context, data):
    context.contango = data.current('v2','Settle')/data.current('v1','Settle')
    return context.contango

def calc_fev(context, data):
    l = data.history(context.spy, 'low', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    h = data.history(context.spy, 'high', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    c = data.history(context.spy, 'close', VOLATILITY_LOOK_BACK_DAYS, '1d')[:-1] #.fillna(method="ffill")
    te = get_TE(l, h, c, ADJUSTMENT_FACTOR, VOLATILITY_WINDOW_DAYS, np.sqrt(DAYS_PER_YEAR))
    te = pd.Series(te)
    return te

def initialize(context):

    context.TIME_ZONE = 'US/Eastern'
    context.DAY_NAME_DIC = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}
    #PIPE_NAME = 'pipe'

    context.VOLATILITY_LOOK_BACK_DAYS = 60
    context.VOLATILITY_WINDOW_DAYS = 11
    context.ADJUSTMENT_FACTOR = 0.9
    context.MOMENTUM_LOOK_BACK_DAYS = 40
    context.DAYS_PER_YEAR = 250
    context.FEV_THRESHOLD = 0.25 
    context.MOMENTUM_THRESHOLD = 0.02
    context.CONTANGO_MIN_THRESHOLD = 0 #1.00
    context.CONTANGO_MAX_THRESHOLD = 2 #1.15

    context.THRESHOLD = 0.00
    context.UTILIZATION = 0.95
    context.TVIX_MULTIPLIER = 1.25
    
    context.spy = sid(8554)
    context.vxx = sid(38054)
    context.xiv = sid(40516) 
    context.tvix = sid(40515)
    
    context.sids = [context.spy,context.vxx,context.xiv,context.tvix]
    
    fetch_csv('http://www.quandl.com/api/v1/datasets/CHRIS/CBOE_VX1.csv', 
        date_column='Trade Date', 
        date_format='%Y-%m-%d',
        symbol='v1',
        post_func=rename_col)
    # Second month VIX futures data
    fetch_csv('http://www.quandl.com/api/v1/datasets/CHRIS/CBOE_VX2.csv', 
        date_column='Trade Date', 
        date_format='%Y-%m-%d',
        symbol='v2',
        post_func=rename_col)
    schedule_function(rebalance, 
                      date_rules.week_end(),
                      time_rules.market_close(minutes=1),
                      calendar=calendars.US_EQUITIES)
    
    schedule_function(my_record_vars, 
                      date_rules.every_day(), 
                      time_rules.market_close(minutes=1),
                      calendar=calendars.US_EQUITIES)
    
    
    attach_pipeline(make_pipeline(), 'my_pipeline')

def my_rebalance(context,data):
    # 最新の価格と，昨日のクローズを取得
    df_entry = data.history(context.sids, 'price', 2, '1d',)
    contango = calc_contango(context, data)
    fev = calc_fev(context, data)
    momentum_fev = calc_momentum(context, data, fev, MOMENTUM_LOOK_BACK_DAYS)

    if not (data.can_trade(context.xiv) and data.can_trade(context.tvix)):
        return
    
    
    
    
    
    
    
    
def my_record_vars(context, data):
    record(third_eye_fev=fev.iloc[-1], 
           momentum_fev=momentum_fev*10, 
           contango=contango-1.0,)
    

    

def make_pipeline():
    
    # Base universe set to the Q500US
    base_universe = Q1500US()

    # Factor of yesterday's close price.
    yesterday_close = USEquityPricing.close.latest
     
    pipe = Pipeline(
        screen = base_universe,
        columns = {
            'close': yesterday_close,
        }
    )
    return pipe
 
def before_trading_start(context, data):
    """
    Called every day before market open.
    """
    context.output = pipeline_output('my_pipeline')
  
    # These are the securities that we are interested in trading each day.
    context.security_list = context.output.index
     
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 

 
    
 
def handle_data(context,data):
    """
    Called every minute.
    """
    pass

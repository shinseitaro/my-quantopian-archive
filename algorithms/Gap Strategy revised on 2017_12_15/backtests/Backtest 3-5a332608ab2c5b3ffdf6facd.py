from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.factors import AverageDollarVolume

from quantopian.pipeline.experimental import QTradableStocksUS
import pandas as pd 

def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0: "Sun", 1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat"}
    msgs = '\t%s\t%s:\t%s'%(dt.strftime('%Y/%m/%d %H:%M (ET)'), youbidict[int(youbi)], msgs)
    log.info(msgs)


class ValueDaybeforeYesterday(CustomFactor):
    window_length = 2
    def compute(self, today, assets, out, values):
        out[:] = values[0]    
        
def make_pipeline(context):
    pipe = Pipeline()
    base_universe = QTradableStocksUS()
    dollar_volume = AverageDollarVolume(window_length=30)
    high_dollar_volume = dollar_volume.percentile_between(98, 100)
    
    close_day_before_yeseterday = ValueDaybeforeYesterday(inputs = [USEquityPricing.close])
    volume_day_before_yeseterday = ValueDaybeforeYesterday(inputs = [USEquityPricing.volume])
    pipe.add(close_day_before_yeseterday, "close_day_before_yeseterday")
    
    my_screen = base_universe & high_dollar_volume
    pipe.set_screen(my_screen)
    return pipe 

    
def initialize(context):
    attach_pipeline(make_pipeline(context), 'pipe')
    schedule_function(calc_gap, date_rules.every_day(), time_rules.market_open())
    
         
def before_trading_start(context, data):
    context.output = pipeline_output('pipe')      


def calc_gap(context, data):
    sids = context.output.index
    open_price = data.current(sids,'open')
    df = pd.concat([context.output, open_price], axis = 1) 
    df['gap'] = df['open'] / df['close_day_before_yeseterday'] - 1
    df = df[(df['gap'] > 0.05) & (df['gap'] < 1.0) ]
    df = df.nlargest(10,'gap')
    print df
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import QTradableStocksUS


def initialize(context):
    future = 'NG'
    context.contract1 = continuous_future(future, offset=0, roll='calendar', adjustment=None)
    context.contract2 = continuous_future(future, offset=0, roll='calendar', adjustment=None)
    
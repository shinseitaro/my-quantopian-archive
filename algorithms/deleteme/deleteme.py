import quantopian.algorithm as algo
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt


def initialize(context):
    
    schedule_function(rebalance,
                      date_rules.every_day(),
                      time_rules.market_open(hours=1))
    context.future = "CL" 
    context.f1 = continuous_future(context.future, offset=0, roll='calendar', adjustment=None)
    context.f2 = continuous_future(context.future, offset=1, roll='calendar', adjustment=None)
    context.f3 = continuous_future(context.future, offset=2, roll='calendar', adjustment=None)
    context.f4 = continuous_future(context.future, offset=3, roll='calendar', adjustment=None)
    context.f5 = continuous_future(context.future, offset=4, roll='calendar', adjustment=None)
    context.f6 = continuous_future(context.future, offset=5, roll='calendar', adjustment=None)
    context.f7 = continuous_future(context.future, offset=6, roll='calendar', adjustment=None)
    context.f8 = continuous_future(context.future, offset=7, roll='calendar', adjustment=None)
    context.f9 = continuous_future(context.future, offset=8, roll='calendar', adjustment=None)
    

    
def rebalance(context, data):
    weights = {}
    context.future_contract = data.current(
        [context.f1,context.f8,],
        fields='contract')
    weights[context.future_contract[context.f1]] = -0.5
    weights[context.future_contract[context.f8]] = 0.5
    
    order_optimal_portfolio(opt.TargetWeights(weights),
                            constraints=[],)
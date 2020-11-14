"""
Tokyo Quantopian User Group handson Vol4
単純なカレンダー
"""
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt
from zipline.utils.calendars import get_calendar
import pandas as pd
import numpy as np


def initialize(context):
    sym1 = "HO"

    context.first_contract = continuous_future(sym1, roll="calendar", offset=0)
    context.f1 = continuous_future(sym1, roll="calendar", offset=2)
    context.f2 = continuous_future(sym1, roll="calendar", offset=4)

    context.holding_days = 0
    context.n_days_before_expired = 10
    context.sma_window = 5

    # schedule
    schedule_function(
        my_rebalance,
        date_rule=date_rules.every_day(),
        time_rule=time_rules.market_open(),
    )
    schedule_function(
        my_record, date_rule=date_rules.every_day(),
        time_rule=time_rules.market_open()
    )


def is_near_expiration(contract):
    return (contract.expiration_date - get_datetime()).days


def get_my_position(cpp):
    l = list()
    for k, v in cpp.iteritems():
        d = {
            "symbol": k.symbol,
            "amount": v.amount,
            "average value": v.cost_basis,
            "last_sale_price": v.last_sale_price,
            "current value": v.last_sale_price * v.amount,
            "PL": ((v.cost_basis / v.last_sale_price - 1) * v.amount * k.multiplier),
            # 'exp date': k.expiration_date.strftime("%Y%m%d")
        }

        l.append(d)
    df = pd.DataFrame(l)
    df = df.set_index("symbol")
    log.info(df)
    return df


def close_all_potision(context, data):
    log.info("close potision".format())
    order_target(context.contract_sym1, 0)
    order_target(context.contract_sym2, 0)


def my_rebalance(context, data):
    cpp = context.portfolio.positions
    if cpp:
        df = get_my_position(cpp)
        log.info("PL: {}".format(df["PL"].sum()))
        if np.abs(df["amount"].sum()) > 5:
            partially_filled = True

    hist = data.history(
        [context.f1, context.f2], fields="price", bar_count=60, frequency="1d"
    )
    context.ratio = hist[context.f1] / hist[context.f2]
    context.sma = context.ratio.rolling(context.sma_window).mean()
    contract_sym1 = data.current(context.f1, "contract")
    contract_sym2 = data.current(context.f2, "contract")

    target_weight = {}
    contract_sym1 = data.current(context.f1, "contract")
    contract_sym2 = data.current(context.f2, "contract")
    if context.ratio[-1] > context.sma[-1]: and context.ratio[-1] < 1:
        target_weight[contract_sym1] = -0.5
        target_weight[contract_sym2] = 0.5
    elif context.ratio[-1] < context.sma[-1]:
        target_weight[contract_sym1] = 0
        target_weight[contract_sym2] = 0

    if target_weight:
        order_optimal_portfolio(opt.TargetWeights(target_weight), constraints=[])


def my_record(context, data):
    record(ratio=context.ratio[-1], sma=context.sma[-1])
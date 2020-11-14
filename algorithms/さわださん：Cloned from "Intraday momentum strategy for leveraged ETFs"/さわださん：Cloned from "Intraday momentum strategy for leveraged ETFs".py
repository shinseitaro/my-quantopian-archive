#!/usr/bin/env python
# -*- coding: utf-8 -*-

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor, CustomFilter
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import StaticSids

import datetime as dt
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier


TIME_ZONE = 'US/Eastern'
DAY_NAME_DIC = {0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat'}

ENTRY_TIMING = 15
EXIT_TIMING = 1

MIN_LEARNING_SIZE = 250
MAX_LEARNING_SIZE = 500
PROBABILLITY_THRESHOLD = 0.6
#MIN_OPENING_GAP = -1.0
#MAX_OPENING_GAP = 1.0
MIN_PRICE_CHANGE_THRESHOLD = np.log(1.025/1.000)
#MAX_PRICE_CHANGE_THRESHOLD = np.log(1.50/1.000)
MIN_POSITIONS = 2
#MAX_POSITIONS = 4

PIPE_NAME = 'pipe'


# Logging
def logging(msgs):
    now = get_datetime(TIME_ZONE)
    msgs = '\t{0}\t{1}:\t{2}'.format(now.strftime('%Y-%m-%d %H:%M'), DAY_NAME_DIC[now.weekday()], msgs)
    log.info(msgs)


class SidInList(CustomFilter):
    inputs = []
    window_length = 1
    params = ('sid_list',)

    def compute(self, today, assets, out, sid_list):
        out[:] = np.in1d(assets, sid_list)


class OpeningGap(CustomFactor):
    inputs = [USEquityPricing.close, USEquityPricing.open]
    window_length = 1

    def compute(self, today, assets, out, close, open):
        out[:] = np.log(open[0] / close[-1])


def initialize(context):
    context.target_symbols = symbols('UPRO', 'FAS', 'SPXL',
                                     #'LABD', 'SSO', 
                                     #'TQQQ', 'NUGT', 'SDS', 'QLD', 'JNUG', 'TZA',    
    )
    context.target_sids = tuple([s.sid for s in context.target_symbols])
    context.static_asset = True
    context.price_records = dict([(sid, None) for sid in context.target_sids])
    context.models = context.price_records.copy()
    #
    #context.min_opening_gap = MIN_OPENING_GAP
    #context.max_opening_gap = MAX_OPENING_GAP
    context.min_price_change_threshold = MIN_PRICE_CHANGE_THRESHOLD
    #context.max_price_change_threshold = MAX_PRICE_CHANGE_THRESHOLD
    #
    attach_pipeline(make_pipeline(context), PIPE_NAME)
    #
    schedule_function(entry_trade, date_rules.every_day(), time_rules.market_close(minutes=ENTRY_TIMING))
    schedule_function(exit_trade, date_rules.every_day(), time_rules.market_close(minutes=EXIT_TIMING))


def make_pipeline(context):
    include_filter = SidInList(sid_list=context.target_sids)
    pipe = Pipeline(
        screen=include_filter,
        columns={
            'previous_close_price': USEquityPricing.close.latest,
            #'market_cap': MarketCap(),
            'opening_gap': OpeningGap(),
            })
    return pipe


def before_trading_start(context, data):
    context.output = pipeline_output(PIPE_NAME)
    context.sids = context.output.index

    # schedule_function can not handle post-date actions
    df_close = data.history(context.sids, 'price', 1, '1d') # this can be removed if you get close price by the
    # following line
    df_entry = data.history(context.sids, 'price', ENTRY_TIMING+1, '1m').head(1)
    context.price_records = add_price_records(context, df_entry, df_close)
    if get_datetime(TIME_ZONE).weekday() == 1:
         update_models(context, data)


def entry_trade(context, data):
    df = context.output
    df['entry_price'] = data.current(context.sids, 'price')
    df['previous_close_price_change'] = (df['entry_price']/df['previous_close_price']).apply(np.log)
    #
    trade_sids = list()
    for sid in context.sids:
        model = context.models[sid]
        if model is not None:
            x = df['previous_close_price_change'][sid]
            if abs(x) > context.min_price_change_threshold:
                y = model.predict([x])[0]
                p = model.predict_proba([x])[0][0]
                if (p > PROBABILLITY_THRESHOLD) \
                or (1-p > PROBABILLITY_THRESHOLD): 
                    trade_sids.append((sid, x, y, p))
    num_trades = max(len(trade_sids), MIN_POSITIONS)
    for sid, x, y, p in trade_sids:
        if x > 0 and y:
            order_percent(sid, 1.0/num_trades)
            logging('Entry long: {0} {1: .2f} {2: .2f}'.format(sid.symbol, 1.0/num_trades, p))
        else:
            order_percent(sid, -1.0/num_trades)
            logging('Entry short: {0} {1: .2f} {2: .2f}'.format(sid.symbol, 1.0/num_trades, p))


def exit_trade(context, data):
    for sid in context.portfolio.positions:
        order_target(sid, 0)


def add_price_records(context, df_entry, df_close):
    d = context.price_records
    for sid in context.sids:
        df = pd.DataFrame([[df_entry[sid][0], df_close[sid][0]]],
                          index=df_close.index, columns=['entry_price', 'close_price'])
        d[sid] = d[sid].append(df) if d[sid] is not None else df
    return d


def update_models(context, data):
    logging('weekly update of the model initiated')
    d = dict()
    for sid in context.models.keys():
        d[sid] = build_model(context.price_records[sid], MIN_LEARNING_SIZE, MAX_LEARNING_SIZE)
    context.models = d


def build_model(df, min_size, max_size):
    if df is None:
        return None
    df = df.copy()
    df['previous_close_price'] = df['close_price'].shift(1)
    df = df.dropna().tail(max_size)
    if len(df) < min_size:
        return None
    df['previous_close_price_change'] = (df['entry_price']/df['previous_close_price']).apply(np.log)
    df['return'] = (df['close_price']/df['entry_price']).apply(np.log)
    model = RandomForestClassifier(n_estimators=1)
    model.fit(df[['previous_close_price_change']].as_matrix(), (df['return'] > 0).as_matrix())
    return model


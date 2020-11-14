# This algorithm recreates the algorithm presented in
# "Quantifying Trading Behavior in Financial Markets Using Google Trends"
# Preis, Moat & Stanley (2013), Scientific Reports
# (c) 2013 Thomas Wiecki, Quantopian Inc.

import numpy as np
import datetime
# Average over 5 weeks, free parameter.
delta_t = 5

def initialize(context):
    # This is the search query we are using, this is tied to the csv file.
    context.query = 'debt'
    # User fetcher to get data. I uploaded this csv file manually, feel free to use.
    # Note that this data is already weekly averages.
    fetch_csv('https://gist.githubusercontent.com/twiecki/5629198/raw/6247da04bacebcd6334a4b91ed21f14483c6d4d0/debt_google_trend',
              date_format='%Y-%m-%d',
              symbol='debt',
    )
    context.order_size = 10000
    context.sec_id = 8554
    context.security = sid(8554) # S&P5000
    
    schedule_function(rebalance, 
                      date_rule=date_rules.week_start(), 
                      time_rule=time_rules.market_close(hours=1))
    
    context.past_queries = []

def rebalance(context, data):
    c = context
  
    # Extract weekly average of search query.
    indicator = data.current(c.query, c.query)
    
    # Track our fetched values in a context variable to build up history.
    context.past_queries.append(indicator)
    if len(context.past_queries) > 5:
        del context.past_queries[0]
    
    if len(context.past_queries) == 5:
        # Compute average over weeks in range
        mean_indicator = np.mean(context.past_queries)

        # Long or short depending on whether debt search frequency
        # went down or up, respectively.
        if indicator > mean_indicator:
            order_target(c.security, -c.order_size)
        else:
            order_target(c.security, c.order_size)

import numpy as np
import pandas as pd
from collections import deque

R_P = 1 # refresh period in days
W_L = 28 # window length in days
def initialize(context):
    context.nobs = W_L
    context.max_notional = 100000
    context.min_notional = -100000
    
    context.stocks = [sid(14516), sid(14517)]
    context.evec = [0.943, -0.822]
    context.unit_shares = 10000
    context.tickers = [e.sid for e in context.stocks]    
    context.prices = pd.DataFrame({ k : pd.Series() for k in context.tickers } )
    schedule_function(func=process_data_and_order, date_rule=date_rules.every_day())

def process_data_and_order(context, data):
    
    if len(context.prices)<context.nobs:
        newRow = pd.DataFrame({k:float(data.current(s, "price")) for k,s in zip(context.tickers, context.stocks) },index=[0])
        context.prices = context.prices.append(newRow, ignore_index = True)
    else:
        comb_price_past_window = np.zeros(len(context.prices))
        log.info(comb_price_past_window)
        for ii,k in enumerate(context.tickers):
            comb_price_past_window += context.evec[ii]*context.prices[k]
        log.info(comb_price_past_window)
        
        meanPrice = np.mean(comb_price_past_window)
        stdPrice = np.std(comb_price_past_window)
        log.info(meanPrice)
        
        comb_price = sum([e*data.current(s, "price") for e,s in zip(context.evec, context.stocks)])
        h = (comb_price - meanPrice)/stdPrice
        
        current_amount = []
        cash_spent = [];
        
        for ii, stock in enumerate(context.stocks):
            current_position = context.portfolio.positions[stock].amount
            new_position = context.unit_shares * (-h) * context.evec[ii]
            current_amount.append(new_position)
            cash_spent.append((new_position - current_position)*data.current(stock, "price"))
            order(stock, new_position - current_position)

        notionals = []
        for ii,stock in enumerate(context.stocks):
            #notionals.append((context.portfolio.positions[stock].amount*data[stock].price)/context.portfolio.starting_cash)
            notionals.append((context.portfolio.positions[stock].amount*data.current(stock, "price"))/context.portfolio.starting_cash)
        log.info("h = {h}, comb_price = {comb_price}, notionals = {notionals}, total = {tot}, price0 = {p0}, price1 = {p1}, cash = {cash}, amount = {amount}, new_cash = {nc}".\
                 format(h = h, comb_price = comb_price, notionals = notionals, \
                        tot = context.portfolio.positions_value + context.portfolio.cash, p0 = data.current(context.stocks[0], "price"), \
                        p1 = data.current(context.stocks[1], "price"), cash = context.portfolio.cash, amount = current_amount, \
                        nc = context.portfolio.cash - sum(cash_spent)))
        
        newRow = pd.DataFrame({k:float(data.current(s, "price")) for k,s in zip(context.tickers, context.stocks) },index=[0])
        context.prices = context.prices.append(newRow, ignore_index = True)
        context.prices = context.prices[1:len(context.prices)]    
        
        record(h = h, mPri = meanPrice)
        record(comb_price = comb_price)
        record(not0 = notionals[0], not1 = notionals[1])
        #record(price0 = data[context.stocks[0]].price*abs(context.evec[0]), price1 = data[context.stocks[1]].price*abs(context.evec[1]))
        #record(price0 = data[context.stocks[0]].price, price1 = data[context.stocks[1]].price)
    #record(port = context.portfolio.positions_value, cash = context.portfolio.cash)
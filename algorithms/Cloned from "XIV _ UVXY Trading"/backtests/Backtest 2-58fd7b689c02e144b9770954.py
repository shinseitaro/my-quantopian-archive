import talib

def initialize(context):
    
    context.XIV = sid(40516)
    context.UVXY = sid(41969)

    schedule_function(
         rebalance, 
         date_rules.every_day(),
         time_rules.market_open(minutes=1)
     )

def rebalance(context, data):

    #Current Prices
    xiv_current = data.current(context.XIV, 'price') 
    xivPrices = data.history(context.XIV,'close',24,'1d')
    uvxyPrices = data.history(context.UVXY,'close',20,'1d')
    xivMA_24 = xivPrices.mean()
    
    #RSI
    uvxyRSI = talib.RSI(uvxyPrices,timeperiod=14)[-1]
    
    #UVXY ENTRY and XIV EXIT
    if data.can_trade(context.UVXY) and uvxyRSI > 70:
        log.info('UVXY RSI: %s ' % uvxyRSI)  
        order_target_percent(context.UVXY,-.9)
        order_target_percent(context.XIV,0)
    
    #XIV ENTRY
    if data.can_trade(context.XIV) and uvxyRSI < 15:
        order_target_percent(context.XIV,.9)
    
    #UVXY EXIT
    if data.can_trade(context.UVXY) and uvxyRSI < 45:
        order_target_percent(context.UVXY,0)
        
    #XIV EXIT
    if data.can_trade(context.XIV) and xiv_current < xivMA_24:
        order_target_percent(context.XIV,0)
           
def pvr(context, data):  
    ''' Custom chart and/or logging of profit_vs_risk returns and related information  
    '''  
    import time  
    from datetime import datetime  
    from pytz import timezone      # Python will only do once, makes this portable.  
                                   #   Move to top of algo for better efficiency.  
    c = context  # Brevity is the soul of wit -- Shakespeare [for readability]  
    if 'pvr' not in c:

        # You can change this to an integer, total cash input minus any withdrawals  
        manual_cash = c.portfolio.starting_cash

        c.pvr = {  
            'options': {  
                # # # # # # # # # #  Options  # # # # # # # # # #  
                'logging'         : 0,    # Info to logging window with some new maximums

                'record_pvr'      : 1,    # Profit vs Risk returns (percentage)  
                'record_pvrp'     : 0,    # PvR (p)roportional neg cash vs portfolio value  
                'record_cash'     : 1,    # Cash available  
                'record_max_lvrg' : 1,    # Maximum leverage encountered  
                'record_risk_hi'  : 0,    # Highest risk overall  
                'record_shorting' : 0,    # Total value of any shorts  
                'record_max_shrt' : 0,    # Max value of shorting total  
                'record_cash_low' : 1,    # Any new lowest cash level  
                'record_q_return' : 0,    # Quantopian returns (percentage)  
                'record_pnl'      : 1,    # Profit-n-Loss  
                'record_risk'     : 0,    # Risked, max cash spent or shorts beyond longs+cash  
                'record_leverage' : 0,    # Leverage (context.account.leverage)  
                # # # # # # # # #  End options  # # # # # # # # #  
            },  
            'pvr'        : 0,      # Profit vs Risk returns based on maximum spent  
            'cagr'       : 0,  
            'max_lvrg'   : 0,  
            'max_shrt'   : 0,  
            'risk_hi'    : 0,  
            'days'       : 0.0,  
            'date_prv'   : '',  
            'date_end'   : get_environment('end').date(),  
            'cash_low'   : manual_cash,  
            'cash'       : manual_cash,  
            'start'      : manual_cash,  
            'begin'      : time.time(),  # For run time  
            'log_summary': 126,          # Summary every x days. 252/yr  
            'run_str'    : '{} to {}  ${}  {} US/Eastern'.format(get_environment('start').date(), get_environment('end').date(), int(manual_cash), datetime.now(timezone('US/Eastern')).strftime("%Y-%m-%d %H:%M"))  
        }  
        if c.pvr['options']['record_pvrp']: c.pvr['options']['record_pvr'] = 0 # if pvrp is active, straight pvr is off  
        if get_environment('arena') not in ['backtest', 'live']: c.pvr['log_summary'] = 1 # Every day when real money  
        log.info(c.pvr['run_str'])  
    p = c.pvr ; o = c.pvr['options']  
    def _pvr(c):  
        p['cagr'] = ((c.portfolio.portfolio_value / p['start']) ** (1 / (p['days'] / 252.))) - 1  
        ptype = 'PvR' if o['record_pvr'] else 'PvRp'  
        log.info('{} {} %/day   cagr {}   Portfolio value {}   PnL {}'.format(ptype, '%.4f' % (p['pvr'] / p['days']), '%.3f' % p['cagr'], '%.0f' % c.portfolio.portfolio_value, '%.0f' % (c.portfolio.portfolio_value - p['start'])))  
        log.info('  Profited {} on {} activated/transacted for PvR of {}%'.format('%.0f' % c.portfolio.pnl, '%.0f' % p['risk_hi'], '%.1f' % p['pvr']))  
        log.info('  QRet {} PvR {} CshLw {} MxLv {} RskHi {} MxShrt {}'.format('%.2f' % q_rtrn, '%.2f' % p['pvr'], '%.0f' % p['cash_low'], '%.2f' % p['max_lvrg'], '%.0f' % p['risk_hi'], '%.0f' % p['max_shrt']))  
    def _minut():  
        dt = get_datetime().astimezone(timezone('US/Eastern'))  
        return str((dt.hour * 60) + dt.minute - 570).rjust(3)  # (-570 = 9:31a)  
    date = get_datetime().date()  
    if p['date_prv'] != date:  
        p['date_prv'] = date  
        p['days'] += 1.0  
    do_summary = 0  
    if p['log_summary'] and p['days'] % p['log_summary'] == 0 and _minut() == '100':  
        do_summary = 1              # Log summary every x days  
    if do_summary or date == p['date_end']:  
        p['cash'] = c.portfolio.cash  
    elif p['cash'] == c.portfolio.cash and not o['logging']: return  # for speed

    shorts = sum([z.amount * z.last_sale_price for s, z in c.portfolio.positions.items() if z.amount < 0])  
    q_rtrn       = 100 * c.portfolio.returns  
    cash         = c.portfolio.cash  
    new_risk_hi  = 0  
    new_max_lv   = 0  
    new_max_shrt = 0  
    new_cash_low = 0               # To trigger logging in cash_low case  
    cash_dip     = int(max(0, p['start'] - cash))  
    risk         = int(max(cash_dip, -shorts))

    if o['record_pvrp'] and cash < 0:   # Let negative cash ding less when portfolio is up.  
        cash_dip = int(max(0, p['start'] - cash * p['start'] / c.portfolio.portfolio_value))  
        # Imagine: Start with 10, grows to 1000, goes negative to -10, should not be 200% risk.

    if int(cash) < p['cash_low']:             # New cash low  
        new_cash_low = 1  
        p['cash_low']  = int(cash)            # Lowest cash level hit  
        if o['record_cash_low']: record(CashLow = p['cash_low'])

    if c.account.leverage > p['max_lvrg']:  
        new_max_lv = 1  
        p['max_lvrg'] = c.account.leverage    # Maximum intraday leverage  
        if o['record_max_lvrg']: record(MaxLv   = p['max_lvrg'])

    if shorts < p['max_shrt']:  
        new_max_shrt = 1  
        p['max_shrt'] = shorts                # Maximum shorts value  
        if o['record_max_shrt']: record(MxShrt  = p['max_shrt'])

    if risk > p['risk_hi']:  
        new_risk_hi = 1  
        p['risk_hi'] = risk                   # Highest risk overall  
        if o['record_risk_hi']:  record(RiskHi  = p['risk_hi'])

    # Profit_vs_Risk returns based on max amount actually spent (risk high)  
    if p['risk_hi'] != 0: # Avoid zero-divide  
        p['pvr'] = 100 * (c.portfolio.portfolio_value - p['start']) / p['risk_hi']  
        ptype = 'PvRp' if o['record_pvrp'] else 'PvR'  
        if o['record_pvr'] or o['record_pvrp']: record(**{ptype: p['pvr']})

    if o['record_shorting']: record(Shorts    = shorts)            # Shorts value as a positve  
    if o['record_leverage']: record(Lvrg = c.account.leverage)     # Leverage  
    if o['record_cash']:     record(Cash = cash)                   # Cash  
    if o['record_risk']:     record(Risk = risk)   # Amount in play, maximum of shorts or cash used  
    if o['record_q_return']: record(QRet = q_rtrn) # Quantopian returns to compare to pvr returns curve  
    if o['record_pnl']:      record(PnL  = c.portfolio.portfolio_value - p['start']) # Profit|Loss

    if o['logging'] and (new_risk_hi or new_cash_low or new_max_lv or new_max_shrt):  
        csh     = ' Cash '   + '%.0f' % cash  
        risk    = ' Risk '   + '%.0f' % risk  
        qret    = ' QRet '   + '%.1f' % q_rtrn  
        shrt    = ' Shrt '   + '%.0f' % shorts  
        lv      = ' Lv '     + '%.1f' % c.account.leverage  
        pvr     = ' PvR '    + '%.1f' % p['pvr']  
        rsk_hi  = ' RskHi '  + '%.0f' % p['risk_hi']  
        csh_lw  = ' CshLw '  + '%.0f' % p['cash_low']  
        mxlv    = ' MxLv '   + '%.2f' % p['max_lvrg']  
        mxshrt  = ' MxShrt ' + '%.0f' % p['max_shrt']  
        pnl     = ' PnL '    + '%.0f' % (c.portfolio.portfolio_value - p['start'])  
        log.info('{}{}{}{}{}{}{}{}{}{}{}{}'.format(_minut(), lv, mxlv, qret, pvr, pnl, csh, csh_lw, shrt, mxshrt, risk, rsk_hi))  
    if do_summary: _pvr(c)  
    if get_datetime() == get_environment('end'):    # Summary at end of run  
        _pvr(c)  
        elapsed = (time.time() - p['begin']) / 60  # minutes  
        log.info( '{}\nRuntime {} hr {} min'.format(p['run_str'], int(elapsed / 60), '%.1f' % (elapsed % 60)))

def handle_data(context, data): 
    pass
    #pvr(context, data)  
    
    
    
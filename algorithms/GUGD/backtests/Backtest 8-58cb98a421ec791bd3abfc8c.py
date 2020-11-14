"""
GUGDのバックテスト
update_universe 
    + 出来高過去平均トップ５００
    + 前日終値から当日始値のDiffが大きいものをそれぞれ１０銘柄
rebalance 
    + GUしたものは，Open５分後にショート
    + GDしたものは，Open５分後にロング
    + ウェイトは銘柄分の１
logging 
    + 銘柄，株数，購入額
    + PLはFullBacktestで確認するのでログには出さない

参考
https://www.quantopian.com/posts/newbie-question-pipe-dot-set-screen-typererror
https://www.quantopian.com/posts/ranked-universe-and-long-short-equity-strategy
"""

from quantopian.algorithm import attach_pipeline, pipeline_output
from quantopian.pipeline import Pipeline, CustomFactor
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.data import morningstar
from quantopian.pipeline.factors import AverageDollarVolume
from quantopian.pipeline.filters.morningstar import Q1500US


def logging(msgs):
    dt = get_datetime('US/Eastern')
    youbi = dt.strftime("%w")
    youbidict = {0:"Sun", 1:"Mon", 2:"Tue", 3:"Wed", 4:"Thu", 5:"Fri", 6:"Sat"}
    msgs = '%s\t%s:\t%s' % (dt.strftime('%Y/%m/%d %H:%M'), youbidict[int(youbi)], msgs)  
    log.info(msgs)
    
class MarketCap(CustomFactor):
    inputs = [USEquityPricing.close, morningstar.valuation.shares_outstanding]
    window_length = 1 
    
    def compute(self, today, assets, out, close, shares):
        out[:] = close[-1] * shares[-1]

# 出来高/発行株高     
class Liquidity(CustomFactor): 
    inputs = [USEquityPricing.volume, morningstar.valuation.shares_outstanding]
    window_length = 1 
    def compute(self, today, assets, out, volume, shares):
        out[:] = volume[-1] / shares[-1]

class Return(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-1] / close[-2] - 1

class PrevClose(CustomFactor):
    inputs = [USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, close):
        out[:] = close[-2]

class Gap(CustomFactor):
    inputs = [USEquityPricing.open, USEquityPricing.close]
    window_length = 2
    def compute(self, today, assets, out, open_price, close):
        out[:] = open_price[-1] / close[-2] - 1 
        
  
def make_pipeline(context):
    pipe = Pipeline()
    
    liquidity = Liquidity()
    pipe.add(liquidity, 'liquidity')
    
    marketcap = MarketCap()
    pipe.add(marketcap, 'marketcap')
    top_500 = marketcap.top(100)
    
    liquidity_rank = liquidity.rank(mask=top_500)
    pipe.add(liquidity_rank, 'liquidity_rank')
    
    gap = Gap()
    pipe.add(gap, 'gap')
    return pipe


def handle_entry(context, data):
    # 最新のプライス
    today_open = data.history(context.stocke_list, fields='open', bar_count=1, frequency='1d')
    prev_close = data.history(context.stocke_list, fields='price', bar_count=2, frequency='1d')
    
    gaps = {}
    for sid in context.stocke_list:

        # 今日の始値/昨日の終値が-1％以下だった場合
        if today_open[sid][-1] / prev_close[sid][-2] - 1 < -0.01:
            gaps[sid] = today_open[sid][-1] / prev_close[sid][-2] - 1
            
    sorted_gaps = sorted(gaps.items(), key = lambda x: x[1])
    
    # 急激にGDした銘柄だけ取得
    targets = [x[0] for x in sorted_gaps[:10]]
    
    logging("Today's GapDown list: %s" % ",".join([x.symbol for x in targets]))
    
    for sid in targets:
        context.order_ids[sid] = {'id': order_percent(sid, 0.09), 
                                  'output': True, 
                                  'prevclose': prev_close[sid][-2],
                                  'today open': today_open[sid][-1],
                                 'gap': gaps[sid]}

def handle_exit(context, data, at_market_closing = False):
    sids = context.order_ids.keys()
    if sids:
        for sid in sids: 
            target_price = context.order_ids[sid]['prevclose']
            current = data.current(sid, 'price')
            gap = context.order_ids[sid]['gap']
            go = False
            todayopen = context.order_ids[sid]['today open']
            prevclose = context.order_ids[sid]['prevclose']
            
            
            if context.order_ids[sid]['position'] != 0:
                last_sale_price = context.order_ids[sid]['last_sale_price']
                if at_market_closing:
                    msg = "Order Closed (At Market Closing) \t symbol \t {symbol} \tPrice \t {current} \tBought at \t {last_sale_price} \t prevclose \t {prevclose} \t today's open \t{todayopen}\tGap \t {gap}\t PL \t {pl}"    
                    go = True
                else:
                    if current >= target_price: #current / last_sale_price - 1 > 0.01:
                        go = True
                        msg = "Order Closed \t symbol \t {symbol} \tPrice \t {current} \tBought at \t {last_sale_price} \t prevclose \t {prevclose} \t today's open \t{todayopen}\tGap \t {gap}\t PL \t {pl}" 
            if go:
                order_percent(sid, 0)
                msg = msg.format(symbol=sid.symbol, current=current, 
                                 last_sale_price=last_sale_price, 
                                 gap=gap, pl=current/last_sale_price-1,
                                todayopen=todayopen, prevclose=prevclose)

                logging(msg)
                del context.order_ids[sid]
                    
def exit_all(context, data):
    handle_exit(context, data, True)


def initialize(context):
    # GUGD銘柄を，寄り付き５分後に取引
    schedule_function(handle_entry, date_rules.every_day(), time_rules.market_open(minutes=5))
     
    schedule_function(exit_all, date_rules.every_day(), time_rules.market_close(minutes=5))
    schedule_function(my_record_vars, date_rules.every_day(), time_rules.market_close())
     
    attach_pipeline(make_pipeline(context), 'mypipe')

    
def before_trading_start(context, data):
    context.order_ids = {}
    
    sp_500 = get_fundamentals(  
                        query(fundamentals.valuation.market_cap)  
                        .filter(fundamentals.valuation.market_cap > 1e8)  
                        .order_by(fundamentals.valuation.market_cap.desc())  
                        .limit(500))  
    context.stocke_list = sp_500.columns
    update_universe(context.stocke_list)
   
    
def handle_data(context,data):
    
    sids = context.order_ids.keys()
    if sids:
        for sid in sids:
            if context.order_ids[sid]['output']:
                
                ordered = get_order(context.order_ids[sid]['id'])  
                last_sale_price =  context.portfolio.positions[sid].last_sale_price
                
                if ordered.filled != 0:
                    logging('Long Order of %s: Shares %s @ %s ' 
                            % (sid.symbol, ordered.filled, last_sale_price))
                    
                else:
                    logging('Failed to order %s' % sid)
                    
                context.order_ids[sid]['position'] = ordered.filled        
                context.order_ids[sid]['last_sale_price'] = last_sale_price
                context.order_ids[sid]['output'] = False 
                
    handle_exit(context,data)                
        
    

    
    
def my_assign_weights(context, data):
    """
    Assign weights to securities that we want to order.
    """
    pass
 
def my_rebalance1(context,data):
    """
    ポジションクローズ；前日終値までギャップを埋めれば、クローズ。
    16:00 までに埋める事が出来なければ、損切り。
    """
    pass

def my_rebalance2(context,data):
    """
    ポジションクローズ；前日終値までギャップを埋めれば、クローズ。
    エントリーから更に50ポイント落ちれば損切り。
    16:00 までに埋める事が出来なければ、損切り。
    """
    pass


def my_record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    record(spy=data.current(sid(8554),'price'))
 

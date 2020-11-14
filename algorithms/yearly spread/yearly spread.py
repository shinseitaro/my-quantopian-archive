"""
https://www.quantopian.com/posts/futuresymbol-error-symbol-argument-must-be-a-string
これから察するに、動的にsymbolを作ることができないので、
https://www.quantopian.com/posts/how-to-get-future-price-beyond-its-auto-close-date#59f359580669ca0009c4f18f
ここのように最初からマップをつくるという悲しいやり方をしてみたが
うまく行かず


"""
import quantopian.algorithm as algo
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.builtin import USEquityPricing
from quantopian.pipeline.filters import QTradableStocksUS


def initialize(context):
    
    future = "NG"
    context.contract_map = {future_symbol('NGF16') : future_symbol('NGF17')
future_symbol('NGG16') : future_symbol('NGG17')
future_symbol('NGH16') : future_symbol('NGH17')
future_symbol('NGJ16') : future_symbol('NGJ17')
future_symbol('NGK16') : future_symbol('NGK17')
future_symbol('NGM16') : future_symbol('NGM17')
future_symbol('NGN16') : future_symbol('NGN17')
future_symbol('NGQ16') : future_symbol('NGQ17')
future_symbol('NGU16') : future_symbol('NGU17')
future_symbol('NGV16') : future_symbol('NGV17')
future_symbol('NGX16') : future_symbol('NGX17')
future_symbol('NGZ16') : future_symbol('NGZ17')
future_symbol('NGF17') : future_symbol('NGF18')
future_symbol('NGG17') : future_symbol('NGG18')
future_symbol('NGH17') : future_symbol('NGH18')
future_symbol('NGJ17') : future_symbol('NGJ18')
future_symbol('NGK17') : future_symbol('NGK18')
future_symbol('NGM17') : future_symbol('NGM18')
future_symbol('NGN17') : future_symbol('NGN18')
future_symbol('NGQ17') : future_symbol('NGQ18')
future_symbol('NGU17') : future_symbol('NGU18')
future_symbol('NGV17') : future_symbol('NGV18')
future_symbol('NGX17') : future_symbol('NGX18')
future_symbol('NGZ17') : future_symbol('NGZ18')
}

    
    schedule_function(rebalance)

def rebalance(context, data):
    pass 

    
    


def record_vars(context, data):
    """
    Plot variables at the end of each day.
    """
    pass
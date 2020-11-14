"""
Tokyo Quantopian User Group handson Vol4
アルゴリズムその３：クラックスプレッド
QuantopianのTutorialに書いてある
https://www.quantopian.com/tutorials/futures-getting-started#lesson12
"""

import numpy as np
import scipy as sp
from quantopian.algorithm import order_optimal_portfolio
import quantopian.optimize as opt

def initialize(context):

    # Crude Oil つなぎ足
    context.crude_oil = continuous_future('CL', roll='calendar')
    # RBOB Gasoline
    context.gasoline = continuous_future('XB', roll='calendar')
    
    # 移動平均に使う日数。長期と短期。 
    context.long_ma = 65
    context.short_ma = 5
    
    # ポジションを持つときに使うフラグ。ロング、ショートポジションを持っているかどうかを確認。
    context.currently_long_the_spread = False
    context.currently_short_the_spread = False
    
    # リバランス用のスケジュール。毎日、オープン３０分後に実行する。
    schedule_function(func=rebalance_pairs, 
                      date_rule=date_rules.every_day(), 
                      time_rule=time_rules.market_open(minutes=30))
    
    # データの可視化
    schedule_function(record_price, 
                      date_rules.every_day(), 
                      time_rules.market_open())

def rebalance_pairs(context, data):
    """
    CL,XBからZSCOREを取得し、ポートフォリオの比率を作ってオーダー
    """

    # zscoreを取得
    zscore = calc_spread_zscore(context, data)
    
    # ポートフォリオの比率（ウェイト）を算出
    target_weights = get_target_weights(context, data, zscore)
        
    if target_weights:
        # オーダー.
        # opt.TargetWeights(target_weights)　を使うことで、枚数を指定するのではなく、
        # 現在のポートフォリオ価格に対して、〜％を投入するかを指示できます。
        order_optimal_portfolio(
            opt.TargetWeights(target_weights),
            constraints=[]
        )

def calc_spread_zscore(context, data):

    # context.long_ma　で指定した日数、ヒストリカルデータを取得
    prices = data.history([context.crude_oil, 
                           context.gasoline], 
                          'price', 
                          context.long_ma, 
                          '1d')
    
    # pd.Seriese データとして、CLとXbを格納
    cl_price = prices[context.crude_oil]
    xb_price = prices[context.gasoline]
        
    # 前日比率を取得
    # [1:]は初日のNAを外すため
    cl_returns = cl_price.pct_change()[1:]
    xb_returns = xb_price.pct_change()[1:]
    
    # 単回帰直線モデルに過去context.long_ma日分を入れる
    # [-context.long_ma:]　はしなくてもいいはずだが、より間違いがないようにいれている（と思う）
    
    regression = sp.stats.linregress(
        xb_returns[-context.long_ma:],
        cl_returns[-context.long_ma:],
    )
    
    # CLとXBの距離を計算⇐距離というとわかりにくいかも
    spreads = cl_returns - (regression.slope * xb_returns)

    # zscore の計算。spreads[-context.short_ma]　の意図はわからない。spreads[-context.short_ma:] なら多少納得はする。    
    zscore = (np.mean(spreads[-context.short_ma]) - np.mean(spreads)) / np.std(spreads, ddof=1)

    return zscore

def get_target_weights(context, data, zscore):
    """
    zscore を使ってその日の注文数を決める
    zscore < -1.0 なら、CLロング、XBショート
    zscore > 1.0 なら、XBロング、CLショート
    ウェイトは現在のポートフォリオ価格に対して０．５ずつ
    """

    # 現在のコントラクト を取得。（CLF17とか)
    cl_contract, xb_contract = data.current(
        [context.crude_oil, context.gasoline], 
        'contract'
    )
    
    # log.info([cl_contract,xb_contract])
    
    # ウェイトを格納する辞書
    target_weights = {}  

    if context.currently_short_the_spread and zscore < 0.0:
        # 両ウェイトを０にする。
        # 0 でオーダーを入れると、ポジションを持っている場合は、クローズオーダ、持っていない場合は何もしないというオーダーになる
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0

        # flag をFalseに上書き
        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif context.currently_long_the_spread and zscore > 0.0:
        # 同上
        target_weights[cl_contract] = 0
        target_weights[xb_contract] = 0

        context.currently_long_the_spread = False
        context.currently_short_the_spread = False

    elif zscore < -1.0 and (not context.currently_long_the_spread):
        # zsocre が < -1.0 でcurrently_long_the_spreadがFalseの場合
        # CLをロング、XBをショート
        target_weights[cl_contract] = 0.5
        target_weights[xb_contract] = -0.5
        
        context.currently_long_the_spread = True
        context.currently_short_the_spread = False

    elif zscore > 1.0 and (not context.currently_short_the_spread):
        # zsocre が > 1.0 でcurrently_short_the_spreadがFalseの場合
        # XBをロング、CLをショート
        target_weights[cl_contract] = -0.5
        target_weights[xb_contract] = 0.5

        context.currently_long_the_spread = False
        context.currently_short_the_spread = True

    return target_weights

def record_price(context, data):

    # ガソリンと原油の価格を表示
    crude_oil_price = data.current(context.crude_oil, 'price')
    gasoline_price = data.current(context.gasoline, 'price')
      
    # 表示をキレイに行うためにガソリンに４２をかけて表示（他の方法でもOK）
    record(Crude_Oil=crude_oil_price, Gasoline=gasoline_price*42)
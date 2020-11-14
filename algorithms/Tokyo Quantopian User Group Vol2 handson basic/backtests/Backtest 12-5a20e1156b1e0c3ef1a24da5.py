"""
Philip Moris を毎日取引開始時間にひたすら買うだけのアルゴリズム
"""

def initialize(context): 
    """
    # 必須
    アルゴリズムを開始するときに冒頭に一度だけ実行
    スケジュール設定や，銘柄指定など，取引に必要な設定
    """   
    # 取引銘柄
    context.my_asset = sid(35902)
    # 取引株数
    context.no_of_stocks = 10 
    # 取引額
    context.transaction_value = 1000
    # 投資額割合
    context.ratio = 1.0 
    
    # スケジュール設定
    # schedule_function(実行する関数名, 日付ルール, 時間ルール)
    schedule_function(my_rebalance, 
                      date_rules.every_day(),
                      time_rules.market_open())

    # 練習問題：金曜日の取引時間終了時にPMを全部クローズする関数を書いて，スケジュール設定してみましょう．


## その他のスケジュール関数
def before_trading_start(context, data): 
    """
    オプション
    取引開始の45分前（米08：45）に実行
    """
    pass 

def handle_data(context,data): 
    """
    オプション
    取引時間中「毎分」実行
    """
    pass
            

    
## ユーザー定義関数
def my_rebalance(context,data):
    """
    my_asset をロングする
    """
    ## 取引する銘柄が取引制限されていないかどうか
    if data.can_trade(context.my_asset):
        #order(context.my_asset, context.no_of_stocks)
        
        # その他オーダー方法
        #order_value(context.my_asset, context.transaction_value)
        #order_percent(context.my_asset,context.ratio)
        #order_target(context.my_asset, context.no_of_stocks)
        #order_target_value(context.my_asset, context.transaction_value)
        order_target_percent(context.my_asset, context.ratio)

 
    
    

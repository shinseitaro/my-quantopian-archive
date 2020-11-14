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
    # 株数
    context.no_of_stocks = 10 
    
    # スケジュール設定
    # schedule_function(実行する関数名, 日付ルール, 時間ルール)
    schedule_function(my_rebalance, 
                      date_rules.every_day(),
                      time_rules.market_open())
    
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
    ## これから取引したい銘柄が，取引可能かどうかを確認してから取引する．
    if data.can_trade(context.my_asset):
        order(context.my_asset, context.no_of_stocks) 
        
        
 
    
    

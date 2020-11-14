"""
今日のstrategy 
1) 業種の違う銘柄を5つ
2) 毎週月曜日の取引開始時間（米市場は09：30），5つの銘柄を自己資金に対して何％ずつ持つかを決める．
2-1) 配分決定方法
3) start日〜end日まで5銘柄保有する．
"""

import pandas as pd 
def initialize(context):
    """
    initialize()は，このアルゴリズム冒頭に一度だけ実行されます．
    銘柄設定や，スケジュール設定等はここに記述します．
    """

    # 業種の違う銘柄を適当に5つ選出
    # MSFT, UNH, CTAS, JNS, COG
    # Microsoft，ﾕﾅｲﾃｯﾄﾞﾍﾙｽ（Health Care，病院運営），シンタス（企業向けに制服の製造、レンタル、販売），
    # Master Card，キャボット・オイル・アンド・ガス（天然ガス、原油、天然ガス液の探鉱・開発・生産事業）
    context.security_list = [sid(5061), sid(7792), sid(1941), sid(32146), sid(1746)]
    context.long_securities = pd.Series()
    context.short_securities = pd.Series()

    # 毎週月曜日（もしお休みなら，週明け最初の取引日）の，取引開始時（米09：30）にrebalanceを実行する．
    schedule_function(my_rebalance,
                      date_rules.week_start(days_offset=0),
                      time_rules.market_open())

   
    # 毎日取引終了時刻に，my_log，ログ出力
    schedule_function(my_log,
                      date_rules.week_start(days_offset=0),
                      time_rules.market_open())

    # 毎日取引終了時刻に，record_varsを実行して，描画
    schedule_function(my_record_vars,
                      date_rules.every_day(),
                      time_rules.market_close())
    

    
def compute_weights(context, data):
    """
    Compute weights for each security that we want to order.
    それぞれの銘柄をどの程度保有するか，ウェイトを計算する
    """

    # IDE: hist = get_pricing(["MSFT", "UNH", "CTAS", "MA", "COG"], start_date="2017-4-21", end_date="2017-6-2", fields="price")
    # 選出した5つの銘柄の過去30日分の終値を取得
    hist = data.history(context.security_list, 'price', 30, '1d')

    # 10日分/30日分の過去データをそれぞれ変数にいれる．
    prices_10 = hist[-10:]
    prices_30 = hist

    # 平均を出す
    mean_10 = prices_10.mean()
    mean_30 = prices_30.mean()

    # 30日平均と10日平均の差が，30日平均と比べてどの程度違うのか．
    raw_weights = (mean_30 - mean_10) / mean_30

    # それぞれの銘柄を他の銘柄のraw_weightと比較して，ウェイトを作る．
    normalized_weights = raw_weights / raw_weights.abs().sum()

    # normalized_weightsがポジティブの場合は，ロング
    # normalized_weightsがネガティブの場合は，ショートする．
    # この情報を出力するために，contextに情報を入れる
    context.short_securities = normalized_weights.index[normalized_weights < 0]
    context.long_securities = normalized_weights.index[normalized_weights > 0]

    return normalized_weights # pandas.Series 

def my_rebalance(context, data):
    """
    rebalance: ポジション調整．

    """
    weights = compute_weights(context, data)

    # 5銘柄をひとつずつ注文．
    for security in context.security_list:
        # この銘柄が現在トレード出来るかどうか確認．
        if data.can_trade(security):
            # weight は pandas.Series なので，weight[security]でその銘柄のウェイトにアクセス出来る
            order_target_percent(security, weights[security])

def my_record_vars(context, data):
    """
    5銘柄それぞれ
    record()：折れ線グラフを描画．5本まで．
    """
    asset0 = context.security_list[0]
    asset1 = context.security_list[1]
    asset2 = context.security_list[2]
    asset3 = context.security_list[3]
    asset4 = context.security_list[4]
    
    # Record our variables.
    record(asset0.symbol, context.portfolio.positions[asset0].amount * data.current(asset0,'price'),
           asset1.symbol, context.portfolio.positions[asset1].amount * data.current(asset1,'price'),
           asset2.symbol, context.portfolio.positions[asset2].amount * data.current(asset2,'price'),
           asset3.symbol, context.portfolio.positions[asset3].amount * data.current(asset3,'price'),
           asset4.symbol, context.portfolio.positions[asset4].amount * data.current(asset4,'price'),
          )

def my_log(context, data): 
    if context.long_securities.any():
        log.info("This week's longs: " + ", ".join([long_.symbol for long_ in context.long_securities]))
    if context.short_securities.any():
        log.info("This week's shorts: " + ", ".join([short_.symbol for short_ in context.short_securities]))

    
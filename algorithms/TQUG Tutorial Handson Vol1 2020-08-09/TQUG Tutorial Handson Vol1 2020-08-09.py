# Algorithm API インポート
import quantopian.algorithm as algo

# Optimize API インポート
# ファクターを使ってポートフォリオを組み上げていくときに、指定された制約条件を考慮した上で
# リターンを最大化するお手伝いをしてくれるライブラリ
# ユーザーはポジションサイズやレバレッジの制約ルールなどを渡すだけであとはこのライブラリがいい感じに
# ファクターに従ってポートフォリオを構築してくれる
import quantopian.optimize as opt

# Pipeline  インポート
from quantopian.pipeline import Pipeline
from quantopian.pipeline.data.psychsignal import stocktwits
from quantopian.pipeline.factors import SimpleMovingAverage

# built-in universe と Risk API method インポート
from quantopian.pipeline.filters import QTradableStocksUS
from quantopian.pipeline.experimental import risk_loading_pipeline


def initialize(context):
    # 制約パラメータ
   
    context.max_leverage = 1.0
    context.max_pos_size = 0.015
    context.max_turnover = 0.95

    # data pipelines を取り付ける
    algo.attach_pipeline(
        make_pipeline(),
        'data_pipe'
    )
    algo.attach_pipeline(
        risk_loading_pipeline(),
        'risk_pipe'
    )

    # rebalance 関数をスケジュール
    algo.schedule_function(
        rebalance,
        algo.date_rules.week_start(),
        algo.time_rules.market_open(),
    )


def before_trading_start(context, data):
    # pipeline出力を取得し、contextに格納する。
    context.pipeline_data = algo.pipeline_output('data_pipe')

    context.risk_factor_betas = algo.pipeline_output('risk_pipe')


# Pipeline definition
# Researchで構築したデータパイプラインをアルゴリズムに統合
def make_pipeline():

    sentiment_score = SimpleMovingAverage(
        inputs=[stocktwits.bull_minus_bear],
        window_length=3,
        # filtering 
        mask=QTradableStocksUS() 
    )

    return Pipeline(
        columns={
            'sentiment_score': sentiment_score,
        },
        # つまり、sentiment_scoreが null ではない銘柄は全部投資対象に入れる
        screen=sentiment_score.notnull()
    )


def rebalance(context, data):
    # pipeline 出力から alpha を取り出す
    alpha = context.pipeline_data.sentiment_score

    if not alpha.empty:
        # MaximizeAlpha objective 作成
        # alpha（つまりsentiment_score）でウェイトをつける
        objective = opt.MaximizeAlpha(alpha)

        # ポジションサイズ制約
        # with_equal_bounds を使うと、どんなに小さなalphaであってもポートフォリオに組み込む
        # という設定。つまり大きなalphaの銘柄に大きく偏ったポートフォリオにならない。
        constrain_pos_size = opt.PositionConcentration.with_equal_bounds(
            -context.max_pos_size, # min
            context.max_pos_size # max 
        )

        # ターゲットポートフォリオレバレッジ制約
        # ポートフォリオのウェイトが、max_leverage 以下になるように制約
        max_leverage = opt.MaxGrossExposure(context.max_leverage)

        # ロング（買い持ち）とショート（売り持ち）のサイズをだいたい同じに合わせる
        dollar_neutral = opt.DollarNeutral()

        # ポートフォリオの出来高の制約
        # MaxTurnoverに関するドキュメントがないのでなんだか良くわからない
        # どうしてDocがないの？という質問がForumにあった。
        # https://www.quantopian.com/posts/optimize-api-maxturnover-constraint-is-it-supported#5a3be89765ca177fe452db6d
        # 答えも不明瞭
        max_turnover = opt.MaxTurnover(context.max_turnover)

        # ターゲットポートフォリオのリスクエクスポージャーを制限する。
        
        # 2casa さんのありがたい教えによると（https://github.com/tokyoquantopian/TQUG6_20181215/blob/master/TQUG6_04-01.%E3%82%A2%E3%83%AB%E3%82%B4%E3%83%AA%E3%82%BA%E3%83%A0%E3%81%AB%E3%82%88%E3%82%8B%E3%83%90%E3%83%83%E3%82%AF%E3%83%86%E3%82%B9%E3%83%88.ipynb)
        # アルファ以外のファクターを取らないようにすることで、純粋に自分が意図するファクターにのみ
        # 投資を行っていることを保証するため、リスクモデルエクスポージャ制約を入れる
        # ということ。
        # デフォルト値は、セクターエクスポージャーの最大値は0.2
        # スタイルエクスポージャーの最大値は0.4
        factor_risk_constraints = opt.experimental.RiskModelExposure(
            context.risk_factor_betas,
            # 将来のリリースで RiskModelExposure のデフォルトが変更された場合にも対応。デフォルト設定もopt.Newest
            version=opt.Newest 
        )

        # 目的関数と制約リストを使ってポートフォリオをリバランスする
        algo.order_optimal_portfolio(
            objective=objective,
            constraints=[
                constrain_pos_size,
                max_leverage,
                dollar_neutral,
                max_turnover,
                factor_risk_constraints,
            ]
        )
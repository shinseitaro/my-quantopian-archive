"""
このアルゴリズムは、Lecture38 Example: Long-Short Equity Algorithm のコメント
を日本語化したものです。コード自体には一切手を加えていません。
04-02以降で、少しづつ手を加えていきます。
<OriginalCodeは以下でCloneできます>
https://www.quantopian.com/lectures/example-long-short-equity-algorithm
"""

import quantopian.algorithm as algo
import quantopian.optimize as opt
from quantopian.pipeline import Pipeline
from quantopian.pipeline.factors import SimpleMovingAverage

from quantopian.pipeline.filters import QTradableStocksUS
from quantopian.pipeline.experimental import risk_loading_pipeline

from quantopian.pipeline.data.psychsignal import stocktwits
from quantopian.pipeline.data import Fundamentals

# 最適化制約パラメータ 
# 最大グロスレバレッジ（例えば $10Mの想定元本のうち、$5Mをロング、$5Mをショートしたらレバレッジは1.0)
# グロスレバレッジ　＝（ロング＋ショート）/（想定元本）
MAX_GROSS_LEVERAGE = 1.0
# 合計ポジション
TOTAL_POSITIONS = 600

# １銘柄当たりの最大保有ポジションサイズの制約。
# 最大値を小さくしすぎると、注文最適化時に影響を与える可能性がある。
MAX_SHORT_POSITION_SIZE = 2.0 / TOTAL_POSITIONS
MAX_LONG_POSITION_SIZE = 2.0 / TOTAL_POSITIONS


def initialize(context):
    """
    バックテスト開始時に呼び出される、アルゴリズムの中心となるメイン関数を、Quantopianでは
    initialize関数と呼びます。
    パラメータ
    ----------
    context : アルゴリズムコンテキスト
        バックテストの状態を保存するために用いられるオブジェクト。
        contextは、initialize, before_trading_start, handle_data, scedule_functionから呼び
        出される全ての関数に渡されます。
        contextは現在のポジションに関する情報を回収ために用いることのできるポートフォリオ特性を提供します。
    """
    
    # パイプラインをアルゴリズムに取り込む（notebookでいうところのrun_pipelineに相当）
    # run_pipelineと違うのは、start_dateとend_dateが引数に存在しない点！
    algo.attach_pipeline(make_pipeline(), 'long_short_equity_template')

    # リスクモデルのファクターを構成するパイプラインをアルゴリズムに取り込む
    algo.attach_pipeline(risk_loading_pipeline(), 'risk_factors')

    # アルゴリズムの動作スケジュールを決定（ポートフォリオのリバランスを【週次】実行している）
    algo.schedule_function(func=rebalance,
                           date_rule=algo.date_rules.week_start(),
                           time_rule=algo.time_rules.market_open(hours=0, minutes=30),
                           half_days=True)

    # アルゴリズムの動作スケジュールを決定（ポートフォリオの状態を営業日終了時点で評価）
    algo.schedule_function(func=record_vars,
                           date_rule=algo.date_rules.every_day(),
                           time_rule=algo.time_rules.market_close(),
                           half_days=True)


def make_pipeline():
    """
    パイプラインを作成して返す関数
    
    パイプラインの構築は、NotebookとAlgorithmの両方で動作させることができるので、Notebook
    で検証したアルファをコピペしてアルゴリズムで使うことが可能。
    【Execise】make_pipeline をNotebookにコピーして動作することを確認しよう。

    Returns
    -------
    pipe : Pipeline
        Represents computation we would like to perform on the assets that make
        it through the pipeline screen.
    """
    
    # ファクターその１：バリューファクター（この時点では生データ）
    value = Fundamentals.ebit.latest / Fundamentals.enterprise_value.latest
    # ファクターその２：クオリティファクター（ROE）（この時点では生データ）
    quality = Fundamentals.roe.latest
    # ファクターその３：センチメントファクター（この時点では生データ）
    sentiment_score = SimpleMovingAverage(
        inputs=[stocktwits.bull_minus_bear],
        window_length=3,
    )
    
    # ユニバースはQTradableStockUS()を使う
    universe = QTradableStocksUS()
    
    # 生データからwinsorizeによってスコア化
    # バリューファクタースコア
    value_winsorized = value.winsorize(min_percentile=0.05, max_percentile=0.95)
    # クオリティファクタースコア
    quality_winsorized = quality.winsorize(min_percentile=0.05, max_percentile=0.95)
    # センチメントファクタースコア
    sentiment_score_winsorized = sentiment_score.winsorize(min_percentile=0.05, max_percentile=0.95)

    # ３つのファクターを合成して、１つのアルファを構成
    # 【Execise】ファクターの合成方法を変えてバックテストしてみよう！
    combined_factor = (
        value_winsorized.zscore() + 
        quality_winsorized.zscore() + 
        sentiment_score_winsorized.zscore()
    )

    # QTradableStocks構成銘柄の中から、さらに、combined_fatctorが上位のものだけを取得
    longs = combined_factor.top(TOTAL_POSITIONS//2, mask=universe)
    # QTradableStocks構成銘柄の中から、さらに、combined_fatctorが下位のものだけを取得
    shorts = combined_factor.bottom(TOTAL_POSITIONS//2, mask=universe)
    
    # longとshortsの構成銘柄を組み合わせることで、最終的なフィルタを構築
    long_short_screen = (longs | shorts)

    # パイプラインを作成
    pipe = Pipeline(
        columns={
            'longs': longs,
            'shorts': shorts,
            'combined_factor': combined_factor
        },
        # フィルタリング（longs または shorts に含まれる銘柄でフィルタリング）
        screen=long_short_screen
    )
    # 作成したパイプラインを返して終了
    return pipe


def before_trading_start(context, data):
    """
    毎営業日の取引開始前に自動的に呼び出される補助関数
    （initializeと同様）

    Parameters
    ----------
    context : AlgorithmContext
        See description above.
    data : BarData
        An object that provides methods to get price and volume data, check
        whether a security exists, and check the last time a security traded.
    """
    # 'long_short_equity_template'　pipeline をcontextのメンバオブジェクトとして追加
    context.pipeline_data = algo.pipeline_output('long_short_equity_template')

    # 'risk_factors' pipelineをcontextのメンバオブジェクトとして追加
    context.risk_loadings = algo.pipeline_output('risk_factors')


def record_vars(context, data):
    """
    initalize関数内部で定義した、scedule_functionによって毎営業日終了後に呼び出される
    関数

    Parameters
    ----------
    context : AlgorithmContext
        See description above.
    data : BarData
        See description above.
    """
    # ポートフォリオの構成銘柄数をnum_positionとして記録する
    algo.record(num_positions=len(context.portfolio.positions))
    # 【Execise】ポートフォリオ構成銘柄数以外にレポートしてほしい情報があれば追加してみよう



def rebalance(context, data):
    """
    initialize関数内部で定義した、schedule_functionによって毎週月曜日に実行される関数。
    before_trading_start()関数によって、'long_short_equity_template'がcontextに
    予めセットされている。


    Parameters
    ----------
    context : AlgorithmContext
        See description above.
    data : BarData
        See description above.
    """
    # contextからパイプラインデータを取り出す（ロングショート）
    pipeline_data = context.pipeline_data
    # contextからパイプラインデータを取り出す（リスクモデルデータ）
    risk_loadings = context.risk_loadings

    # 最適化APIの目的関数を定義する。
    # ここではMaximizeAlpha（アルファ最大化）という組み込みの目的関数を利用する。
    # combined_factorはmake_pipeline()の中でzscoreの合成値として定義されているので
    # その値は、正または負の値をとる。
    # 正負両方の値を取り得るアルファを使って、アルファを最大化するためには、
    # アルファ＞0 の銘柄ならば買い（正のアルファスコア　x　正のポジション　＝　正）
    # アルファ＜0 の銘柄ならば売り（負のアルファスコア　x　負のポジション　＝　正）
    # となることがアルファ最大化に繋がるはずである。この目的関数を指定することで、自動的に
    # 売り判断と買い判断を行っていることと等しくなる。
    objective = opt.MaximizeAlpha(pipeline_data.combined_factor)

    # 目的関数最大化（アルファ最大化）をしつつ、守るべき制約条件をセットするリストの初期化
    constraints = []
    # 最大グロスレバレッジ制約をセット
    constraints.append(opt.MaxGrossExposure(MAX_GROSS_LEVERAGE))

    # ドルニュートラル制約（ロングポジションの額と、ショートポジションの額が一致）
    constraints.append(opt.DollarNeutral())

    # リスクモデルエクスポージャ制約
    # アルファ以外のファクターを取らないようにすることで、純粋に自分が意図するファクターにのみ
    # 投資を行っていることを保証するため、リスクモデルエクスポージャ制約を入れる
    # 【Excesice】リスクモデルエクスポージャ制約がない場合のパフォーマンスはどうなるか？
    # また、そのときのriskエクスポージャが、制約アリのときと比べてどのように変化しているか？
    neutralize_risk_factors = opt.experimental.RiskModelExposure(
        risk_model_loadings=risk_loadings,
        version=0
    )
    constraints.append(neutralize_risk_factors)

    # 投資比率制約をセット。
    # 今回のアルゴリズムの場合、
    # 'long_short_equity_template'パイプラインにデータが含まれる時点で、必ず売買を行う
    # ようにしたい（らしい）。全ての銘柄は、一定の範囲内でポジションを持つように制約をセット
    # このようにすることで、アルファの絶対値が小さい(ゼロ近辺)の銘柄についても、必ずポジション
    # を持つことが保証される。言い換えればアルファの絶対値が大きい銘柄に投資を集中させない仕組み
    constraints.append(
        opt.PositionConcentration.with_equal_bounds(
            min=-MAX_SHORT_POSITION_SIZE,
            max=MAX_LONG_POSITION_SIZE
        ))
    
    # レッツ発注！（制約を満たしつつ、目的関数を最大化するように注文を自動作成するなんて素敵やん）
    algo.order_optimal_portfolio(
        objective=objective,
        constraints=constraints
    )
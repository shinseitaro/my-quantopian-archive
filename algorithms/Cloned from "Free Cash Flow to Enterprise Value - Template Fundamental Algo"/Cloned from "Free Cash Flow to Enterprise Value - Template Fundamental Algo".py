import numpy as np
import quantopian.algorithm as algo
import quantopian.optimize as opt
from quantopian.pipeline import Pipeline
from quantopian.pipeline.factors import CustomFactor
from quantopian.pipeline.filters import QTradableStocksUS
from quantopian.pipeline.data import Fundamentals

ZSCORE_FILTER = 3 # Maximum number of standard deviations to include before counting as outliers
ZERO_FILTER = 0.001 # Minimum weight we allow before dropping security
        

def initialize(context):
    
    algo.attach_pipeline(make_pipeline(), 'alpha_factor_template')

    # Schedule our rebalance function
    algo.schedule_function(func=rebalance,
                           date_rule=algo.date_rules.week_start(),
                           time_rule=algo.time_rules.market_open(),
                           half_days=True)

    # Record our portfolio variables at the end of day
    algo.schedule_function(func=record_vars,
                           date_rule=algo.date_rules.every_day(),
                           time_rule=algo.time_rules.market_close(),
                           half_days=True)


def make_pipeline():
    # Setting up the variables
    alpha_factor = (Fundamentals.fcf_per_share.latest * Fundamentals.shares_outstanding.latest) / \
                    Fundamentals.enterprise_value.latest

    # Standardized logic for each input factor after this point
    alpha_w = alpha_factor.winsorize(min_percentile=0.02,
                                     max_percentile=0.98,
                                     mask=QTradableStocksUS() & alpha_factor.isfinite())

    alpha_z = alpha_w.zscore()
    alpha_weight = alpha_z / 100.0

    outlier_filter = alpha_z.abs() < 3
    zero_filter = alpha_weight.abs() > 0.001

    universe = QTradableStocksUS() & \
               outlier_filter & \
               zero_filter

    pipe = Pipeline(
        columns={
            'alpha_weight': alpha_weight
        },
        screen=universe
    )
    return pipe


def before_trading_start(context, data):
    context.pipeline_data = algo.pipeline_output('alpha_factor_template')


def record_vars(context, data):
    # Plot the number of positions over time.
    algo.record(num_positions=len(context.portfolio.positions))
    algo.record(leverage=context.account.leverage)

    
def rebalance(context, data):
    # Retrieve pipeline output
    pipeline_data = context.pipeline_data
    
    alpha_weight = pipeline_data['alpha_weight']
    alpha_weight_norm = alpha_weight / alpha_weight.abs().sum()


    objective = opt.TargetWeights(alpha_weight_norm)

    # No constraints currently
    constraints = []
    
    algo.order_optimal_portfolio(
        objective=objective,
        constraints=constraints
    )
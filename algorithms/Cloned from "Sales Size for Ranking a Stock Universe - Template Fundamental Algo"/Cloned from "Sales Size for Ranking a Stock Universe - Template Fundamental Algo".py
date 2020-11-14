import numpy as np
import quantopian.algorithm as algo
import quantopian.optimize as opt
from quantopian.pipeline import Pipeline
from quantopian.pipeline.filters import QTradableStocksUS
from quantopian.pipeline.data import factset
 
OUTLIER_THRESHOLD = 3 # Maximum zscore that is not an outlier
ZERO_THRESHOLD = 0.1 # Minimum zscore we allow before dropping security
 
 
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
    # marketcap に対して売上が比較的小さい会社を買う（過去一年）
    
    revenue_ltm = factset.Fundamentals.sales_ltm.latest/\
                  factset.Fundamentals.mkt_val_public.latest
    roe = factset.Fundamentals.roe_qf
    alpha_factor = revenue_ltm + roe
    alpha_factor = revenue_ltm.log()
    
    # Standardized logic for each input factor after this point
    alpha_w = alpha_factor.winsorize(
        min_percentile=0.10,
        max_percentile=0.98,
        mask=QTradableStocksUS() & (revenue_ltm > 0) & alpha_factor.isfinite()
    )
    alpha_z = alpha_w.zscore()
    
    outlier_filter = alpha_z.abs() < OUTLIER_THRESHOLD
    non_zero_filter = alpha_z.abs() > ZERO_THRESHOLD
    
    universe = QTradableStocksUS() & \
               outlier_filter & \
               non_zero_filter
 
    pipe = Pipeline(
        columns={
            'alpha_z': alpha_z,
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
    
    alpha_weight = pipeline_data['alpha_z']
    alpha_weight_norm = alpha_weight / alpha_weight.abs().sum()
 
    objective = opt.TargetWeights(alpha_weight_norm)
 
    # No constraints, want all assets allocated to
    constraints = []
    
    algo.order_optimal_portfolio(
        objective=objective,
        constraints=constraints
    )
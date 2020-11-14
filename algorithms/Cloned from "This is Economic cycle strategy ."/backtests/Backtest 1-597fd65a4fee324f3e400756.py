def initialize(context):
    context.SPY =  symbol('SPY') #SPY= S&P ETF
    context.XLK =  symbol('XLK') #XLK= technology ETF
    context.XLY =  symbol('XLY') #XLY= Consumer goods ETF
    context.XLE =  symbol('XLE') #XLE= energy ETF
    context.XLU =  symbol('XLU') #XLU= Utilities ETF
   
    schedule_function(rebalance,date_rules.every_day())
    
def before_trading_start(context, data):
    context.num_of_assets = len(context.portfolio.positions)
    print [(sid.symbol, context.portfolio.positions[sid].amount) for sid in context.portfolio.positions]
        
        
        

def rebalance(context, data):
    Benchmark_average_50 = data.history(context.SPY,'price',50,'1d')[:-1].mean()
    
    Defensive_average1_250 = data.history(context.XLE,'price',250,'1d').pct_change()[:-1].mean()
    Defensive_average2_250 = data.history(context.XLU,'price',250,'1d').pct_change()[:-1].mean()
    Growth_average1_50 = data.history(context.XLK,'price',50,'1d').pct_change()[:-1].mean()
    Growth_average2_50 = data.history(context.XLY,'price',50,'1d').pct_change()[:-1].mean()

    current_spy = data.current(context.SPY, 'price')
    record(Defensive_average1_250=Defensive_average1_250,Growth_average1_50=Growth_average1_50 )
    
    if current_spy > Benchmark_average_50:
        if data.can_trade(context.XLK): 
            order_target_percent(context.XLK,0.25)
        elif context.portfolio.positions[context.XLK].amount < 0:
            order_target_percent(context.XLK,0)
           
    if current_spy < Benchmark_average_50:
        if data.can_trade(context.XLK): 
            order_target_percent(context.XLK,-0.25)        
        elif context.portfolio.positions[context.XLK].amount > 0:
            order_target_percent(context.XLK,0)
            
    if (Growth_average1_50 > Defensive_average1_250) or (Growth_average2_50 > Defensive_average2_250):  
        if data.can_trade(context.SPY): 
            order_target_percent(context.SPY,0.25) 
        elif context.portfolio.positions[context.SPY].amount < 0:
            order_target_percent(context.SPY,0) 
    if (Growth_average1_50 < Defensive_average1_250) or (Growth_average2_50 < Defensive_average2_250):          
        if data.can_trade(context.SPY): 
            order_target_percent(context.SPY,-0.25) 
        elif context.portfolio.positions[context.SPY].amount > 0:
            order_target_percent(context.SPY,0) 
        
        
        
        
        
   
# def rebalance(context,data):
    
#     Benchmark_average_50 = data.history(context.SPY,'price',50,'1d')[:-1].mean()
#     Benchmark_price = (context.SPY,'price')
    
#     Growth_average1_50 = data.history(context.XLK,'price',50,'1d')[:-1].mean()
#     Growth_average2_50 = data.history(context.XLY,'price',50,'1d')[:-1].mean()
        
#     Defensive_average1_250 = data.history(context.XLE,'price',250,'1d')[:-1].mean()
#     Defensive_average2_250 = data.history(context.XLU,'price',250,'1d')[:-1].mean()
    
#     if data.can_trade(context.SPY):
#        if data.can_trade(context.XLK):
#           if data.can_trade(context.XLY):
#              if data.can_trade(context.XLE):
#                 if data.can_trade(context.XLU):
                    
#                   if Benchmark_average_50 < Benchmark_price:
#                      order_target_percent(context.XLK,0.25)

#                   if Benchmark_average_50 > Benchmark_price:
#                      order_target_percent(context.XLK,-0.25)              
            
#                   if Benchmark_average_50 < Benchmark_price:
#                      order_target_percent(context.XLY,0.25)
            
#                   if Benchmark_average_50 > Benchmark_price:
#                      order_target_percent(context.XLY,-0.25)   
                        
                        
#                   if Growth_average1_50 > Defensive_average1_250:     
#                      order_target_percent(context.SPY,0.25) 
                   
#                   if Growth_average1_50 < Defensive_average2_250:
#                      order_target_percent(context.SPY,-0.25)
                    
#                   if Growth_average2_50 > Defensive_average2_250:
#                      order_target_percent(context.SPY,0.25)
                        
#                   if Growth_average2_50 < Defensive_average2_250:
#                      order_target_percent(context.SPY,-0.25)
              
#                   #if Growth_average1_50 > Defensive_average1_250:
#                      #order_target_percent(context.SPY,0) # 0.0625 = 0.5/8
            
#                   #if Growth_average1_50 < Defensive_average1_250:
#                      #order_target_percent(context.SPY,-0.125)
                        
#                   #if Growth_average1_50 > Defensive_average2_250:
#                      #order_target_percent(context.SPY,0)
                        
#                   #if Growth_average1_50 < Defensive_average2_250:
#                      #order_target_percent(context.SPY,-0.125)
                        
#                   #if Growth_average2_50 > Defensive_average1_250:
#                      #order_target_percent(context.SPY,0)
                        
#                   #if Growth_average2_50 < Defensive_average1_250:
#                     # order_target_percent(context.SPY,-0.125)
            
#                   #if Growth_average2_50 > Defensive_average2_250:
#                      #order_target_percent(context.SPY,0) 
            
#                   #if Growth_average2_50 < Defensive_average2_250:
#                      #order_target_percent(context.SPY,-0.125) 
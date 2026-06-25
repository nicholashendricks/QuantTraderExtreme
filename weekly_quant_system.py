import yfinance as yf
import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt

def run_analysis(ticker, start_date, end_date):
    print(f"Fetching data for {ticker}...")
    # 1. yfinance -> pandas
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # Flatten MultiIndex columns if they exist (fix for newer yfinance versions)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty:
        print("No data found.")
        return

    # Convert yfinance data to backtrader format
    bt_data = bt.feeds.PandasData(dataname=data)

    # 2. Setup Backtrader Cerebro engine
    cerebro = bt.Cerebro()
    cerebro.adddata(bt_data)

    # Add a simple strategy (Example: Simple Moving Average Crossover)
    class SmaStrategy(bt.Strategy):
        def __init__(self):
            self.sma = bt.indicators.SimpleMovingAverage(period=20)
            self.signal = "HOLD"

        def next(self):
            if not self.position:
                if self.data.close[0] > self.sma[0]:
                    self.buy()
                    self.signal = "BUY"
            else:
                if self.data.close[0] < self.sma[0]:
                    self.sell()
                    self.signal = "SELL"

    cerebro.addstrategy(SmaStrategy)
    
    # Set initial cash
    cerebro.broker.setcash(10000.0)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    strategies = cerebro.run()
    strat = strategies[0]
    
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
    
    # Save the final signal to CSV as required by Step 5
    signal_df = pd.DataFrame([{"ticker": ticker, "signal": strat.signal}])
    signal_df.to_csv("weekly_target_trade.csv", index=False)
    print("Signal saved to weekly_target_trade.csv")

    # 3. Plot results
    cerebro.plot()

if __name__ == "__main__":
    # Example: Analyze SPY as mentioned in Startup.md
    run_analysis("SPY", "2018-01-01", "2026-06-25")
import yfinance as yf
import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt

def run_analysis(ticker, start_date, end_date):
    print(f"Fetching data for {ticker}...")
    # 1. yfinance -> pandas
    data = yf.download(ticker, start=start_date, end=end_date)
    
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

        def next(self):
            if not self.position:
                if self.data.close[0] > self.sma[0]:
                    self.buy()
            else:
                if self.data.close[0] < self.sma[0]:
                    self.sell()

    cerebro.addstrategy(SmaStrategy)
    
    # Set initial cash
    cerebro.broker.setcash(10000.0)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    cerebro.run()
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")

    # 3. Plot results
    cerebro.plot()

if __name__ == "__main__":
    # Example: Analyze Apple (AAPL)
    run_analysis("AAPL", "2023-01-01", "2023-12-31")
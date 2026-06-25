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

def get_params_from_csv():
    """
    Fetches ticker, start_date, and end_date from a local input.csv file.
    """
    try:
        df = pd.read_csv("input.csv")
        ticker = df.iloc[0]['ticker']
        start_date = df.iloc[0]['start_date']
        end_date = df.iloc[0]['end_date']
        return ticker, start_date, end_date
    except Exception as e:
        print(f"Error reading parameters from input.csv: {e}")
        print("Falling back to default parameters.")
        return "SPY", "2018-01-01", "2026-06-25"

if __name__ == "__main__":
    # Fetch parameters dynamically from input.csv
    ticker, start, end = get_params_from_csv()
    print(f"Using parameters: Ticker={ticker}, Start={start}, End={end}")
    run_analysis(ticker, start, end)

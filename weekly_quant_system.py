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
    
    # 3. Plot results
    cerebro.plot()

    return strat.signal

def get_params_from_csv():
    """
    Fetches all tickers, start_dates, and end_dates from a local input.csv file.
    """
    try:
        return pd.read_csv("input.csv")
    except Exception as e:
        print(f"Error reading parameters from input.csv: {e}")
        print("Falling back to default parameters.")
        return pd.DataFrame([{"ticker": "SPY", "start_date": "2018-01-01", "end_date": "2026-06-25"}])

if __name__ == "__main__":
    # Fetch parameters dynamically from input.csv
    params_df = get_params_from_csv()
    
    all_signals = []
    
    for index, row in params_df.iterrows():
        ticker = row['ticker']
        start = row['start_date']
        end = row['end_date']
        print(f"\n--- Analyzing {ticker} (Start: {start}, End: {end}) ---")
        
        signal = run_analysis(ticker, start, end)
        if signal:
            all_signals.append({"ticker": ticker, "signal": signal})
    
    # Save all signals to CSV
    if all_signals:
        results_df = pd.DataFrame(all_signals)
        results_df.to_csv("weekly_target_trade.csv", index=False)
        print("\nAll signals saved to weekly_target_trade.csv")

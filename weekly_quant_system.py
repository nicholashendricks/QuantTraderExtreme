import yfinance as yf
import pandas as pd
import backtrader as bt
import matplotlib.pyplot as plt
import argparse
from datetime import date

def run_analysis(ticker, start_date, end_date, show_plot=False):
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
            self.strength = 0.0

        def next(self):
            close = self.data.close[0]
            sma = self.sma[0]
            
            if not self.position:
                if close > sma:
                    self.buy()
                    self.signal = "BUY"
                    self.strength = (close - sma) / sma
                else:
                    self.signal = "HOLD"
                    self.strength = 0.0
            else:
                if close < sma:
                    self.sell()
                    self.signal = "SELL"
                    self.strength = (sma - close) / sma
                else:
                    self.signal = "BUY" # Maintain BUY signal if still above SMA
                    self.strength = (close - sma) / sma

    cerebro.addstrategy(SmaStrategy)
    
    # Set initial cash
    cerebro.broker.setcash(10000.0)

    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    strategies = cerebro.run()
    strat = strategies[0]
    
    print(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
    
    # 3. Plot results
    if show_plot:
        cerebro.plot()

    return strat.signal, strat.strength

def get_params_from_csv():
    """
    Fetches all tickers from a local input.csv file.
    """
    try:
        return pd.read_csv("input.csv")
    except Exception as e:
        print(f"Error reading parameters from input.csv: {e}")
        print("Falling back to default parameters.")
        return pd.DataFrame([{"ticker": "SPY"}])

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Weekly Quant System Analysis")
    parser.add_argument("--graph", action="store_true", help="Show plots for the analysis")
    args = parser.parse_args()

    # Fetch parameters dynamically from input.csv
    params_df = get_params_from_csv()
    
    all_signals = []
    
    start = "2018-01-01"
    end = date.today().strftime('%Y-%m-%d')

    for index, row in params_df.iterrows():
        ticker = row['ticker']
        print(f"\n--- Analyzing {ticker} (Start: {start}, End: {end}) ---")
        
        signal, strength = run_analysis(ticker, start, end, show_plot=args.graph)
        if signal:
            all_signals.append({"ticker": ticker, "signal": signal, "strength": round(strength, 4)})
    
    # Save all signals to CSV
    if all_signals:
        results_df = pd.DataFrame(all_signals)
        results_df.to_csv("weekly_target_trade.csv", index=False)
        print("\nAll signals saved to weekly_target_trade.csv")

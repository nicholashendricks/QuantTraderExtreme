import yfinance as yf
import pandas as pd
import argparse
from datetime import date

def run_analysis(ticker, start_date, end_date):
    """
    Simple SMA crossover strategy using pandas (no backtrader dependency).
    Returns (signal, strength) based on the last bar's close vs SMA-20.
    """
    print(f"Fetching data for {ticker}...")
    data = yf.download(ticker, start=start_date, end=end_date)

    # Flatten MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or len(data) < 20:
        print(f"  Insufficient data for {ticker}.")
        return ("HOLD", 0.0)

    # Calculate 20-period SMA
    close = data["Close"]
    sma20 = close.rolling(window=20).mean()

    # Get the last values
    last_close = close.iloc[-1]
    last_sma = sma20.iloc[-1]

    strength = (last_close - last_sma) / last_sma

    if pd.isna(strength):
        return ("HOLD", 0.0)

    if last_close > last_sma:
        return ("BUY", round(strength, 6))
    else:
        return ("HOLD", 0.0)


def get_params_from_csv():
    """Fetches all tickers from a local input.csv file."""
    try:
        return pd.read_csv("input.csv")
    except Exception as e:
        print(f"Error reading parameters from input.csv: {e}")
        print("Falling back to default parameters.")
        return pd.DataFrame([{"ticker": "SPY"}])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Weekly Quant System Analysis")
    args = parser.parse_args()

    params_df = get_params_from_csv()
    all_signals = []

    start = "2018-01-01"
    end = date.today().strftime('%Y-%m-%d')

    for index, row in params_df.iterrows():
        ticker = row["ticker"]
        print(f"\n--- Analyzing {ticker} (Start: {start}, End: {end}) ---")

        signal, strength = run_analysis(ticker, start, end)
        if signal:
            all_signals.append({"ticker": ticker, "signal": signal, "strength": round(strength, 4)})

    # Save all signals to CSV
    if all_signals:
        results_df = pd.DataFrame(all_signals)
        results_df.to_csv("weekly_target_trade.csv", index=False)
        print("\nAll signals saved to weekly_target_trade.csv")
import yfinance as yf
import pandas as pd
import argparse
from datetime import date


def run_analysis(ticker, start_date, end_date):
    """
    Simulates the original backtrader SMA crossover strategy using pandas.
    Tracks position state across bars to reproduce BUY/SELL/HOLD logic.
    Returns (signal, strength) based on the last bar.
    """
    print(f"Fetching data for {ticker}...")
    data = yf.download(ticker, start=start_date, end=end_date)

    # Flatten MultiIndex columns if present
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or len(data) < 20:
        print(f"  Insufficient data for {ticker}.")
        return ("HOLD", 0.0)

    close = data["Close"]
    sma20 = close.rolling(window=20).mean()

    # Replicate backtrader SmaStrategy.next() logic by iterating each bar
    in_position = False
    signal = "HOLD"
    strength = 0.0

    for i in range(len(data)):
        c = close.iloc[i]
        s = sma20.iloc[i]

        if pd.isna(s):
            continue  # no SMA yet, skip

        if not in_position:
            if c > s:
                in_position = True
                signal = "BUY"
                strength = (c - s) / s
            else:
                signal = "HOLD"
                strength = 0.0
        else:
            if c < s:
                in_position = False
                signal = "SELL"
                strength = (s - c) / s
            else:
                signal = "BUY"
                strength = (c - s) / s

    return (signal, strength)


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
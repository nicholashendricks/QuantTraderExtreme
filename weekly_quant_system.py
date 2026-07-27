import argparse
from datetime import date
import pandas as pd
import yfinance as yf


def run_analysis(ticker, start_date, end_date, window=20, use_weekly=False):
    """Vectorized quantitative strategy evaluator.

    Calculates SMA crossover signals, position states, and normalized z-score
    strength without iterative loops.
    """
    print(f"Fetching data for {ticker}...")
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
    except Exception as e:
        print(f" Failed to fetch data for {ticker}: {e}")
        return None

    # Flatten MultiIndex columns if present (handles yfinance API updates)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if data.empty or len(data) < window + 1:
        print(f" Insufficient data points for {ticker}.")
        return None

    # Optional: Resample daily data to weekly Friday-close bars
    if use_weekly:
        data = data.resample('W-FRI').agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum',
        }).dropna()

    close = data['Close']

    # Rolling calculations
    sma = close.rolling(window=window).mean()
    std = close.rolling(window=window).std()

    # Normalized distance metric (Z-Score / Standard Deviations from SMA)
    z_score = (close - sma) / std

    # Vectorized state evaluation
    above_sma = close > sma

    # Track in-position state chronologically across bars
    in_position = above_sma.ffill().fillna(False)

    # Detect crossovers between current and previous bar
    prev_in_position = in_position.shift(1).fillna(False)
    buy_crossover = in_position & (~prev_in_position)
    sell_crossover = (~in_position) & prev_in_position

    # Extract metrics from the most recent completed bar
    latest_buy_cross = buy_crossover.iloc[-1]
    latest_sell_cross = sell_crossover.iloc[-1]
    latest_in_position = in_position.iloc[-1]
    latest_z = z_score.iloc[-1]
    latest_close = close.iloc[-1]
    latest_sma = sma.iloc[-1]

    # Assign actionable signals
    if latest_buy_cross:
        signal = 'NEW_BUY'
    elif latest_sell_cross:
        signal = 'NEW_SELL'
    elif latest_in_position:
        signal = 'HOLD_LONG'
    else:
        signal = 'HOLD_CASH'

    # Unbounded percentage distance (retained for backward compatibility)
    pct_dist = (latest_close - latest_sma) / latest_sma

    return {
        'ticker': ticker,
        'evaluation_date': data.index[-1].strftime('%Y-%m-%d'),
        'signal': signal,
        'z_score_strength': round(float(latest_z), 2) if pd.notna(latest_z) else 0.0,
        'pct_distance': round(float(pct_dist), 4),
        'close': round(float(latest_close), 2),
        'sma_20': round(float(latest_sma), 2),
    }


def get_params_from_csv():
    """Fetches target tickers from local input.csv or defaults to SPY."""
    try:
        df = pd.read_csv('input.csv')
        if 'ticker' in df.columns:
            return df['ticker'].dropna().tolist()
        else:
            print("Warning: 'ticker' column not found in input.csv.")
            return ['SPY']
    except Exception as e:
        print(f"Error reading input.csv: {e}. Defaulting to SPY.")
        return ['SPY']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Weekly Quant System Analysis')
    parser.add_argument('--window', type=int, default=20, help='SMA Window length (default: 20)')
    parser.add_argument('--weekly', action='store_true', help='Resample daily data to weekly bars')
    args = parser.parse_args()

    tickers = get_params_from_csv()
    all_signals = []

    start = '2018-01-01'
    end = date.today().strftime('%Y-%m-%d')

    print(f'=== Starting Quant System Run ({len(tickers)} tickers) ===\n')

    for ticker in tickers:
        res = run_analysis(ticker, start, end, window=args.window, use_weekly=args.weekly)
        if res:
            all_signals.append(res)

    # Export structured output payload
    if all_signals:
        results_df = pd.DataFrame(all_signals)
        results_df.to_csv('weekly_target_trade.csv', index=False)
        print('\n=== Output Summary ===')
        print(results_df[['ticker', 'evaluation_date', 'signal', 'z_score_strength', 'close']].to_string(index=False))
        print('\nSaved full signals payload to weekly_target_trade.csv')
    else:
        print('\nNo valid signals generated.')

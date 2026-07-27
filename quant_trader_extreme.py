import os
import sys
import math
import pandas as pd
from datetime import datetime

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus

# ==============================================================================
# QUANT TRADER EXTREME V2: MONDAY EXECUTION MODULE
# ==============================================================================

# Initialize API Keys safely from environment variables
API_KEY = os.getenv('ALPACA_API_KEY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')

if not API_KEY or not SECRET_KEY:
    print("[!] WARNING: ALPACA_API_KEY or ALPACA_SECRET_KEY environment variables not set.")
    print("[!] Please set your environment variables before executing live/paper orders.")

# Initialize Alpaca Paper Trading Client
trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)

# Base dollar allocation per trade (scaled by z_score_strength)
BASE_ALLOCATION_USD = 1000.0


def execute_monday_rebalance(multiplier=1.0):
    csv_path = "weekly_target_trade.csv"

    # 1. Check if payload exists
    if not os.path.exists(csv_path):
        print(f"[-] Error: '{csv_path}' not found. Ensure weekly_quant_system.py has run.")
        sys.exit(1)

    instructions = pd.read_csv(csv_path)
    if instructions.empty:
        print("[-] Error: Trade instruction file is empty.")
        sys.exit(1)

    # 2. Fetch live account positions and open orders from Alpaca
    try:
        current_positions = {pos.symbol: float(pos.qty) for pos in trading_client.get_all_positions()}
    except Exception as e:
        print(f"[-] Error fetching account positions: {e}")
        current_positions = {}

    # 3. Process each trade instruction row from V2 payload
    for index, trade_row in instructions.iterrows():
        ticker = str(trade_row['ticker'])
        action = str(trade_row['signal']).upper()
        strength = trade_row.get('z_score_strength', 0.0)

        if pd.isna(strength):
            strength = 0.0
        else:
            strength = float(strength)

        print(f"\n[*] Processing Signal -- Ticker: {ticker} | Action: {action} | Z-Strength: {strength}")

        # Check for active pending orders
        try:
            open_orders_request = GetOrdersRequest(symbols=[ticker])
            orders = trading_client.get_orders(filter=open_orders_request)
            terminal_statuses = {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED}
            active_orders = [o for o in orders if o.status not in terminal_statuses]

            if active_orders:
                print(f"[!] Target {ticker} already has an active pending order. Skipping.")
                continue
        except Exception as e:
            print(f"[!] Warning: Could not verify pending orders for {ticker}: {e}")

        holding_qty = current_positions.get(ticker, 0.0)
        is_holding = holding_qty > 0

        # --- EXECUTION LOGIC ---

        if action in ["HOLD_LONG", "HOLD_CASH"]:
            print(f"[+] Posture nominal for {ticker} ({action}). No trade required.")
            continue

        elif action == "NEW_BUY":
            if is_holding:
                print(f"[+] Already long {holding_qty} shares of {ticker}. Holding position.")
                continue

            # Calculate current price for dollar-based position sizing
            current_price = get_latest_price(ticker)
            if current_price <= 0:
                print(f"[-] Could not retrieve price for {ticker}. Skipping buy.")
                continue

            # Scale dollar allocation by strength metric
            adjusted_strength = max(0.5, abs(strength)) if strength != 0 else 1.0
            target_dollars = BASE_ALLOCATION_USD * adjusted_strength * multiplier
            qty = math.floor(target_dollars / current_price)

            if qty <= 0:
                print(f"[!] Calculated quantity is 0 for {ticker} (Target USD: ${target_dollars:.2f}). Skipping.")
                continue

            print(f"[▲] EXECUTING BUY: {ticker} | Qty: {qty} shares (~${qty * current_price:.2f})")
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=qty,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            submit_order(order_data, current_price)

        elif action == "NEW_SELL":
            if not is_holding:
                print(f"[+] Liquidation requested for {ticker}, but position is already 0. Standing down.")
                continue

            # Liquidate 100% of held shares
            current_price = get_latest_price(ticker)
            print(f"[▼] EXECUTING FULL LIQUIDATION: {ticker} | Qty: {holding_qty} shares")
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=holding_qty,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            submit_order(order_data, current_price)


def get_latest_price(ticker):
    """Fetches latest trade price from Alpaca market data feed."""
    try:
        latest_trade = trading_client.get_latest_trade(ticker)
        return float(latest_trade.price)
    except Exception as e:
        print(f"[-] Error fetching price for {ticker}: {e}")
        return 0.0


def submit_order(order_data, current_price):
    """Submits order to Alpaca API and appends audit log to history.csv."""
    try:
        order = trading_client.submit_order(order_data=order_data)
        print(f"[SUCCESS] Order ID {order.id} submitted successfully.")
        log_trade(order_data.symbol, order_data.side.value, order.id, order_data.qty, current_price)
    except Exception as e:
        print(f"[-] Execution Failure for {order_data.symbol}: {e}")


def log_trade(ticker, action, order_id, shares, cost):
    """Logs trade audit record to history.csv."""
    history_file = "history.csv"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade_data = pd.DataFrame([[timestamp, ticker, action, order_id, shares, cost]],
                              columns=['timestamp', 'ticker', 'action', 'order_id', 'shares', 'cost'])
    trade_data.to_csv(history_file, mode='a', index=False, header=not os.path.exists(history_file))


if __name__ == '__main__':
    multiplier = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    print(f"--- STARTING QUANT TRADER EXTREME RUN (Multiplier: {multiplier}x) ---")
    execute_monday_rebalance(multiplier)

import os
import sys
import math
import pandas as pd
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderStatus

# ==============================================================================
# THORP TRADER EXTREME: MONDAY APOCALYPSE EXECUTION MODULE
# ==============================================================================

# 1. Initialize API Keys (Using Alpaca Paper Trading Environment)
# Replace these placeholders with your actual keys from the Alpaca dashboard
API_KEY = os.getenv('ALPACA_API_KEY', 'PKHCXGLGERDBEV5YZAPKCDZDBY')
SECRET_KEY = os.getenv('ALPACA_SECRET_KEY', 'Bh4XgxyEazaVRULEHeB8ZCm2rvrfgAxe7inSbddHsyza')

if API_KEY == 'YOUR_PAPER_API_KEY':
    print("[!] WARNING: ThorpTraderExtreme is running on default placeholder keys. Update them for the math to work.")

# Initialize the Trading Client (paper=True keeps your real cash safe)
trading_client = TradingClient(api_key=API_KEY, secret_key=SECRET_KEY, paper=True)

# Base quantity to be scaled by signal strength
BASE_QTY = 1000

def execute_monday_rebalance():
    csv_path = "weekly_target_trade.csv"
    
    # 2. Check if the weekend analysis payload actually exists
    if not os.path.exists(csv_path):
        print(f"[-] Error: '{csv_path}' not found. Did ThorpTraderExtreme sleep through Sunday?")
        sys.exit(1)
        
    # Read the instruction contract
    instructions = pd.read_csv(csv_path)
    if instructions.empty:
        print("[-] Error: Trade instruction file is empty.")
        sys.exit(1)
        
    # 3. Process each trade instruction in the payload
    for index, trade_row in instructions.iterrows():
        ticker = str(trade_row['ticker'])
        action = str(trade_row['signal']).upper()
        
        print(f"\n[*] ThorpTraderExtreme Processing Signal -- Ticker: {ticker} | Action Required: {action}")
        
        # Check for any open pending orders for this specific ticker to avoid doubling down
        open_orders_request = GetOrdersRequest(symbols=[ticker])
        orders = trading_client.get_orders(filter=open_orders_request)
        
        # Filter for orders that are not in a terminal state
        terminal_statuses = {OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.EXPIRED, OrderStatus.REJECTED}
        open_orders = [o for o in orders if o.status not in terminal_statuses]
        
        if open_orders:
            print(f"[!] Target {ticker} already has an active pending order. Skipping this ticker.")
            continue
        
        # Fetch current broker account positions
        current_positions = trading_client.get_all_positions()
        holding_ticker = any(pos.symbol == ticker for pos in current_positions)
        
        # Execute Order Logic based on the payload contract
        if action == "HOLD":
            print(f"[+] System status nominal. Maintaining current posture for {ticker}. No trades executed.")
            continue
            
        # Calculate quantity based on signal strength
        strength = float(trade_row.get('strength', 0))
        qty = math.ceil(BASE_QTY * strength)
        
        if qty <= 0:
            print(f"[!] Signal strength too low ({strength}) for {ticker}. Skipping trade.")
            continue

        elif action == "BUY":
            if holding_ticker:
                print(f"[+] Already long {ticker}. ThorpTraderExtreme diamond-handing.")
                continue
                
            print(f"[▲] EXECUTING SYSTEM BUY ORDER FOR: {ticker} | Qty: {qty} (Strength: {strength})")
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=qty,  
                side=OrderSide.BUY,
                time_in_force=TimeInForce.GTC
            )
            submit_order(order_data)
            
        elif action == "SELL":
            if not holding_ticker:
                print(f"[+] Requested liquidation for {ticker}, but wallet is already empty. Standing down.")
                continue
                
            print(f"[▼] EXECUTING SYSTEM LIQUIDATION ORDER FOR: {ticker} | Qty: {qty} (Strength: {strength})")
            order_data = MarketOrderRequest(
                symbol=ticker,
                qty=qty,  
                side=OrderSide.SELL,
                time_in_force=TimeInForce.GTC
            )
            submit_order(order_data)

def log_trade(ticker, action, order_id, shares, cost):
    """Logs the trade details to history.csv"""
    history_file = "history.csv"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade_data = pd.DataFrame([[timestamp, ticker, action, order_id, shares, cost]], 
                              columns=['timestamp', 'ticker', 'action', 'order_id', 'shares', 'cost'])
    
    # Append to CSV, write header only if file doesn't exist
    trade_data.to_csv(history_file, mode='a', index=False, header=not os.path.exists(history_file))

def submit_order(order_data):
    try:
        # Get current price for cost estimation
        try:
            latest_trade = trading_client.get_latest_trade(order_data.symbol)
            current_price = latest_trade.price
        except Exception:
            current_price = 0.0

        order = trading_client.submit_order(order_data=order_data)
        print(f"[SUCCESS] Order ID {order.id} transmitted successfully to the exchange floor.")
        
        # Log the trade to history.csv
        log_trade(order_data.symbol, order_data.side.value, order.id, order_data.qty, current_price)
    except Exception as e:
        print(f"[-] Execution Failure: {e}")

if __name__ == '__main__':
    print("--- STARTING THORP TRADER EXTREME MONDAY RUN ---")
    execute_monday_rebalance()
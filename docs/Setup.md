# **Setting Up a Weekly Quantitative Trading System**

Line Spacing: 1.25

## **Overview**

This document details the configuration for a casual, weekly quantitative trading architecture using Python, pandas, yfinance, and backtrader. This decoupled approach runs historical simulations over the weekend and exports a clean CSV payload containing target execution orders for Monday morning.

## **1\. System Architecture**

The system operates in a linear data pipeline to isolate historical calculation from broker interaction:

* **yfinance:** Fetches free daily historical market metrics.  
* **pandas:** Resamples raw daily data into clean weekly blocks, mitigating market noise.  
* **backtrader:** Processes the downsampled dataset to execute backtests and calculate indicators.  
* **CSV Payload:** Saves a lightweight instruction file (weekly\_target\_trade.csv) for programmatic execution.

## **2\. Installation & Dependencies**

Install the required packages via your package manager. Note the use of backtrader-freetier, which provides vital modern Python and NumPy compatibility patches:  
`pip install pandas yfinance backtrader-freetier matplotlib`

## **3\. Core Script Implementation**

Save the following implementation block as weekly\_quant\_system.py:  
`import os`  
`from datetime import datetime`  
`import pandas as pd`  
`import yfinance as yf`  
`import backtrader as bt`

`def get_weekly_data(ticker, start_date, end_date):`  
    `"""Downloads daily data and resamples it to clean weekly bars."""`  
    `print(f"Downloading data for {ticker}...")`  
    `df = yf.download(ticker, start=start_date, end=end_date, progress=False)`  
      
    `if df.empty:`  
        `raise ValueError(f"No data found for ticker {ticker}")`  
          
    `if isinstance(df.columns, pd.MultiIndex):`  
        `df.columns = df.columns.get_level_values(0)`  
          
    `weekly_logic = {`  
        `'Open': 'first',`  
        `'High': 'max',`  
        `'Low': 'min',`  
        `'Close': 'last',`  
        `'Volume': 'sum'`  
    `}`  
      
    `if 'Adj Close' in df.columns:`  
        `df = df.rename(columns={'Adj Close': 'AdjClose'})`  
        `weekly_logic['AdjClose'] = 'last'`  
          
    `df_weekly = df.resample('W-FRI').agg({k: v for k, v in weekly_logic.items() if k in df.columns})`  
    `return df_weekly.dropna()`

`class WeeklyCrossStrategy(bt.Strategy):`  
    `params = (`  
        `('fast_period', 10),`    
        `('slow_period', 40),`    
    `)`

    `def __init__(self):`  
        `self.dataclose = self.datas[0].close`  
        `self.order = None`  
        `self.fast_ma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.p.fast_period)`  
        `self.slow_ma = bt.indicators.SimpleMovingAverage(self.datas[0], period=self.p.slow_period)`  
        `self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)`  
        `self.target_action = "HOLD"`

    `def log(self, txt, dt=None):`  
        `dt = dt or self.datas[0].datetime.date(0)`  
        `print(f'{dt.isoformat()}, {txt}')`

    `def notify_order(self, order):`  
        `if order.status in [order.Submitted, order.Accepted]:`  
            `return`  
        `if order.status in [order.Completed]:`  
            `if order.isbuy():`  
                `self.log(f'BUY EXECUTED, Price: {order.executed.price:.2f}')`  
            `elif order.issell():`  
                `self.log(f'SELL EXECUTED, Price: {order.executed.price:.2f}')`  
        `self.order = None`

    `def next(self):`  
        `self.target_action = "HOLD"`  
        `if self.order:`  
            `return`

        `if not self.position:`  
            `if self.crossover > 0:`  
                `self.log('BUY SIGNAL GENERATED')`  
                `self.order = self.buy()`  
                `self.target_action = "BUY"`  
        `else:`  
            `if self.crossover < 0:`  
                `self.log('SELL SIGNAL GENERATED')`  
                `self.order = self.sell()`  
                `self.target_action = "SELL"`

`def run_backtest():`  
    `ticker = "SPY"`  
    `start = "2018-01-01"`  
    `end = datetime.now().strftime("%Y-%m-%d")`  
      
    `df_weekly = get_weekly_data(ticker, start, end)`  
    `cerebro = bt.Cerebro()`  
      
    `data = bt.feeds.PandasData(`  
        `dataname=df_weekly,`  
        `open='Open',`  
        `high='High',`  
        `low='Low',`  
        `close='Close',`  
        `volume='Volume',`  
        `openinterest=None`  
    `)`  
      
    `cerebro.adddata(data)`  
    `cerebro.addstrategy(WeeklyCrossStrategy)`  
    `cerebro.broker.setcash(100000.0)`  
    `cerebro.broker.setcommission(commission=0.001)`  
      
    `print(f'Starting Portfolio Value: {cerebro.broker.getvalue():.2f}')`  
    `strategies = cerebro.run()`  
    `strat = strategies[0]`  
    `print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')`  
      
    `last_date = df_weekly.index[-1].strftime("%Y-%m-%d")`  
    `trade_instructions = pd.DataFrame([{`  
        `'Ticker': ticker,`  
        `'EvaluationDate': last_date,`  
        `'Action': strat.target_action,`  
        `'CurrentPosition': "LONG" if strat.position else "CASH"`  
    `}])`  
      
    `trade_instructions.to_csv("weekly_target_trade.csv", index=False)`  
    `print("Generated 'weekly_target_trade.csv'")`

`if __name__ == '__main__':`  
    `run_backtest()`

## **4\. Payload Contract**

The system generates a standard CSV structure after analyzing the final bar over the weekend. Below is the data model contract:

| Field Name | Data Type | Description   |
| :---- | :---- | :---- |
| **Ticker** | String | The asset identifier symbol evaluated (e.g., SPY). |
| **EvaluationDate** | Date (YYYY-MM-DD) | The close date of the final weekly bar processed. |
| **Action** | Enum \[BUY, SELL, HOLD\] | The execution directive triggered by the structural signals. |
| **CurrentPosition** | Enum \[LONG, CASH\] | The current market posture calculated at evaluation time. |


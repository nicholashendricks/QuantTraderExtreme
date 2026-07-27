REM Navigate to project directory
cd /d "C:\Users\nhend\QuantTraderExtreme"

REM Optional: Set API Keys for Alpaca
set ALPACA_API_KEY=PKTZD2HHJ2Q5P4BKJRPH3C4K4S
set ALPACA_SECRET_KEY=5pLkR4rKksvcdiLLZ7QqWrj9J4YSzbBFVULM9y7iJzy3

echo [%date% %time%] Starting Weekly Quant Analysis... >> runner.log
python weekly_quant_system.py --weekly >> runner.log 2>&1

REM Only proceed to execution if the analysis script succeeded (errorlevel 0)
if %errorlevel% equ 0 (
    echo [%date% %time%] Analysis completed. Executing Alpaca Trader... >> runner.log
    python quant_trader_extreme.py 10.0 >> runner.log 2>&1
) else (
    echo [%date% %time%] Quant Analysis failed. Skipping trade execution. >> runner.log
)
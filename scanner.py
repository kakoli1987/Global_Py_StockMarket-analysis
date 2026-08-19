import yfinance as yf
from indicators import calculate_bollinger_bands

WATCHLIST = ['AAPL', 'MSFT', 'TSLA']

def run_local_scan():
    for ticker in WATCHLIST:
        data = yf.download(ticker, period="1mo", progress=False)
        upper, lower, _ = calculate_bollinger_bands(data)
        price = data['Close'].iloc[-1]

        if price >= upper.iloc[-1]:
            print(f"[{ticker}] ALERT: Overbought at ${price:.2f}")
        elif price <= lower.iloc[-1]:
            print(f"[{ticker}] ALERT: Oversold at ${price:.2f}")
        else:
            print(f"[{ticker}] Status: Normal")

if __name__ == "__main__":
    run_local_scan()
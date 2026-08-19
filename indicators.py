import pandas as pd
import numpy as np

def calculate_rsi(data: pd.DataFrame, window: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI) for momentum evaluation."""
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_bollinger_bands(data: pd.DataFrame, window: int = 20, num_std: int = 2):
    """Calculates Bollinger Bands and Moving Averages."""
    sma = data['Close'].rolling(window=window).mean()
    std = data['Close'].rolling(window=window).std()
    upper_band = sma + (std * num_std)
    lower_band = sma - (std * num_std)
    return upper_band, lower_band, sma

def calculate_support_resistance(data: pd.DataFrame, window: int = 50):
    """Calculates rolling support (lowest lows) and resistance (highest highs)."""
    support = data['Low'].rolling(window=window).min()
    resistance = data['High'].rolling(window=window).max()
    return support, resistance

def generate_ai_report(latest_price, rsi, upper, lower, daily_return):
    """Simulates an AI heuristic commentary report based on technical stats."""
    insights = []
    if rsi < 30:
        insights.append("• **RSI Oversold Alert**: Stock is trading under 30 RSI, pointing to potential reversal or bounce opportunities.")
    elif rsi > 70:
        insights.append("• **RSI Overbought Alert**: Stock is trading above 70 RSI, signaling potential pullback risk.")
    else:
        insights.append(f"• **Momentum Normal**: RSI is neutral at {rsi:.2f}.")

    if latest_price <= lower:
        insights.append("• **Bollinger Lower Band Breach**: Price is pressing against or violating the lower volatility channel.")
    elif latest_price >= upper:
        insights.append("• **Bollinger Upper Band Breach**: Price is testing upper resistance limits.")

    if daily_return <= -4.0:
        insights.append("⚠️ **Sudden Drop Warning**: Asset has dropped more than 4% in the current session, indicating high volatility or panic sell pressure.")
    else:
        insights.append("• **Volatility State**: Normal intraday behavior detected without emergency systemic drop triggers.")

    return "\n".join(insights)
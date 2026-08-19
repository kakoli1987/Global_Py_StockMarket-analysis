import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from indicators import (
    calculate_bollinger_bands,
    calculate_rsi,
    calculate_support_resistance,
    generate_ai_report,
)
from streamlit_autorefresh import st_autorefresh

# Page Config
st.set_page_config(
    page_title="Global Real-Time Stock & AI Intelligence Platform", layout="wide"
)

# --- AUTOMATIC PAGE REFRESH (Every 10 Minutes) ---
count = st_autorefresh(interval=10 * 60 * 1000, key="dataplatform_autorefresh")

# Initialize session state flags for safe dialog control
if "show_risk_modal" not in st.session_state:
    st.session_state.show_risk_modal = False


# Popup modal window for Risk Management & Position Sizing
@st.dialog("🛡️ Advanced Risk Management & Position Calculator", width="large")
def render_risk_management_modal(current_price, currency, ticker_symbol):
    st.markdown(
        f"Configuring trade risk parameters for **{ticker_symbol}** at current"
        f" price: **{current_price:,.2f} {currency}**"
    )
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        trade_action = st.radio("Trade Direction", ["BUY (Long)", "SELL (Short)"])
        total_capital = st.number_input(
            f"Total Investment Capital ({currency})",
            min_value=100.0,
            value=10000.0,
            step=500.0,
        )
        risk_pct = st.slider(
            "Risk Tolerance per Trade (%)", min_value=0.5, max_value=5.0, value=1.5
        )

    with col2:
        risk_reward_ratio = st.selectbox(
            "Risk-to-Reward Target", [1.0, 1.5, 2.0, 2.5, 3.0], index=2
        )
        stop_loss_pct = st.slider(
            "Stop-Loss Distance from Current (%)",
            min_value=0.5,
            max_value=10.0,
            value=3.0,
        )

    # Calculations
    if trade_action == "BUY (Long)":
        stop_loss_price = current_price * (1 - (stop_loss_pct / 100.0))
        take_profit_price = current_price * (
                1 + ((stop_loss_pct * risk_reward_ratio) / 100.0)
        )
        max_loss_currency = total_capital * (risk_pct / 100.0)
        risk_per_share = current_price - stop_loss_price
        shares_to_buy = (
            max_loss_currency / risk_per_share if risk_per_share > 0 else 0
        )
    else:
        stop_loss_price = current_price * (1 + (stop_loss_pct / 100.0))
        take_profit_price = current_price * (
                1 - ((stop_loss_pct * risk_reward_ratio) / 100.0)
        )
        max_loss_currency = total_capital * (risk_pct / 100.0)
        risk_per_share = stop_loss_price - current_price
        shares_to_buy = (
            max_loss_currency / risk_per_share if risk_per_share > 0 else 0
        )

    total_position_value = shares_to_buy * current_price
    expected_profit_currency = max_loss_currency * risk_reward_ratio

    st.markdown("---")
    st.subheader("📊 Output Results")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🛑 Stop-Loss Price", f"{stop_loss_price:,.2f} {currency}")
    m2.metric("🎯 Take-Profit Target", f"{take_profit_price:,.2f} {currency}")
    m3.metric("📉 Max Risk Capital", f"{max_loss_currency:,.2f} {currency}")
    m4.metric("📈 Target Profit", f"+{expected_profit_currency:,.2f} {currency}")

    st.info(
        f"**Position Recommendation:** To risk no more than **{risk_pct}%**"
        f" ({max_loss_currency:,.2f} {currency}) of your capital, trade"
        f" **{shares_to_buy:,.2f} shares/units** (Total Exposure:"
        f" **{total_position_value:,.2f} {currency}**)."
    )

    if st.button("Close Modal", use_container_width=True):
        st.session_state.show_risk_modal = False
        st.rerun()


# --- REAL-TIME MARKET SCREENER FETCH FUNCTION ---
@st.cache_data(ttl=300)
def fetch_real_time_market_screener(tickers_list):
    screener_records = []

    for ticker_symbol in tickers_list:
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info

            hist = stock.history(period="2d")
            if hist.empty:
                continue

            current_price = float(hist["Close"].iloc[-1])
            prev_close = (
                float(hist["Close"].iloc[-2])
                if len(hist) > 1
                else current_price
            )
            chg_pct = (
                ((current_price - prev_close) / prev_close) * 100
                if prev_close > 0
                else 0.0
            )

            symbol_code = ticker_symbol.replace(".T", "")
            company_name = info.get("longName") or info.get(
                "shortName", ticker_symbol
            )
            currency = info.get("currency", "USD")
            market_cap = info.get("marketCap", 0)
            volume = hist["Volume"].iloc[-1] if "Volume" in hist.columns else 0

            pe_ratio = info.get("trailingPE", "—")
            if isinstance(pe_ratio, (int, float)):
                pe_str = f"{pe_ratio:.2f}"
            else:
                pe_str = "—"

            eps = info.get("trailingEps", 0)
            eps_str = f"{eps:,.2f} {currency}" if eps else "—"

            div_yield = info.get("dividendYield", 0)
            div_yield_pct = (
                f"{div_yield * 100:.2f}%"
                if isinstance(div_yield, (int, float)) and div_yield > 0
                else "0.00%"
            )

            sector = info.get("sector", "General")
            recommendation = info.get("recommendationKey", "none").upper()

            if recommendation in ["BUY", "STRONG_BUY"]:
                analyst_rating = "🟢 Strong buy"
            elif recommendation == "SELL":
                analyst_rating = "🔴 Sell"
            else:
                analyst_rating = "— No rating"

            screener_records.append({
                "SortKey": market_cap if market_cap else 0,
                "Symbol": symbol_code,
                "Company": company_name,
                "Price": f"{current_price:,.2f} {currency}",
                "Chg %": f"{chg_pct:+.2f}%",
                "Vol": f"{volume:,.0f}",
                "Mkt cap": f"{market_cap / 1e9:,.2f} B {currency}"
                if market_cap > 0
                else "N/A",
                "P/E": pe_str,
                "EPS dil TTM": eps_str,
                "Div yield % TTM": div_yield_pct,
                "Sector": sector,
                "Analyst rating": analyst_rating,
            })
        except Exception:
            continue

    df = pd.DataFrame(screener_records)
    if not df.empty:
        df = df.sort_values(by="SortKey", ascending=False).drop(
            columns=["SortKey"]
        )
    return df


# --- HELPER: RESOLVE COMPANY NAMES TO TICKERS AUTOMATICALLY ---
def parse_inputs_to_tickers(raw_input_string):
    tokens = [t.strip() for t in raw_input_string.split(",") if t.strip()]
    resolved_tickers = []

    for token in tokens:
        # Check if it's already a clean ticker format or explicit code
        if (
                token.upper() in ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
                or "." in token
                or token.isdigit()
        ):
            symbol = token.upper()
            if symbol.isdigit():
                symbol += ".T"
            resolved_tickers.append(symbol)
        else:
            try:
                # Fallback/Safe mapping for common Japanese names if typed textually without suffix
                lower_token = token.lower()
                japan_mapping = {
                    "yokohama rubber": "5101.T",
                    "yokohama": "5101.T",
                    "yokohama financial": "7186.T",
                    "toyota": "7203.T",
                    "sony": "6758.T",
                    "softbank": "9984.T",
                    "honda": "7267.T",
                    "nissan": "7201.T",
                    "canon": "7751.T",
                    "nintendo": "7974.T"
                }
                if lower_token in japan_mapping:
                    resolved_tickers.append(japan_mapping[lower_token])
                    continue

                search_res = yf.Search(token, max_results=1)
                quotes = search_res.quotes
                if quotes:
                    best_symbol = quotes[0].get("symbol")
                    if best_symbol:
                        resolved_tickers.append(best_symbol.upper())
                    else:
                        resolved_tickers.append(token.upper())
                else:
                    resolved_tickers.append(token.upper())
            except Exception:
                resolved_tickers.append(token.upper())

    return list(dict.fromkeys(resolved_tickers))


# --- POPUP VIEW: CUSTOM STOCK SCREENER & WATCHLIST DASHBOARD ---
@st.dialog("📈 Custom Stock Screener & Watchlist Dashboard", width="large")
def render_market_screener_modal():
    st.caption(
        "Enter single or multiple company names/tickers separated by commas"
        " (e.g., Apple or Apple, Toyota, Microsoft)."
    )

    preset_choice = st.selectbox(
        "Load Quick Preset Universe",
        [
            "Custom / Single Entry",
            "🇺🇸 US Mega Tech (Apple, Microsoft, Nvidia, Tesla)",
            "🇯🇵 Japan Blue-Chips (Toyota, Sony, SoftBank)",
        ],
    )

    if "US Mega Tech" in preset_choice:
        default_text = "Apple, Microsoft, Nvidia, Tesla"
    elif "Japan Blue-Chips" in preset_choice:
        default_text = "Toyota, Sony, SoftBank"
    else:
        default_text = "Apple"

    user_tickers_input = st.text_area(
        "Enter Company Name(s) or Ticker(s) (comma-separated):",
        value=default_text,
        help=(
            "Works perfectly for a single stock or a watchlist, displaying"
            " comprehensive valuation metrics."
        ),
    )

    if st.button("🚀 Fetch Live Data", type="primary"):
        with st.spinner("Resolving names and fetching live metrics..."):
            target_tickers = parse_inputs_to_tickers(user_tickers_input)

        if not target_tickers:
            st.warning("Please enter at least one valid company name or ticker.")
            return

        with st.spinner(f"Loading data for: {', '.join(target_tickers)}..."):
            live_screener_df = fetch_real_time_market_screener(target_tickers)

        if not live_screener_df.empty:
            st.success(
                f"Successfully loaded {len(live_screener_df)} asset(s), sorted"
                " top-to-low!"
            )
            st.dataframe(
                live_screener_df, use_container_width=True, hide_index=True
            )
        else:
            st.warning(
                "No data returned. Check if the company names or ticker symbols"
                " are valid."
            )

    st.markdown("---")
    if st.button("Close View", use_container_width=True):
        st.rerun()


# --- STYLISH GITHUB BANNER ---
st.html("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); padding: 18px 20px; border-radius: 12px; color: #ffffff; display: flex; align-items: center; justify-content: space-between; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1); margin-bottom: 20px; flex-wrap: wrap; gap: 10px;">
    <div>
        <div style="font-size: 11px; font-weight: 700; color: #38bdf8; letter-spacing: 1px; margin-bottom: 3px;">
            📊 
        </div>
        <h2 style="font-size: 22px; font-weight: 800; margin: 0; background: linear-gradient(to right, #ffffff, #94a3b8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Global Stock Analysis 
        </h2>
    </div>
    <div style="display: flex; gap: 15px; font-size: 12px; color: #94a3b8; background: rgba(15, 23, 42, 0.6); padding: 8px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
        <div>⚡ <strong style="color: #fff;">Real-Time</strong></div>
        <div>🤖 <strong style="color: #fff;">AI Heuristics</strong></div>
        <div>🛡️ <strong style="color: #fff;">Risk Calc</strong></div>
    </div>
</div>
""")


# Sidebar Configuration
st.sidebar.header("Global Ticker Controls")

market_zone = st.sidebar.selectbox(
    "Select Market Zone / Region",
    [
        "All Global Markets",
        "🇺🇸 United States (US)",
        "🇯🇵 Japan (Tokyo - .T)",
        "🇮🇳 India (NSE/BSE - .NS/.BO)",
        "🇬🇧 United Kingdom (London - .L)",
    ],
)


@st.cache_data(show_spinner=False)
def search_tickers(query, zone):
    if not query:
        return {}
    try:
        query_cleaned = query.strip()
        search_results = yf.Search(query_cleaned, max_results=15)
        quotes = search_results.quotes
        options = {}

        for item in quotes:
            symbol = item.get("symbol", "")
            name = item.get("longname") or item.get("shortname", "")
            exchange = item.get("exchange", "")

            if "Japan" in zone:
                if not symbol.endswith(".T"):
                    if exchange in ["NYQ", "NMS", "ASE"]:
                        continue
                    elif symbol.isdigit():
                        symbol += ".T"
                if not symbol.endswith(".T"):
                    continue

            elif "India" in zone and not (
                    symbol.endswith(".NS") or symbol.endswith(".BO")
            ):
                if symbol.isalnum() and exchange == "NSI":
                    symbol += ".NS"
                else:
                    continue

            elif "United Kingdom" in zone and not symbol.endswith(".L"):
                continue

            if symbol:
                display_name = (
                    f"{name} ({symbol}) - Exch: {exchange}"
                    if name
                    else f"{symbol} - Exch: {exchange}"
                )
                options[display_name] = symbol

        if not options and "Japan" in zone:
            manual_map = {
                "yokohama": "5101.T",
                "yokohama rubber": "5101.T",
                "yokohama financial": "7186.T",
                "honda": "7267.T",
                "subaru": "7270.T",
                "toyota": "7203.T",
                "nissan": "7201.T",
                "sony": "6758.T",
                "softbank": "9984.T",
                "canon": "7751.T",
                "nintendo": "7974.T",
            }
            for k, v in manual_map.items():
                if k in query.lower():
                    options[f"Mapped Asset ({v}) - Exch: TYO"] = v

        return options
    except Exception:
        return {}


search_query = st.sidebar.text_input(
    "Search Company Name / Product",
    "Apple",
    placeholder="e.g., Apple, Toyota, Yokohama, Honda",
)
ticker_options = search_tickers(search_query, market_zone)

if ticker_options:
    selected_display = st.sidebar.selectbox(
        "Select Company / Product", list(ticker_options.keys())
    )
    ticker_input = ticker_options[selected_display]
    st.sidebar.success(f"Selected Ticker: **{ticker_input}**")
else:
    st.sidebar.warning(
        "No matches found for this region. Try loosening the zone filter."
    )
    ticker_input = "AAPL"

timeframe_view = st.sidebar.selectbox(
    "Select Analysis Timeframe",
    [
        "1-Minute Intraday (Last 7 Days)",
        "Monthly View (6mo)",
        "Yearly Macro Trend (1y - 5y)",
    ],
)

with st.sidebar.expander("ℹ️ Global Ticker Suffix Formatting Guide"):
    st.markdown("""
    * **US Default:** `AAPL`, `TSLA`, `MSFT`
    * **Tokyo (Japan):** `5101.T` (Yokohama Rubber), `7186.T` (Yokohama Financial), `7203.T` (Toyota)
    * **London (UK):** `SHEL.L`
    * **NSE (India):** `RELIANCE.NS`
    """)

st.sidebar.markdown("---")
if st.sidebar.button(
        "📈 Custom Stock Screener & Watchlist Dashboard", use_container_width=True
):
    render_market_screener_modal()


# --- 1. LIVE TICKER CONTAINER ---
@st.fragment(run_every=10 * 60)
def render_live_ticker_header(symbol):
    try:
        stock = yf.Ticker(symbol)
        df_live = stock.history(period="2d", interval="1m")
        info = stock.info

        if not df_live.empty:
            company_name = info.get("longName", symbol)
            currency = info.get("currency", "USD")
            sector = info.get("sector", "General Equity")
            market_cap = info.get("marketCap", 0)

            latest_price = float(df_live["Close"].iloc[-1])
            prev_price = (
                float(df_live["Close"].iloc[-2])
                if len(df_live) > 1
                else latest_price
            )
            day_change = latest_price - prev_price
            day_change_pct = (day_change / prev_price) * 100

            st.markdown(
                f"### **Target Asset:** {company_name} (`{symbol}`) | Sector:"
                f" {sector}"
            )
            c1, c2, c3, c4 = st.columns(4)
            c1.metric(
                "Live Price (10m Feed)",
                f"{latest_price:,.2f} {currency}",
                f"{day_change_pct:+.2f}%",
            )
            c2.metric(
                "Market Cap", f"{market_cap / 1e9:,.2f} B {currency}" if market_cap > 0 else "N/A"
            )
            c3.metric("Candles Loaded", f"{len(df_live)}")
            c4.metric("Currency Code", currency)

            st.markdown("---")

            col_btn1, col_btn2 = st.columns([1, 3])
            with col_btn1:
                if st.button(
                        "🛡️ Open Risk Calculator", type="primary", use_container_width=True
                ):
                    st.session_state.show_risk_modal = True
                    st.rerun()

            st.session_state.latest_price = latest_price
            st.session_state.currency = currency
            st.session_state.symbol = symbol

        else:
            st.warning("Fetching live price feed...")
    except Exception:
        st.warning("Connecting to live price stream...")


render_live_ticker_header(ticker_input)

if st.session_state.get("show_risk_modal", False):
    render_risk_management_modal(
        st.session_state.get("latest_price", 100.0),
        st.session_state.get("currency", "USD"),
        st.session_state.get("symbol", ticker_input),
    )

st.markdown("")


# --- 2. HEAVY ANALYTICS CONTAINER ---
@st.cache_data(ttl=600)
def fetch_historical_analysis_data(symbol, view):
    stock = yf.Ticker(symbol)
    if "1-Minute" in view:
        df = stock.history(period="7d", interval="1m")
    elif "Monthly" in view:
        df = stock.history(period="6mo", interval="1d")
    else:
        df = stock.history(period="5y", interval="1d")

    try:
        info = stock.info
    except:
        info = {}
    return df, info


try:
    data, info = fetch_historical_analysis_data(ticker_input, timeframe_view)

    if not data.empty:
        currency = info.get("currency", "USD")
        latest_price = float(data["Close"].iloc[-1])

        # Technical Indicator Pipeline & Signal Engine
        upper, lower, sma = calculate_bollinger_bands(data)
        data["RSI"] = calculate_rsi(data)
        sup_window = 10 if "1-Minute" in timeframe_view else 50
        data["Support"], data["Resistance"] = calculate_support_resistance(
            data, window=sup_window
        )
        data["Daily_Return"] = data["Close"].pct_change() * 100

        latest_rsi = (
            float(data["RSI"].iloc[-1]) if not data["RSI"].empty else 50.0
        )
        latest_return = (
            float(data["Daily_Return"].iloc[-1])
            if not data["Daily_Return"].empty
            else 0.0
        )

        action_signal = "HOLD / NEUTRAL"
        signal_color = "orange"
        if latest_price <= float(lower.iloc[-1]) or latest_rsi < 30:
            action_signal = "BUY SIGNAL (Oversold / Support)"
            signal_color = "green"
        elif latest_price >= float(upper.iloc[-1]) or latest_rsi > 70:
            action_signal = "SELL SIGNAL (Overbought / Resistance)"
            signal_color = "red"

        st.html(f"""
            <div style="padding:15px; border-radius:8px; background-color:#1e293b; color:white; text-align:center; font-size:20px; font-weight:bold;">
                Automated Trade Action Message: <span style="color:{signal_color};">{action_signal}</span>
            </div>
        """)
        st.markdown("")

        # --- MULTI-CHART PRESENTATION SELECTOR ---
        st.subheader("📈 Multi-Style Market Chart Presentations")
        chart_style = st.selectbox(
            "Select Global Chart Presentation Style",
            [
                "Candlestick (Standard OHLC + Technicals)",
                "Line Chart (Clean Macro Trend)",
                "Bar Chart (OHLC Traditional)",
                "Area Chart (Cumulative Shading)",
                "Renko-Style Trend Bricks (Volatility Filtered)"
            ]
        )

        fig = go.Figure()

        if chart_style == "Candlestick (Standard OHLC + Technicals)":
            fig.add_trace(
                go.Candlestick(
                    x=data.index,
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    name="Candles",
                )
            )
            fig.add_trace(go.Scatter(x=data.index, y=upper, name="Upper Bollinger", line=dict(color="gray", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=data.index, y=lower, name="Lower Bollinger", line=dict(color="gray", width=1, dash="dot")))
            fig.add_trace(go.Scatter(x=data.index, y=data["Support"], name="Support Line", line=dict(color="green", width=1.5, dash="dash")))
            fig.add_trace(go.Scatter(x=data.index, y=data["Resistance"], name="Resistance Line", line=dict(color="red", width=1.5, dash="dash")))

        elif chart_style == "Line Chart (Clean Macro Trend)":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data["Close"],
                    mode="lines",
                    name="Close Line",
                    line=dict(color="#38bdf8", width=2)
                )
            )
            fig.add_trace(go.Scatter(x=data.index, y=data["Support"], name="Support Line", line=dict(color="green", width=1.5, dash="dash")))
            fig.add_trace(go.Scatter(x=data.index, y=data["Resistance"], name="Resistance Line", line=dict(color="red", width=1.5, dash="dash")))

        elif chart_style == "Bar Chart (OHLC Traditional)":
            fig.add_trace(
                go.Ohlc(
                    x=data.index,
                    open=data["Open"],
                    high=data["High"],
                    low=data["Low"],
                    close=data["Close"],
                    name="OHLC Bars"
                )
            )

        elif chart_style == "Area Chart (Cumulative Shading)":
            fig.add_trace(
                go.Scatter(
                    x=data.index,
                    y=data["Close"],
                    mode="lines",
                    name="Price Area",
                    fill="tozeroy",
                    line=dict(color="#38bdf8", width=2),
                    fillcolor="rgba(56, 189, 248, 0.15)"
                )
            )

        elif chart_style == "Renko-Style Trend Bricks (Volatility Filtered)":
            brick_size = float(data["Close"].mean() * 0.01)
            renko_x, renko_y, renko_colors = [], [], []
            last_brick = float(data["Close"].iloc[0])

            for idx, row in data.iterrows():
                close_val = float(row["Close"])
                while abs(close_val - last_brick) >= brick_size:
                    if close_val > last_brick:
                        last_brick += brick_size
                        renko_colors.append("green")
                    else:
                        last_brick -= brick_size
                        renko_colors.append("red")
                    renko_x.append(idx)
                    renko_y.append(last_brick)

            if renko_y:
                fig.add_trace(
                    go.Bar(
                        x=renko_x,
                        y=[brick_size] * len(renko_y),
                        base=[y - brick_size if c == "green" else y for y, c in zip(renko_y, renko_colors)],
                        marker_color=renko_colors,
                        name="Renko Bricks"
                    )
                )
            else:
                fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode="lines", name="Price (No Brick Shift)"))

        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=True,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Reports & Analyst Notices
        col_rep1, col_rep2 = st.columns(2)
        with col_rep1:
            st.subheader("📋 Per-Stock Fundamental & Technical Sheet")

            target_mean = info.get("targetMeanPrice", "N/A")
            recommendation = info.get("recommendationKey", "N/A").upper()
            num_analysts = info.get("numberOfAnalystOpinions", "N/A")

            raw_ex_div = info.get("exDividendDate")
            if isinstance(raw_ex_div, (int, float)) and raw_ex_div > 0:
                ex_div_date = pd.to_datetime(raw_ex_div, unit='s').strftime('%b %d, %Y')
            else:
                ex_div_date = "N/A"

            open_price = info.get("open", data['Open'].iloc[-1] if not data.empty else "N/A")
            high_price = info.get("dayHigh", data['High'].iloc[-1] if not data.empty else "N/A")
            low_price = info.get("dayLow", data['Low'].iloc[-1] if not data.empty else "N/A")
            volume = info.get("volume", data['Volume'].iloc[-1] if not data.empty else 0)
            avg_volume = info.get("averageVolume", "N/A")
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE", "N/A")
            week_high_52 = info.get("fiftyTwoWeekHigh", "N/A")
            week_low_52 = info.get("fiftyTwoWeekLow", "N/A")
            trailing_eps = info.get("trailingEps", "N/A")
            shares_out = info.get("sharesOutstanding", 0)
            div_yield = info.get("dividendYield", 0)
            quarterly_div = info.get("lastDividendValue", "N/A")
            employees = info.get("fullTimeEmployees", "N/A")

            def fmt_price(val):
                return f"{currency} {val:,.2f}" if isinstance(val, (int, float)) else str(val)

            def fmt_vol(val):
                if not isinstance(val, (int, float)): return str(val)
                if val >= 1e9: return f"{val/1e9:.2f}B"
                if val >= 1e6: return f"{val/1e6:.2f}M"
                if val >= 1e3: return f"{val/1e3:.2f}K"
                return f"{val:,.0f}"

            def fmt_mkt(val):
                return f"{val/1e9:.2f}B" if isinstance(val, (int, float)) and val > 0 else "N/A"

            # Analyst Notice Box (Safe handling when analyst data is absent or fallback defaults occur)
            if recommendation in ["BUY", "STRONG_BUY"]:
                st.success(
                    f"📢 **Analyst Notice:** Wall Street consensus rates this asset "
                    f"as **{recommendation}**! Average 1-year price target is "
                    f"**{target_mean} {currency}** (based on {num_analysts} analysts)."
                )
            elif recommendation in ["SELL", "UNDERPERFORM"]:
                st.error(
                    f"⚠️ **Analyst Notice:** Wall Street consensus rates this asset "
                    f"as **{recommendation}**. Average 1-year price target is "
                    f"**{target_mean} {currency}** (based on {num_analysts} analysts)."
                )
            else:
                st.info(
                    f"ℹ️ **Analyst Notice:** Wall Street consensus is "
                    f"**{recommendation}**. Average price target is "
                    f"**{target_mean} {currency}** across {num_analysts} reporting analysts."
                )

            st.markdown("---")

            grid_data = [
                ("Open", fmt_price(open_price), "Ex-dividend date", ex_div_date),
                ("High", fmt_price(high_price), "P/E ratio", f"{pe_ratio:,.2f}" if isinstance(pe_ratio, (int, float)) else pe_ratio),
                ("Low", fmt_price(low_price), "52-wk high", fmt_price(week_high_52)),
                ("Mkt. cap", fmt_mkt(market_cap), "52-wk low", fmt_price(week_low_52)),
                ("Avg. vol.", fmt_vol(avg_volume), "EPS", fmt_price(trailing_eps)),
                ("Volume", fmt_vol(volume), "Shares outstanding", fmt_vol(shares_out)),
                ("Dividend", f"{div_yield * 100:.2f}%" if isinstance(div_yield, (int, float)) and div_yield > 0 else "0.00%", "No. of employees", f"{employees:,}" if isinstance(employees, int) else str(employees)),
                ("Quarterly dividend", fmt_price(quarterly_div), "", "")
            ]

            for label1, val1, label2, val2 in grid_data:
                col_a, col_b, col_c, col_d = st.columns([1.2, 1.3, 1.2, 1.3])
                with col_a:
                    st.markdown(f"<span style='color: #94a3b8;'>{label1}</span>", unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"<span style='color: #38bdf8; font-weight: 600;'>{val1}</span>", unsafe_allow_html=True)
                with col_c:
                    if label2:
                        st.markdown(f"<span style='color: #94a3b8;'>{label2}</span>", unsafe_allow_html=True)
                with col_d:
                    if label2:
                        st.markdown(f"<span style='color: #38bdf8; font-weight: 600;'>{val2}</span>", unsafe_allow_html=True)

        with col_rep2:
            st.subheader("🤖 AI Heuristic Analysis & Diagnostic Report")
            ai_text = generate_ai_report(
                latest_price,
                latest_rsi,
                float(upper.iloc[-1]),
                float(lower.iloc[-1]),
                latest_return,
            )
            st.markdown(ai_text)

        sudden_drops = data[data["Daily_Return"] <= -4.0]
        if not sudden_drops.empty:
            st.markdown("---")
            st.subheader("⚠️ Sudden Crash / Drop History (>4% Session Collapse)")
            drop_view = sudden_drops[["Close", "Daily_Return"]].copy()
            drop_view["Drop Percentage"] = (
                    drop_view["Daily_Return"].round(2).astype(str) + "%"
            )
            st.dataframe(
                drop_view.rename(columns={"Close": "Closing Price"})[
                    ["Closing Price", "Drop Percentage"]
                ],
                use_container_width=True,
            )

    else:
        st.error("Data could not be retrieved. Please check the ticker symbol.")

except Exception as e:
    st.error(f"Runtime execution error caught: {e}")
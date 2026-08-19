import streamlit as st


# Defines a popup modal window in Streamlit
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
        st.rerun()
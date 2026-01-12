import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

# Page configuration
st.set_page_config(
    page_title="DCF Valuation Calculator",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("📊 DCF Valuation Calculator (Complete)")
st.markdown("---")

# Sidebar for ticker input
with st.sidebar:
    st.header("Stock Selection")
    ticker_input = st.text_input("Enter Stock Ticker", value="NVDA").upper()
    fetch_button = st.button("🔍 Fetch Data", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("This tool provides two DCF analysis methods:\n\n"
            "**Reverse DCF**: Calculate implied growth rate from current price\n\n"
            "**Fundamental DCF**: Calculate intrinsic value from projections")
    
    st.warning("⚠️ For educational purposes only. Not financial advice.")

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None

# Fetch stock data
if fetch_button and ticker_input:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            import time
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            # Create ticker with session for better rate limit handling
            stock = yf.Ticker(ticker_input)
            
            # 1. Price (History)
            try:
                hist = stock.history(period="1d")
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            except:
                current_price = 0
            
            # 2. Shares & Market Cap (Fast Info - EquityQuery)
            try:
                info = stock.fast_info
                shares_outstanding = info.shares if hasattr(info, 'shares') else 0
                market_cap = info.market_cap if hasattr(info, 'market_cap') else 0
            except:
                shares_outstanding = 0
                market_cap = 0
            
            # 3. Financial Statements
            try:
                cashflow = stock.cashflow
                financials = stock.financials
                balance_sheet = stock.balance_sheet
            except:
                cashflow = pd.DataFrame()
                financials = pd.DataFrame()
                balance_sheet = pd.DataFrame()
            
            # --- EXTRACT DATA ---
            
            # Revenue & Net Income
            revenue = 0
            net_income = 0
            if not financials.empty:
                try:
                    # Revenue
                    if 'Total Revenue' in financials.index:
                        revenue = financials.loc['Total Revenue'].iloc[0]
                    elif 'Operating Revenue' in financials.index:
                        revenue = financials.loc['Operating Revenue'].iloc[0]
                    
                    # Net Income
                    if 'Net Income' in financials.index:
                        net_income = financials.loc['Net Income'].iloc[0]
                    elif 'Net Income Common Stockholders' in financials.index:
                        net_income = financials.loc['Net Income Common Stockholders'].iloc[0]
                except:
                    pass

            # Cash & Debt
            cash = 0
            total_debt = 0
            if not balance_sheet.empty:
                try:
                    # Cash
                    if 'Cash And Cash Equivalents' in balance_sheet.index:
                        cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
                    elif 'Cash Financial' in balance_sheet.index: # For banks
                        cash = balance_sheet.loc['Cash Financial'].iloc[0]
                    
                    # Total Debt
                    if 'Total Debt' in balance_sheet.index:
                        total_debt = balance_sheet.loc['Total Debt'].iloc[0]
                except:
                    pass

            # Free Cash Flow
            fcf = 0
            if not cashflow.empty:
                try:
                    if 'Free Cash Flow' in cashflow.index:
                        fcf = cashflow.loc['Free Cash Flow'].iloc[0]
                    elif 'Operating Cash Flow' in cashflow.index:
                        ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
                        capex = cashflow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cashflow.index else 0
                        fcf = ocf + capex
                except:
                    pass

            # Construct Data Object
            stock_data = {
                'ticker': ticker_input,
                'current_price': current_price,
                'shares_outstanding': shares_outstanding,
                'market_cap': market_cap,
                'free_cash_flow': fcf,
                'revenue': revenue,
                'net_income': net_income,
                'total_debt': total_debt,
                'cash': cash,
                'company_name': ticker_input
            }
            
            # Validation
            if stock_data['current_price'] == 0:
                st.error("❌ Could not fetch price/shares. Try again or enter manually.")
                # (Manual entry block - simplified for brevity, logic remains similar)
            else:
                st.session_state.stock_data = stock_data
                st.success(f"✅ Successfully fetched data for {ticker_input}")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Manual Input Option (Using Expander)
with st.expander("📝 Update/Enter Data Manually"):
    if st.session_state.stock_data:
        defaults = st.session_state.stock_data
    else:
        defaults = {'current_price': 0.0, 'shares_outstanding': 0.0, 'free_cash_flow': 0.0, 'cash': 0.0, 'total_debt': 0.0}
    
    col_m1, col_m2, col_m3 = st.columns(3)
    m_price = col_m1.number_input("Price ($)", value=float(defaults.get('current_price', 0.0)))
    m_shares = col_m2.number_input("Shares (B)", value=float(defaults.get('shares_outstanding', 0.0)/1e9))
    m_fcf = col_m3.number_input("FCF ($B)", value=float(defaults.get('free_cash_flow', 0.0)/1e9))
    
    col_m4, col_m5 = st.columns(2)
    m_cash = col_m4.number_input("Cash & Equiv ($B)", value=float(defaults.get('cash', 0.0)/1e9))
    m_debt = col_m5.number_input("Total Debt ($B)", value=float(defaults.get('total_debt', 0.0)/1e9))
    
    if st.button("Update Data"):
        st.session_state.stock_data = {
            'ticker': ticker_input,
            'current_price': m_price,
            'shares_outstanding': m_shares * 1e9,
            'market_cap': m_price * m_shares * 1e9,
            'free_cash_flow': m_fcf * 1e9,
            'cash': m_cash * 1e9,
            'total_debt': m_debt * 1e9,
            'revenue': 0, 'net_income': 0, 'company_name': ticker_input
        }
        st.rerun()

# Display Analysis
if st.session_state.stock_data:
    data = st.session_state.stock_data
    
    st.header(f"{data['company_name']} ({data['ticker']})")
    
    # Financial Overview Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Price", f"${data['current_price']:.2f}")
    with col2: st.metric("Market Cap", f"${data['market_cap']/1e9:.2f}B")
    with col3: st.metric("Free Cash Flow", f"${data['free_cash_flow']/1e9:.2f}B")
    with col4: st.metric("Shares Outstanding", f"{data['shares_outstanding']/1e9:.2f}B")
    
    # Balance Sheet Metrics
    col5, col6, col7, col8 = st.columns(4)
    with col5: st.metric("Total Cash", f"${data['cash']/1e9:.2f}B")
    with col6: st.metric("Total Debt", f"${data['total_debt']/1e9:.2f}B")
    with col7: st.metric("Revenue", f"${data['revenue']/1e9:.2f}B")
    with col8: st.metric("Net Income", f"${data['net_income']/1e9:.2f}B")
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2 = st.tabs(["🔄 Reverse DCF", "📈 Fundamental DCF"])
    
    # ==================== REVERSE DCF ====================
    with tab1:
        st.header("Reverse DCF Analysis")
        st.caption("What growth rate justifies the current price?")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            term_growth_rev = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_rev")
        with col_r2:
            wacc_rev = st.number_input("WACC (%)", 1.0, 30.0, 10.0, 0.5, key="wacc_rev")
            
        if st.button("Calculate Implied Growth", type="primary"):
            fcf = data['free_cash_flow']
            if fcf <= 0:
                st.error("Requires positive Free Cash Flow.")
            else:
                # Target: Enterprise Value (EV)
                # EV = Market Cap + Debt - Cash
                target_ev = data['market_cap'] + data['total_debt'] - data['cash']
                
                wacc_d = wacc_rev / 100
                term_d = term_growth_rev / 100
                
                # Iterative solver for Growth Rate (g)
                # EV = Sum(PV_FCF) + PV_Terminal
                implied_g = 0
                min_diff = float('inf')
                
                # Search range -20% to 100%
                for g in range(-200, 1000):
                    g_rate = g / 10.0 # -20.0 to 100.0
                    g_dec = g_rate / 100
                    
                    pv_sum = 0
                    curr_fcf = fcf
                    
                    # 5 Year Projection
                    for y in range(1, 6):
                        curr_fcf = curr_fcf * (1 + g_dec)
                        pv_sum += curr_fcf / ((1 + wacc_d) ** y)
                    
                    # Terminal Value
                    tv = (curr_fcf * (1 + term_d)) / (wacc_d - term_d)
                    pv_tv = tv / ((1 + wacc_d) ** 5)
                    
                    calc_ev = pv_sum + pv_tv
                    diff = abs(calc_ev - target_ev)
                    
                    if diff < min_diff:
                        min_diff = diff
                        implied_g = g_rate
                
                st.success(f"✅ The market implies an annual growth rate of: **{implied_g:.2f}%**")
                st.info(f"Target Enterprise Value: **${target_ev/1e9:.2f}B** (Market Cap + Debt - Cash)")

    # ==================== FUNDAMENTAL DCF ====================
    with tab2:
        st.header("Fundamental DCF Valuation")
        st.caption("Calculate Intrinsic Value (Equity Value per Share)")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: growth_rate = st.number_input("Growth Rate (%)", 0.0, 50.0, 15.0, 1.0)
        with col_f2: terminal_growth = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1)
        with col_f3: wacc = st.number_input("WACC (%)", 1.0, 30.0, 10.0, 0.5)
        
        if st.button("Calculate Value", type="primary"):
            fcf = data['free_cash_flow']
            if fcf <= 0:
                st.error("Requires positive Free Cash Flow.")
            else:
                wacc_d = wacc / 100
                growth_d = growth_rate / 100
                term_d = terminal_growth / 100
                
                projections = []
                total_pv = 0
                curr_fcf = fcf
                
                # 1. Project Cash Flows
                for year in range(1, 6):
                    curr_fcf = curr_fcf * (1 + growth_d)
                    pv = curr_fcf / ((1 + wacc_d) ** year)
                    total_pv += pv
                    projections.append({'Year': year, 'FCF': curr_fcf/1e9, 'PV': pv/1e9})
                
                # 2. Terminal Value
                terminal_val = (curr_fcf * (1 + term_d)) / (wacc_d - term_d)
                pv_terminal = terminal_val / ((1 + wacc_d) ** 5)
                
                # 3. Enterprise Value
                enterprise_value = total_pv + pv_terminal
                
                # 4. Equity Value (New Logic)
                # Equity Value = Enterprise Value + Cash - Debt
                equity_value = enterprise_value + data['cash'] - data['total_debt']
                
                # 5. Intrinsic Value per Share
                intrinsic_value = equity_value / data['shares_outstanding']
                
                # Upside
                upside = ((intrinsic_value - data['current_price']) / data['current_price']) * 100
                
                # --- Display ---
                st.success("✅ Valuation Complete")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Intrinsic Value", f"${intrinsic_value:.2f}")
                c2.metric("Current Price", f"${data['current_price']:.2f}")
                c3.metric("Upside/Downside", f"{upside:+.2f}%", delta=f"{upside:.2f}%")
                
                st.markdown("### 🧮 Valuation Bridge")
                bridge_df = pd.DataFrame({
                    'Item': ['Enterprise Value (PV of FCF)', '+ Total Cash', '- Total Debt', '= Equity Value'],
                    'Amount ($B)': [
                        enterprise_value/1e9,
                        data['cash']/1e9,
                        -data['total_debt']/1e9,
                        equity_value/1e9
                    ]
                })
                st.table(bridge_df)
                
                # Plots
                df_proj = pd.DataFrame(projections)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_proj['Year'], y=df_proj['PV'], name='PV of FCF', marker_color='#3b82f6'))
                fig.add_trace(go.Bar(x=['Terminal'], y=[pv_terminal/1e9], name='PV Terminal', marker_color='#8b5cf6'))
                fig.update_layout(title="Present Value Breakdown ($B)", height=400)
                st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Enter a stock ticker to begin.")

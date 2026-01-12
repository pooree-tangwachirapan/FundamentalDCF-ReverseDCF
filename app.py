import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time

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
st.title("📊 DCF Valuation Calculator")
st.markdown("---")

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None

# Sidebar for ticker input
with st.sidebar:
    st.header("Stock Selection")
    ticker_input = st.text_input("Enter Stock Ticker", value="NVDA").upper()
    fetch_button = st.button("🔍 Fetch Data", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("""
    **Methods:**
    1. **Reverse DCF**: Find what growth rate the market expects.
    2. **Fundamental DCF**: Calculate fair value based on your growth assumptions.
    """)
    
    st.warning("⚠️ For educational purposes only. Not financial advice.")

# Helper function to safely get float
def safe_float(val):
    try:
        if val is None: return 0.0
        return float(val)
    except:
        return 0.0

# Fetch stock data
if fetch_button and ticker_input:
    st.session_state.stock_data = None # Reset previous data
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            # Create ticker object
            stock = yf.Ticker(ticker_input)
            
            # 1. Fetch Price & Shares (Use fast_info for speed/reliability)
            try:
                current_price = safe_float(stock.fast_info.get('last_price'))
                shares_outstanding = safe_float(stock.fast_info.get('shares'))
                
                # Fallback to history/info if fast_info fails
                if current_price == 0:
                    hist = stock.history(period="1d")
                    current_price = hist['Close'].iloc[-1] if not hist.empty else 0
                
                if shares_outstanding == 0:
                    info = stock.info
                    shares_outstanding = safe_float(info.get('sharesOutstanding'))
            except Exception as e:
                print(f"Error getting price/shares: {e}")
                current_price = 0
                shares_outstanding = 0

            # 2. Fetch Financials (Cash Flow)
            try:
                # Need trailing 12 months or recent annual
                cashflow = stock.cashflow
                if cashflow.empty:
                    cashflow = stock.quarterly_cashflow
            except:
                cashflow = pd.DataFrame()

            # 3. Calculate Free Cash Flow
            fcf_value = 0
            if not cashflow.empty:
                # Try explicit 'Free Cash Flow'
                if 'Free Cash Flow' in cashflow.index:
                    fcf_value = safe_float(cashflow.loc['Free Cash Flow'].iloc[0])
                # Calculate manually: Operating Cash Flow + CapEx
                elif 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
                    ocf = safe_float(cashflow.loc['Operating Cash Flow'].iloc[0])
                    capex = safe_float(cashflow.loc['Capital Expenditure'].iloc[0]) # Capex is usually negative
                    fcf_value = ocf + capex
            
            # 4. Get other info for display (Optional)
            try:
                info = stock.info
            except:
                info = {}

            # Construct Data Object
            stock_data = {
                'ticker': ticker_input,
                'current_price': current_price,
                'shares_outstanding': shares_outstanding,
                'market_cap': current_price * shares_outstanding,
                'free_cash_flow': fcf_value,
                'revenue': safe_float(info.get('totalRevenue', 0)),
                'company_name': info.get('longName', ticker_input)
            }
            
            st.session_state.stock_data = stock_data
            
            if stock_data['current_price'] > 0 and stock_data['shares_outstanding'] > 0:
                st.success(f"✅ Successfully fetched data for {ticker_input}")
            else:
                st.warning("⚠️ Some data points are missing. You may need to enter them manually.")

        except Exception as e:
            st.error(f"❌ Error fetching data: {str(e)}")

# Manual Input Override (Always available in expander)
with st.expander("📝 Manual Data Entry (Use if data is missing/incorrect)", expanded=not st.session_state.stock_data):
    col_m1, col_m2, col_m3 = st.columns(3)
    
    # Defaults from fetched data or 0
    default_price = st.session_state.stock_data['current_price'] if st.session_state.stock_data else 0.0
    default_shares = (st.session_state.stock_data['shares_outstanding'] / 1e9) if st.session_state.stock_data else 0.0
    default_fcf = (st.session_state.stock_data['free_cash_flow'] / 1e9) if st.session_state.stock_data else 0.0

    manual_price = col_m1.number_input("Current Price ($)", min_value=0.0, value=float(default_price), step=0.01)
    manual_shares = col_m2.number_input("Shares Outstanding (Billions)", min_value=0.0, value=float(default_shares), step=0.01)
    manual_fcf = col_m3.number_input("Free Cash Flow ($B)", value=float(default_fcf), step=0.01)

    if st.button("Update/Use Manual Data"):
        st.session_state.stock_data = {
            'ticker': ticker_input,
            'current_price': manual_price,
            'shares_outstanding': manual_shares * 1e9,
            'market_cap': manual_price * manual_shares * 1e9,
            'free_cash_flow': manual_fcf * 1e9,
            'company_name': ticker_input,
            'manual_entry': True
        }
        st.rerun()

# Display Analysis
if st.session_state.stock_data:
    data = st.session_state.stock_data
    
    st.header(f"{data['company_name']} ({data['ticker']})")
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Current Price", f"${data['current_price']:.2f}")
    with col2: st.metric("Market Cap", f"${data['market_cap']/1e9:.2f}B")
    with col3: st.metric("Free Cash Flow (TTM)", f"${data['free_cash_flow']/1e9:.2f}B")
    with col4: st.metric("Shares Outstanding", f"{data['shares_outstanding']/1e9:.2f}B")
    
    st.markdown("---")
    
    if data['free_cash_flow'] <= 0:
        st.error("⚠️ Free Cash Flow is negative or zero. DCF models require positive cash flow to work properly.")
    else:
        # Tabs for different DCF methods
        tab1, tab2 = st.tabs(["🔄 Reverse DCF (Expectations)", "📈 Fundamental DCF (Valuation)"])
        
        # ==================== REVERSE DCF ====================
        with tab1:
            st.subheader("Reverse DCF Analysis")
            st.caption("What growth rate is the market pricing in right now?")
            
            col1, col2 = st.columns(2)
            with col1:
                terminal_growth_reverse = st.slider("Terminal Growth Rate (%)", 0.0, 6.0, 2.5, 0.1, key="term_rev")
            with col2:
                wacc_reverse = st.slider("WACC / Discount Rate (%)", 5.0, 20.0, 10.0, 0.5, key="wacc_rev")
            
            # Calculation
            market_cap = data['market_cap']
            fcf = data['free_cash_flow']
            wacc_dec = wacc_reverse / 100
            term_dec = terminal_growth_reverse / 100
            
            # Simple Reverse DCF Model (Two-stage)
            # Assumption: High growth for 5 years, then terminal growth
            # We solve for 'g' (High Growth Rate)
            
            # This requires a numerical solver or an iterative approximation. 
            # Simplified approach: Solve assuming the market cap is the sum of PVs
            
            # To avoid complex solving in Streamlit, we iterate to find the closest match
            best_g = 0
            min_diff = float('inf')
            
            for g in range(-20, 100): # Check growth from -20% to 100%
                temp_g = g / 100
                pv_sum = 0
                for year in range(1, 6):
                    projected_fcf = fcf * ((1 + temp_g) ** year)
                    pv_sum += projected_fcf / ((1 + wacc_dec) ** year)
                
                terminal_val = (fcf * ((1 + temp_g) ** 5) * (1 + term_dec)) / (wacc_dec - term_dec)
                pv_terminal = terminal_val / ((1 + wacc_dec) ** 5)
                
                implied_ev = pv_sum + pv_terminal
                diff = abs(implied_ev - market_cap)
                
                if diff < min_diff:
                    min_diff = diff
                    best_g = g + (diff/market_cap) # minor adjustment
            
            st.success(f"### The market is pricing in ~{best_g:.2f}% annual growth")
            st.info(f"If you believe {data['ticker']} can grow faster than {best_g:.2f}% annually for the next 5 years, it might be Undervalued.")

        # ==================== FUNDAMENTAL DCF ====================
        with tab2:
            st.subheader("Fundamental DCF Valuation")
            st.caption("Calculate Intrinsic Value based on YOUR assumptions.")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                growth_rate = st.number_input("Expected Growth Rate (Next 5 Yrs) %", value=15.0, step=0.5)
            with col2:
                terminal_growth = st.number_input("Terminal Growth Rate %", value=2.5, step=0.1)
            with col3:
                wacc = st.number_input("WACC (Discount Rate) %", value=10.0, step=0.5)
            
            if st.button("Calculate Value", type="primary"):
                fcf = data['free_cash_flow']
                shares = data['shares_outstanding']
                
                # Logic
                wacc_d = wacc / 100
                growth_d = growth_rate / 100
                term_d = terminal_growth / 100
                
                projections = []
                total_pv_fcf = 0
                
                # Years 1-5
                curr_fcf = fcf
                for y in range(1, 6):
                    curr_fcf = curr_fcf * (1 + growth_d)
                    pv = curr_fcf / ((1 + wacc_d) ** y)
                    total_pv_fcf += pv
                    projections.append({'Year': y, 'FCF': curr_fcf, 'PV': pv})
                
                # Terminal Value
                # TV = (Final Year FCF * (1 + g_term)) / (WACC - g_term)
                terminal_val = (curr_fcf * (1 + term_d)) / (wacc_d - term_d)
                pv_terminal = terminal_val / ((1 + wacc_d) ** 5)
                
                enterprise_val = total_pv_fcf + pv_terminal
                intrinsic_val = enterprise_val / shares
                
                upside = ((intrinsic_val - data['current_price']) / data['current_price']) * 100
                
                # Results
                res_col1, res_col2, res_col3 = st.columns(3)
                with res_col1:
                    st.metric("Intrinsic Value", f"${intrinsic_val:.2f}")
                with res_col2:
                    st.metric("Current Price", f"${data['current_price']:.2f}")
                with res_col3:
                    color = "normal" if upside > 0 else "inverse"
                    st.metric("Upside / Downside", f"{upside:+.2f}%", delta=f"{upside:.2f}%")
                
                # Chart
                df_proj = pd.DataFrame(projections)
                fig = go.Figure()
                fig.add_trace(go.Bar(x=df_proj['Year'], y=df_proj['FCF'], name='Projected FCF', marker_color='#10b981'))
                fig.add_trace(go.Bar(x=['Terminal'], y=[terminal_val], name='Terminal Value', marker_color='#6366f1'))
                fig.update_layout(title="Future Cash Flows", yaxis_title="Amount ($)", height=400)
                st.plotly_chart(fig, use_container_width=True)

else:
    # Landing page info
    st.info("👈 Please enter a stock ticker in the sidebar to begin.")
    st.markdown("#### Popular Tickers")
    st.code("NVDA, AAPL, MSFT, GOOGL, TSLA, AMD")

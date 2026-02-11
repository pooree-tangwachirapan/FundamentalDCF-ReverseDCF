import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from scipy.optimize import brentq, OptimizeWarning
import warnings

# Page configuration

st.set_page_config(
    page_title="DCF Valuation Calculator",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',  # พื้นหลังโปร่งใส
    plot_bgcolor='rgba(0,0,0,0)',   # พื้นกราฟโปร่งใส
    font=dict(color="white", size=12)
)
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
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 1rem;
        color: white;
        margin: 1rem 0;
    }
      </style>
""", unsafe_allow_html=True)

# Title
st.title("📊 DCF Valuation Calculator (Enhanced)")
st.markdown("---")

# Helper Functions
def calculate_dcf_ev(growth_rate, fcf, wacc, terminal_growth, years=5):
    """Calculate Enterprise Value using DCF method"""
    try:
        pv_sum = 0
        curr_fcf = fcf
        
        # Project cash flows
        for year in range(1, years + 1):
            curr_fcf = curr_fcf * (1 + growth_rate)
            pv_sum += curr_fcf / ((1 + wacc) ** year)
        
        # Terminal value
        terminal_val = (curr_fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_terminal = terminal_val / ((1 + wacc) ** years)
        
        return pv_sum + pv_terminal
    except:
        return None

def reverse_dcf_solver(target_ev, fcf, wacc, terminal_growth, years=5):
    """
    Solve for implied growth rate using numerical optimization
    Returns: (implied_growth_rate, success_flag, error_message)
    """
    def equation(g):
        ev = calculate_dcf_ev(g, fcf, wacc, terminal_growth, years)
        return ev - target_ev if ev else 1e15
    
    try:
        # Try to find growth rate between -30% and 200%
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            implied_g = brentq(equation, -0.30, 2.0, maxiter=1000)
        return implied_g * 100, True, None
    except ValueError as e:
        # If no solution found, try fallback method
        try:
            # Sample search at key points
            test_rates = np.linspace(-0.20, 1.50, 200)
            min_diff = float('inf')
            best_g = 0
            
            for g in test_rates:
                ev = calculate_dcf_ev(g, fcf, wacc, terminal_growth, years)
                if ev:
                    diff = abs(ev - target_ev)
                    if diff < min_diff:
                        min_diff = diff
                        best_g = g
            
            return best_g * 100, False, "Approximate solution (no exact match found)"
        except:
            return 0, False, "Could not solve for growth rate"
    except Exception as e:
        return 0, False, f"Error: {str(e)}"

def sensitivity_analysis(fcf, target_ev, base_wacc, base_terminal, years=5):
    """Generate sensitivity table for WACC and Terminal Growth variations"""
    wacc_range = np.linspace(base_wacc - 0.03, base_wacc + 0.03, 5)
    term_range = np.linspace(base_terminal - 0.01, base_terminal + 0.01, 5)
    
    results = []
    for wacc in wacc_range:
        for term in term_range:
            if wacc > term:  # Valid combination
                g, success, _ = reverse_dcf_solver(target_ev, fcf, wacc, term, years)
                results.append({
                    'WACC': f"{wacc*100:.1f}%",
                    'Terminal': f"{term*100:.1f}%",
                    'Implied Growth': f"{g:.1f}%"
                })
    
    return pd.DataFrame(results)

# Sidebar for ticker input
with st.sidebar:
    st.header("Stock Selection")
    ticker_input = st.text_input("Enter Stock Ticker", value="NVDA").upper()
    fetch_button = st.button("🔍 Fetch Data", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### About")
    st.info("This tool provides two DCF analysis methods:\n\n"
            "**Reverse DCF**: Calculate implied growth rate from current price (with scipy optimization)\n\n"
            "**Fundamental DCF**: Calculate intrinsic value from projections\n\n"
            "**✨ Enhanced Features:**\n"
            "- Numerical solver (faster & more accurate)\n"
            "- Sensitivity analysis\n"
            "- Better error handling\n"
            "- Interactive visualizations")
    
    st.warning("⚠️ For educational purposes only. Not financial advice.")

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None

# Fetch stock data
if fetch_button and ticker_input:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            import time
            time.sleep(1)
            
            stock = yf.Ticker(ticker_input)
            
            # 1. Price
            try:
                hist = stock.history(period="1d")
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            except:
                current_price = 0
            
            # 2. Shares & Market Cap
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
            
            # Extract data
            revenue = 0
            net_income = 0
            if not financials.empty:
                try:
                    if 'Total Revenue' in financials.index:
                        revenue = financials.loc['Total Revenue'].iloc[0]
                    elif 'Operating Revenue' in financials.index:
                        revenue = financials.loc['Operating Revenue'].iloc[0]
                    
                    if 'Net Income' in financials.index:
                        net_income = financials.loc['Net Income'].iloc[0]
                    elif 'Net Income Common Stockholders' in financials.index:
                        net_income = financials.loc['Net Income Common Stockholders'].iloc[0]
                except:
                    pass

            cash = 0
            total_debt = 0
            if not balance_sheet.empty:
                try:
                    if 'Cash And Cash Equivalents' in balance_sheet.index:
                        cash = balance_sheet.loc['Cash And Cash Equivalents'].iloc[0]
                    elif 'Cash Financial' in balance_sheet.index:
                        cash = balance_sheet.loc['Cash Financial'].iloc[0]
                    
                    if 'Total Debt' in balance_sheet.index:
                        total_debt = balance_sheet.loc['Total Debt'].iloc[0]
                except:
                    pass

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
            
            if stock_data['current_price'] == 0:
                st.error("❌ Could not fetch price data. Please enter manually below.")
            else:
                st.session_state.stock_data = stock_data
                st.success(f"✅ Successfully fetched data for {ticker_input}")
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Manual Input Option
with st.expander("📝 Update/Enter Data Manually"):
    if st.session_state.stock_data:
        defaults = st.session_state.stock_data
    else:
        defaults = {'current_price': 0.0, 'shares_outstanding': 0.0, 'free_cash_flow': 0.0, 'cash': 0.0, 'total_debt': 0.0}
    
    col_m1, col_m2, col_m3 = st.columns(3)
    m_price = col_m1.number_input("Price ($)", value=float(defaults.get('current_price', 0.0)), min_value=0.0)
    m_shares = col_m2.number_input("Shares (B)", value=float(defaults.get('shares_outstanding', 0.0)/1e9), min_value=0.0)
    m_fcf = col_m3.number_input("FCF ($B)", value=float(defaults.get('free_cash_flow', 0.0)/1e9))
    
    col_m4, col_m5 = st.columns(2)
    m_cash = col_m4.number_input("Cash & Equiv ($B)", value=float(defaults.get('cash', 0.0)/1e9), min_value=0.0)
    m_debt = col_m5.number_input("Total Debt ($B)", value=float(defaults.get('total_debt', 0.0)/1e9), min_value=0.0)
    
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
    tab1, tab2, tab3 = st.tabs(["🔄 Reverse DCF", "📈 Fundamental DCF", "📊 Sensitivity Analysis"])
    
    # ==================== REVERSE DCF ====================
    with tab1:
        st.header("Reverse DCF Analysis")
        st.caption("What growth rate is implied by the current market price?")
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            term_growth_rev = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_rev")
        with col_r2:
            wacc_rev = st.number_input("WACC (%)", 1.0, 30.0, 10.0, 0.5, key="wacc_rev")
        
        # Validation
        wacc_decimal = wacc_rev / 100
        term_decimal = term_growth_rev / 100
        
        if wacc_decimal <= term_decimal:
            st.error("⚠️ WACC must be greater than Terminal Growth Rate for the model to work!")
        
        if st.button("Calculate Implied Growth", type="primary"):
            fcf = data['free_cash_flow']
            if fcf <= 0:
                st.error("❌ Requires positive Free Cash Flow to perform DCF analysis.")
            elif wacc_decimal <= term_decimal:
                st.error("❌ Invalid parameters: WACC must be > Terminal Growth")
            else:
                # Target Enterprise Value
                target_ev = data['market_cap'] + data['total_debt'] - data['cash']
                
                with st.spinner("Solving for implied growth rate..."):
                    implied_g, success, error_msg = reverse_dcf_solver(
                        target_ev, fcf, wacc_decimal, term_decimal
                    )
                
                if success:
                    st.success(f"✅ The market implies an annual FCF growth rate of: **{implied_g:.2f}%**")
                    
                    # Display calculation details
                    st.info(f"""
                    **Calculation Details:**
                    - Target Enterprise Value: **${target_ev/1e9:.2f}B**
                    - EV Formula: Market Cap (${data['market_cap']/1e9:.2f}B) + Debt (${data['total_debt']/1e9:.2f}B) - Cash (${data['cash']/1e9:.2f}B)
                    - Current FCF: **${fcf/1e9:.2f}B**
                    - WACC: **{wacc_rev:.2f}%**
                    - Terminal Growth: **{term_growth_rev:.2f}%**
                    """)
                    
                    # Visualization: FCF Projection
                    years = []
                    fcf_values = []
                    curr_fcf = fcf
                    
                    for year in range(1, 6):
                        curr_fcf = curr_fcf * (1 + implied_g/100)
                        years.append(f"Year {year}")
                        fcf_values.append(curr_fcf/1e9)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=years,
                        y=fcf_values,
                        marker_color='#3b82f6',
                        text=[f"${v:.2f}B" for v in fcf_values],
                        textposition='outside'
                    ))
                    fig.update_layout(
                        title=f"Implied FCF Projection at {implied_g:.2f}% Growth",
                        xaxis_title="Year",
                        yaxis_title="FCF ($B)",
                        height=400
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.warning(f"⚠️ {error_msg if error_msg else 'Could not find exact solution'}")
                    st.info(f"Approximate implied growth rate: **{implied_g:.2f}%**")

    # ==================== FUNDAMENTAL DCF ====================
    with tab2:
        st.header("Fundamental DCF Valuation")
        st.caption("Calculate Intrinsic Value (Equity Value per Share)")
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: growth_rate = st.number_input("Growth Rate (%)", -50.0, 100.0, 15.0, 1.0)
        with col_f2: terminal_growth = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_fund")
        with col_f3: wacc = st.number_input("WACC (%)", 1.0, 30.0, 10.0, 0.5, key="wacc_fund")
        
        # Validation
        if wacc/100 <= terminal_growth/100:
            st.error("⚠️ WACC must be greater than Terminal Growth Rate!")
        
        if st.button("Calculate Value", type="primary"):
            fcf = data['free_cash_flow']
            if fcf <= 0:
                st.error("❌ Requires positive Free Cash Flow.")
            elif wacc/100 <= terminal_growth/100:
                st.error("❌ Invalid parameters: WACC must be > Terminal Growth")
            else:
                wacc_d = wacc / 100
                growth_d = growth_rate / 100
                term_d = terminal_growth / 100
                
                projections = []
                total_pv = 0
                curr_fcf = fcf
                
                # Project Cash Flows
                for year in range(1, 6):
                    curr_fcf = curr_fcf * (1 + growth_d)
                    pv = curr_fcf / ((1 + wacc_d) ** year)
                    total_pv += pv
                    projections.append({'Year': year, 'FCF': curr_fcf/1e9, 'PV': pv/1e9})
                
                # Terminal Value
                terminal_val = (curr_fcf * (1 + term_d)) / (wacc_d - term_d)
                pv_terminal = terminal_val / ((1 + wacc_d) ** 5)
                
                # Enterprise Value
                enterprise_value = total_pv + pv_terminal
                
                # Equity Value
                equity_value = enterprise_value + data['cash'] - data['total_debt']
                
                # Intrinsic Value per Share
                intrinsic_value = equity_value / data['shares_outstanding']
                
                # Upside/Downside
                upside = ((intrinsic_value - data['current_price']) / data['current_price']) * 100
                
                # Display Results
                st.success("✅ Valuation Complete")
                
                # Key Metrics
                c1, c2, c3 = st.columns(3)
                c1.metric("Intrinsic Value", f"${intrinsic_value:.2f}")
                c2.metric("Current Price", f"${data['current_price']:.2f}")
                
                delta_color = "normal" if upside > 0 else "inverse"
                c3.metric(
                    "Upside/Downside", 
                    f"{upside:+.2f}%",
                    delta=f"{upside:.2f}%"
                )
                
                # Valuation Bridge
                st.markdown("### 🧮 Valuation Bridge")
                bridge_df = pd.DataFrame({
                    'Step': [
                        'PV of Projected FCF (Years 1-5)',
                        'PV of Terminal Value',
                        'Enterprise Value',
                        '+ Total Cash',
                        '- Total Debt',
                        'Equity Value',
                        '÷ Shares Outstanding',
                        'Intrinsic Value per Share'
                    ],
                    'Amount ($B)': [
                        f"{total_pv/1e9:.2f}",
                        f"{pv_terminal/1e9:.2f}",
                        f"{enterprise_value/1e9:.2f}",
                        f"{data['cash']/1e9:.2f}",
                        f"-{data['total_debt']/1e9:.2f}",
                        f"{equity_value/1e9:.2f}",
                        f"{data['shares_outstanding']/1e9:.2f}B shares",
                        f"${intrinsic_value:.2f}"
                    ]
                })
                st.table(bridge_df)
                
                # Visualizations
                col_v1, col_v2 = st.columns(2)
                
                with col_v1:
                    # PV Breakdown
                    df_proj = pd.DataFrame(projections)
                    fig1 = go.Figure()
                    fig1.add_trace(go.Bar(
                        x=df_proj['Year'], 
                        y=df_proj['PV'], 
                        name='PV of FCF',
                        marker_color='#3b82f6',
                        text=[f"${v:.2f}B" for v in df_proj['PV']],
                        textposition='outside'
                    ))
                    fig1.add_trace(go.Bar(
                        x=['Terminal'], 
                        y=[pv_terminal/1e9], 
                        name='PV Terminal',
                        marker_color='#8b5cf6',
                        text=[f"${pv_terminal/1e9:.2f}B"],
                        textposition='outside'
                    ))
                    fig1.update_layout(
                        title="Present Value Breakdown",
                        yaxis_title="Value ($B)",
                        height=400
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col_v2:
                    # FCF Growth Projection
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=df_proj['Year'],
                        y=df_proj['FCF'],
                        mode='lines+markers',
                        marker=dict(size=10, color='#10b981'),
                        line=dict(width=3, color='#10b981'),
                        text=[f"${v:.2f}B" for v in df_proj['FCF']],
                        textposition='top center'
                    ))
                    fig2.update_layout(
                        title=f"FCF Projection at {growth_rate:.1f}% Growth",
                        xaxis_title="Year",
                        yaxis_title="FCF ($B)",
                        height=400
                    )
                    st.plotly_chart(fig2, use_container_width=True)

    # ==================== SENSITIVITY ANALYSIS ====================
    with tab3:
        st.header("📊 Sensitivity Analysis")
        st.caption("How does the implied growth rate change with different assumptions?")
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            base_wacc_sens = st.number_input("Base WACC (%)", 1.0, 30.0, 10.0, 0.5, key="wacc_sens")
        with col_s2:
            base_term_sens = st.number_input("Base Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_sens")
        
        if st.button("Run Sensitivity Analysis", type="primary"):
            fcf = data['free_cash_flow']
            if fcf <= 0:
                st.error("❌ Requires positive Free Cash Flow.")
            else:
                target_ev = data['market_cap'] + data['total_debt'] - data['cash']
                
                with st.spinner("Running sensitivity analysis..."):
                    sens_df = sensitivity_analysis(
                        fcf, target_ev, 
                        base_wacc_sens/100, 
                        base_term_sens/100
                    )
                
                st.success("✅ Sensitivity Analysis Complete")
                
                st.markdown("### Impact of WACC and Terminal Growth on Implied Growth Rate")
                st.dataframe(sens_df, use_container_width=True, height=400)
                
                st.info("""
                **How to read this table:**
                - Each row shows a different combination of WACC and Terminal Growth
                - The Implied Growth rate changes based on these assumptions
                - Higher WACC → Lower implied growth (more conservative)
                - Higher Terminal Growth → Lower implied growth for projection period
                """)
                
                # Heatmap visualization
                pivot_data = []
                wacc_values = sorted(sens_df['WACC'].unique())
                term_values = sorted(sens_df['Terminal'].unique())
                
                for wacc in wacc_values:
                    row = []
                    for term in term_values:
                        match = sens_df[(sens_df['WACC'] == wacc) & (sens_df['Terminal'] == term)]
                        if not match.empty:
                            growth_str = match['Implied Growth'].values[0]
                            growth_val = float(growth_str.replace('%', ''))
                            row.append(growth_val)
                    if row:
                        pivot_data.append(row)
                
                if pivot_data:
                    fig = go.Figure(data=go.Heatmap(
                        z=pivot_data,
                        x=[t.replace('%', '') for t in term_values],
                        y=[w.replace('%', '') for w in wacc_values],
                        colorscale='RdYlGn',
                        text=pivot_data,
                        texttemplate='%{text:.1f}%',
                        textfont={"size": 10},
                        colorbar=dict(title="Growth %")
                    ))
                    fig.update_layout(
                        title="Sensitivity Heatmap: Implied Growth Rate",
                        xaxis_title="Terminal Growth Rate (%)",
                        yaxis_title="WACC (%)",
                        height=500
                    )
                    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("👈 Enter a stock ticker in the sidebar to begin analysis.")
    
    # Show example
    st.markdown("### 📚 Quick Start Guide")
    st.markdown("""
    1. **Enter a ticker symbol** (e.g., AAPL, NVDA, MSFT) in the sidebar
    2. **Click 'Fetch Data'** to automatically pull financial data from Yahoo Finance
    3. **Choose your analysis:**
       - **Reverse DCF**: See what growth the market expects
       - **Fundamental DCF**: Calculate if the stock is over/undervalued
       - **Sensitivity Analysis**: Test how assumptions affect results
    
    **Tips:**
    - If auto-fetch fails, use the manual input option
    - WACC typically ranges from 8-15% for most companies
    - Terminal growth is usually 2-3% (GDP growth rate)
    """)




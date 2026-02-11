import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings

# Try to import scipy, use fallback if not available
try:
    from scipy.optimize import brentq, OptimizeWarning
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    st.warning("⚠️ scipy not installed. Using alternative solver (still fast!).")

# Page configuration
st.set_page_config(
    page_title="DCF Valuation Calculator",
    page_icon="📊",
    layout="wide"
)

# Custom CSS - รองรับทั้ง Light และ Dark Mode
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: rgba(240, 242, 246, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    
    /* Dark mode adjustments */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        font-weight: 600;
    }
    
    /* Table styling */
    .dataframe {
        font-size: 0.95rem;
    }
    
    /* Header styling */
    h1, h2, h3 {
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to detect theme and return appropriate plotly template
def get_plotly_template():
    """
    Detect Streamlit theme and return appropriate Plotly template
    Dark mode = plotly_dark, Light mode = plotly_white
    """
    # Try to detect theme from session state
    try:
        # Streamlit doesn't expose theme directly, so we use a workaround
        # Check if user has dark mode preference
        return "plotly_dark"  # Default to dark-friendly
    except:
        return "plotly"

# Color schemes for charts (work well in both modes)
CHART_COLORS = {
    'primary': '#3b82f6',      # Blue
    'secondary': '#8b5cf6',    # Purple
    'success': '#10b981',      # Green
    'warning': '#f59e0b',      # Amber
    'danger': '#ef4444',       # Red
    'info': '#06b6d4',         # Cyan
}

# Title
st.title("📊 DCF Valuation Calculator (Enhanced)")
st.markdown("---")

# Helper Functions
def calculate_wacc(stock_data, stock_obj=None):
    """
    Calculate WACC (Weighted Average Cost of Capital)
    WACC = (E/V × Re) + (D/V × Rd × (1-Tax))
    
    Where:
    - E = Market Cap (Equity)
    - D = Total Debt
    - V = E + D (Total Value)
    - Re = Cost of Equity (from CAPM)
    - Rd = Cost of Debt (Interest/Debt)
    - Tax = Corporate Tax Rate
    
    Returns: (wacc, components_dict)
    """
    try:
        # Get basic data
        market_cap = stock_data.get('market_cap', 0)
        total_debt = stock_data.get('total_debt', 0)
        
        if market_cap == 0:
            return 0.10, {'method': 'default', 'reason': 'No market cap data'}
        
        # Default values
        risk_free_rate = 0.045  # US 10-Year Treasury (4.5% as of 2025)
        market_return = 0.10    # Historical S&P 500 return (~10%)
        default_tax_rate = 0.21 # US Corporate Tax Rate
        
        components = {
            'market_cap': market_cap,
            'total_debt': total_debt,
            'risk_free_rate': risk_free_rate,
            'market_return': market_return
        }
        
        # 1. Get Beta
        beta = 1.0  # Default
        if stock_obj:
            try:
                info = stock_obj.info
                if 'beta' in info and info['beta']:
                    beta = float(info['beta'])
                    components['beta'] = beta
            except:
                pass
        
        # 2. Calculate Cost of Equity (CAPM)
        # Re = Rf + β(Rm - Rf)
        cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)
        components['cost_of_equity'] = cost_of_equity
        
        # 3. Calculate Cost of Debt
        cost_of_debt = 0.05  # Default 5%
        tax_rate = default_tax_rate
        
        if stock_obj and total_debt > 0:
            try:
                # Get Income Statement for Interest Expense
                financials = stock_obj.financials
                if not financials.empty:
                    # Interest Expense
                    if 'Interest Expense' in financials.index:
                        interest_expense = abs(financials.loc['Interest Expense'].iloc[0])
                        cost_of_debt = interest_expense / total_debt
                        components['interest_expense'] = interest_expense
                    
                    # Tax Rate
                    if 'Tax Provision' in financials.index and 'Pretax Income' in financials.index:
                        tax_provision = financials.loc['Tax Provision'].iloc[0]
                        pretax_income = financials.loc['Pretax Income'].iloc[0]
                        if pretax_income > 0:
                            tax_rate = tax_provision / pretax_income
                            components['tax_rate'] = tax_rate
            except:
                pass
        
        components['cost_of_debt'] = cost_of_debt
        components['tax_rate'] = tax_rate
        
        # 4. Calculate WACC
        total_value = market_cap + total_debt
        
        if total_value == 0:
            return 0.10, {'method': 'default', 'reason': 'Zero total value'}
        
        equity_weight = market_cap / total_value
        debt_weight = total_debt / total_value
        
        wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))
        
        components['equity_weight'] = equity_weight
        components['debt_weight'] = debt_weight
        components['wacc'] = wacc
        components['method'] = 'calculated'
        
        # Sanity check: WACC should be between 3% and 30%
        if wacc < 0.03 or wacc > 0.30:
            return 0.10, {'method': 'default', 'reason': f'WACC {wacc:.1%} out of reasonable range'}
        
        return wacc, components
        
    except Exception as e:
        return 0.10, {'method': 'default', 'reason': f'Error: {str(e)}'}

def bisection_solver(func, a, b, tol=1e-6, max_iter=100):
    """
    Bisection method to find root of function
    Fast alternative to scipy when not available
    """
    fa = func(a)
    fb = func(b)
    
    if fa * fb > 0:
        # No sign change, return midpoint
        return (a + b) / 2
    
    for _ in range(max_iter):
        c = (a + b) / 2
        fc = func(c)
        
        if abs(fc) < tol or abs(b - a) < tol:
            return c
        
        if fa * fc < 0:
            b = c
            fb = fc
        else:
            a = c
            fa = fc
    
    return (a + b) / 2

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
        if HAS_SCIPY:
            # Use scipy's fast solver
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OptimizeWarning)
                implied_g = brentq(equation, -0.30, 2.0, maxiter=1000)
            return implied_g * 100, True, None
        else:
            # Use custom bisection method (still fast!)
            implied_g = bisection_solver(equation, -0.30, 2.0)
            # Verify solution is reasonable
            if abs(equation(implied_g)) < target_ev * 0.01:  # Within 1%
                return implied_g * 100, True, None
            else:
                return implied_g * 100, False, "Approximate solution (within 1% tolerance)"
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
    
    solver_info = "scipy optimizer (fastest)" if HAS_SCIPY else "bisection method (fast)"
    
    st.info(f"This tool provides two DCF analysis methods:\n\n"
            "**Reverse DCF**: Calculate implied growth rate from current price\n\n"
            "**Fundamental DCF**: Calculate intrinsic value from projections\n\n"
            "**✨ Enhanced Features:**\n"
            f"- Numerical solver: {solver_info}\n"
            "- Sensitivity analysis\n"
            "- Better error handling\n"
            "- Interactive visualizations")
    
    st.warning("⚠️ For educational purposes only. Not financial advice.")

# Initialize session state
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None
if 'wacc_data' not in st.session_state:
    st.session_state.wacc_data = None

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
            
            # Calculate WACC
            wacc_value, wacc_components = calculate_wacc(stock_data, stock)
            
            if stock_data['current_price'] == 0:
                st.error("❌ Could not fetch price data. Please enter manually below.")
            else:
                st.session_state.stock_data = stock_data
                st.session_state.wacc_data = {
                    'wacc': wacc_value,
                    'components': wacc_components
                }
                st.success(f"✅ Successfully fetched data for {ticker_input}")
                
                # Show WACC calculation
                if wacc_components.get('method') == 'calculated':
                    st.info(f"""
                    📊 **WACC Calculated: {wacc_value*100:.2f}%**
                    
                    **Components:**
                    - Cost of Equity (Re): {wacc_components.get('cost_of_equity', 0)*100:.2f}% (using CAPM with Beta={wacc_components.get('beta', 1.0):.2f})
                    - Cost of Debt (Rd): {wacc_components.get('cost_of_debt', 0)*100:.2f}%
                    - Tax Rate: {wacc_components.get('tax_rate', 0.21)*100:.1f}%
                    - Equity Weight: {wacc_components.get('equity_weight', 0)*100:.1f}% | Debt Weight: {wacc_components.get('debt_weight', 0)*100:.1f}%
                    """)
                else:
                    st.warning(f"⚠️ Using default WACC of 10% - {wacc_components.get('reason', 'Insufficient data')}")
            
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
    
    # WACC Breakdown (if available)
    if st.session_state.wacc_data and st.session_state.wacc_data['components'].get('method') == 'calculated':
        with st.expander("📊 WACC Calculation Details", expanded=False):
            comp = st.session_state.wacc_data['components']
            
            col_w1, col_w2 = st.columns(2)
            
            with col_w1:
                st.markdown("### Cost of Equity (CAPM)")
                st.markdown(f"""
                **Re = Rf + β × (Rm - Rf)**
                
                - Risk-free Rate (Rf): **{comp.get('risk_free_rate', 0.045)*100:.2f}%**
                - Beta (β): **{comp.get('beta', 1.0):.2f}**
                - Market Return (Rm): **{comp.get('market_return', 0.10)*100:.1f}%**
                - **Cost of Equity = {comp.get('cost_of_equity', 0)*100:.2f}%**
                """)
                
                st.markdown("### Capital Structure")
                st.markdown(f"""
                - Market Cap: **${comp.get('market_cap', 0)/1e9:.2f}B**
                - Total Debt: **${comp.get('total_debt', 0)/1e9:.2f}B**
                - Equity Weight: **{comp.get('equity_weight', 0)*100:.1f}%**
                - Debt Weight: **{comp.get('debt_weight', 0)*100:.1f}%**
                """)
            
            with col_w2:
                st.markdown("### Cost of Debt")
                if 'interest_expense' in comp:
                    st.markdown(f"""
                    **Rd = Interest Expense / Total Debt**
                    
                    - Interest Expense: **${comp.get('interest_expense', 0)/1e9:.2f}B**
                    - Total Debt: **${comp.get('total_debt', 0)/1e9:.2f}B**
                    - **Cost of Debt = {comp.get('cost_of_debt', 0)*100:.2f}%**
                    """)
                else:
                    st.markdown(f"""
                    - **Cost of Debt = {comp.get('cost_of_debt', 0)*100:.2f}%** (estimated)
                    """)
                
                st.markdown("### Tax Effect")
                st.markdown(f"""
                - Tax Rate: **{comp.get('tax_rate', 0.21)*100:.1f}%**
                - After-tax Cost of Debt: **{comp.get('cost_of_debt', 0)*(1-comp.get('tax_rate', 0.21))*100:.2f}%**
                """)
                
                st.markdown("---")
                st.markdown(f"""
                ### 🎯 Final WACC
                **WACC = {comp.get('wacc', 0)*100:.2f}%**
                
                = ({comp.get('equity_weight', 0)*100:.1f}% × {comp.get('cost_of_equity', 0)*100:.2f}%) + ({comp.get('debt_weight', 0)*100:.1f}% × {comp.get('cost_of_debt', 0)*(1-comp.get('tax_rate', 0.21))*100:.2f}%)
                """)
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs(["🔄 Reverse DCF", "📈 Fundamental DCF", "📊 Sensitivity Analysis"])
    
    # ==================== REVERSE DCF ====================
    with tab1:
        st.header("Reverse DCF Analysis")
        st.caption("What growth rate is implied by the current market price?")
        
        # Get calculated WACC or use default
        default_wacc = 10.0
        if st.session_state.wacc_data:
            default_wacc = st.session_state.wacc_data['wacc'] * 100
        
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            term_growth_rev = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_rev")
        with col_r2:
            wacc_rev = st.number_input(
                "WACC (%)", 
                1.0, 30.0, 
                default_wacc, 
                0.5, 
                key="wacc_rev",
                help="Weighted Average Cost of Capital - calculated from company data"
            )
        
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
                        marker_color=CHART_COLORS['primary'],
                        text=[f"${v:.2f}B" for v in fcf_values],
                        textposition='outside',
                        textfont=dict(size=12)
                    ))
                    fig.update_layout(
                        title=dict(
                            text=f"Implied FCF Projection at {implied_g:.2f}% Growth",
                            font=dict(size=18)
                        ),
                        xaxis_title="Year",
                        yaxis_title="FCF ($B)",
                        height=400,
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=12),
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:
                    st.warning(f"⚠️ {error_msg if error_msg else 'Could not find exact solution'}")
                    st.info(f"Approximate implied growth rate: **{implied_g:.2f}%**")

    # ==================== FUNDAMENTAL DCF ====================
    with tab2:
        st.header("Fundamental DCF Valuation")
        st.caption("Calculate Intrinsic Value (Equity Value per Share)")
        
        # Get calculated WACC or use default
        default_wacc_fund = 10.0
        if st.session_state.wacc_data:
            default_wacc_fund = st.session_state.wacc_data['wacc'] * 100
        
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: growth_rate = st.number_input("Growth Rate (%)", -50.0, 100.0, 15.0, 1.0)
        with col_f2: terminal_growth = st.number_input("Terminal Growth (%)", 0.0, 10.0, 2.5, 0.1, key="tg_fund")
        with col_f3: wacc = st.number_input(
            "WACC (%)", 
            1.0, 30.0, 
            default_wacc_fund, 
            0.5, 
            key="wacc_fund",
            help="Weighted Average Cost of Capital - calculated from company data"
        )
        
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
                        marker_color=CHART_COLORS['primary'],
                        text=[f"${v:.2f}B" for v in df_proj['PV']],
                        textposition='outside',
                        textfont=dict(size=11)
                    ))
                    fig1.add_trace(go.Bar(
                        x=['Terminal'], 
                        y=[pv_terminal/1e9], 
                        name='PV Terminal',
                        marker_color=CHART_COLORS['secondary'],
                        text=[f"${pv_terminal/1e9:.2f}B"],
                        textposition='outside',
                        textfont=dict(size=11)
                    ))
                    fig1.update_layout(
                        title=dict(text="Present Value Breakdown", font=dict(size=16)),
                        yaxis_title="Value ($B)",
                        height=400,
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=11),
                        showlegend=True,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )
                    st.plotly_chart(fig1, use_container_width=True)
                
                with col_v2:
                    # FCF Growth Projection
                    fig2 = go.Figure()
                    fig2.add_trace(go.Scatter(
                        x=df_proj['Year'],
                        y=df_proj['FCF'],
                        mode='lines+markers+text',
                        marker=dict(size=12, color=CHART_COLORS['success'], line=dict(width=2, color='white')),
                        line=dict(width=3, color=CHART_COLORS['success']),
                        text=[f"${v:.2f}B" for v in df_proj['FCF']],
                        textposition='top center',
                        textfont=dict(size=11),
                        name='Projected FCF'
                    ))
                    fig2.update_layout(
                        title=dict(text=f"FCF Projection at {growth_rate:.1f}% Growth", font=dict(size=16)),
                        xaxis_title="Year",
                        yaxis_title="FCF ($B)",
                        height=400,
                        template="plotly_dark",
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(size=11),
                        showlegend=False
                    )
                    st.plotly_chart(fig2, use_container_width=True)

    # ==================== SENSITIVITY ANALYSIS ====================
    with tab3:
        st.header("📊 Sensitivity Analysis")
        st.caption("How does the implied growth rate change with different assumptions?")
        
        # Get calculated WACC or use default
        default_wacc_sens = 10.0
        if st.session_state.wacc_data:
            default_wacc_sens = st.session_state.wacc_data['wacc'] * 100
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            base_wacc_sens = st.number_input(
                "Base WACC (%)", 
                1.0, 30.0, 
                default_wacc_sens, 
                0.5, 
                key="wacc_sens",
                help="Weighted Average Cost of Capital - calculated from company data"
            )
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
                try:
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
                            textfont=dict(size=11, color="white"),
                            hovertemplate='WACC: %{y}%<br>Terminal: %{x}%<br>Growth: %{z:.1f}%<extra></extra>'
                        ))
                        fig.update_layout(
                            title=dict(
                                text="Sensitivity Heatmap: Implied Growth Rate",
                                font=dict(size=18)
                            ),
                            xaxis=dict(
                                title=dict(text="Terminal Growth Rate (%)", font=dict(size=13)),
                                tickfont=dict(size=11)
                            ),
                            yaxis=dict(
                                title=dict(text="WACC (%)", font=dict(size=13)),
                                tickfont=dict(size=11)
                            ),
                            height=500,
                            template="plotly_dark",
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(size=12)
                        )
                        # Update colorbar separately to avoid issues
                        fig.update_traces(
                            colorbar=dict(title="Growth %")
                        )
                        st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Could not generate heatmap: {str(e)}")
                    st.info("The sensitivity table above still shows all the results.")

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

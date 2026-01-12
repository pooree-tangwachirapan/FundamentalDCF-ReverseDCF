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
st.title("📊 DCF Valuation Calculator")
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
            stock = yf.Ticker(ticker_input)
            info = stock.info
            
            # Get financial data
            cashflow = stock.cashflow
            balance_sheet = stock.balance_sheet
            
            # Extract key metrics
            stock_data = {
                'ticker': ticker_input,
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                'market_cap': info.get('marketCap', 0),
                'free_cash_flow': 0,
                'revenue': info.get('totalRevenue', 0),
                'net_income': info.get('netIncome', 0),
                'total_debt': info.get('totalDebt', 0),
                'cash': info.get('totalCash', 0),
                'company_name': info.get('longName', ticker_input)
            }
            
            # Try to get Free Cash Flow
            if not cashflow.empty:
                if 'Free Cash Flow' in cashflow.index:
                    stock_data['free_cash_flow'] = cashflow.loc['Free Cash Flow'].iloc[0]
                elif 'Operating Cash Flow' in cashflow.index:
                    ocf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
                    capex = cashflow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cashflow.index else 0
                    stock_data['free_cash_flow'] = ocf + capex  # capex is negative
            
            st.session_state.stock_data = stock_data
            st.success(f"✅ Successfully fetched data for {ticker_input}")
            
        except Exception as e:
            st.error(f"❌ Error fetching data: {str(e)}")
            st.info("Please check the ticker symbol and try again.")

# Display stock data if available
if st.session_state.stock_data:
    data = st.session_state.stock_data
    
    st.header(f"{data['company_name']} ({data['ticker']})")
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Price", f"${data['current_price']:.2f}")
    with col2:
        st.metric("Market Cap", f"${data['market_cap']/1e9:.2f}B")
    with col3:
        st.metric("Free Cash Flow", f"${data['free_cash_flow']/1e9:.2f}B")
    with col4:
        st.metric("Shares Outstanding", f"{data['shares_outstanding']/1e9:.2f}B")
    
    st.markdown("---")
    
    # Tabs for different DCF methods
    tab1, tab2 = st.tabs(["🔄 Reverse DCF", "📈 Fundamental DCF"])
    
    # ==================== REVERSE DCF ====================
    with tab1:
        st.header("Reverse DCF Analysis")
        st.markdown("Calculate the implied growth rate based on current market price")
        
        col1, col2 = st.columns(2)
        
        with col1:
            terminal_growth_reverse = st.number_input(
                "Terminal Growth Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.5,
                step=0.1,
                key="terminal_reverse"
            )
        
        with col2:
            wacc_reverse = st.number_input(
                "WACC - Weighted Average Cost of Capital (%)",
                min_value=1.0,
                max_value=30.0,
                value=10.0,
                step=0.5,
                key="wacc_reverse"
            )
        
        if st.button("Calculate Implied Growth Rate", type="primary", key="calc_reverse"):
            
            current_price = data['current_price']
            shares_outstanding = data['shares_outstanding']
            fcf = data['free_cash_flow']
            
            if fcf <= 0:
                st.error("Free Cash Flow must be positive for Reverse DCF calculation")
            else:
                # Calculate market cap
                market_cap = current_price * shares_outstanding
                
                # Reverse DCF calculation
                # Market Cap = PV of future cash flows
                # Using simplified model: implied FCF growth over 5 years
                wacc_decimal = wacc_reverse / 100
                terminal_growth_decimal = terminal_growth_reverse / 100
                
                # Terminal value
                terminal_value = market_cap
                
                # Implied FCF at year 5
                implied_fcf_year5 = terminal_value * (wacc_decimal - terminal_growth_decimal)
                
                # Implied growth rate (CAGR)
                implied_growth = ((implied_fcf_year5 / fcf) ** (1/5) - 1) * 100
                
                # Project cash flows
                projections = []
                fcf_projected = fcf
                for year in range(1, 6):
                    fcf_projected = fcf_projected * (1 + implied_growth / 100)
                    projections.append({
                        'Year': year,
                        'Projected FCF': fcf_projected / 1e9
                    })
                
                df_projections = pd.DataFrame(projections)
                
                # Display results
                st.success("✅ Calculation Complete")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Implied Annual Growth Rate", f"{implied_growth:.2f}%")
                with col2:
                    st.metric("Current Market Cap", f"${market_cap/1e9:.2f}B")
                
                # Plot projections
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df_projections['Year'],
                    y=df_projections['Projected FCF'],
                    mode='lines+markers',
                    name='Projected FCF',
                    line=dict(color='#4f46e5', width=3),
                    marker=dict(size=10)
                ))
                
                fig.update_layout(
                    title="5-Year Free Cash Flow Projection",
                    xaxis_title="Year",
                    yaxis_title="Free Cash Flow ($B)",
                    hovermode='x unified',
                    template='plotly_white',
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show projection table
                st.subheader("Detailed Projections")
                df_display = df_projections.copy()
                df_display['Projected FCF'] = df_display['Projected FCF'].apply(lambda x: f"${x:.2f}B")
                st.dataframe(df_display, use_container_width=True)
                
                st.info(f"💡 **Interpretation**: The market is pricing in an annual FCF growth rate of **{implied_growth:.2f}%** "
                       f"for the next 5 years to justify the current price of **${current_price:.2f}**")
    
    # ==================== FUNDAMENTAL DCF ====================
    with tab2:
        st.header("Fundamental DCF Valuation")
        st.markdown("Calculate intrinsic value based on projected cash flows")
        
        col1, col2 = st.columns(2)
        
        with col1:
            growth_rate = st.number_input(
                "Annual Growth Rate (%)",
                min_value=0.0,
                max_value=50.0,
                value=15.0,
                step=1.0,
                key="growth_rate"
            )
            
            projection_years = st.number_input(
                "Projection Years",
                min_value=1,
                max_value=10,
                value=5,
                step=1,
                key="projection_years"
            )
        
        with col2:
            terminal_growth = st.number_input(
                "Terminal Growth Rate (%)",
                min_value=0.0,
                max_value=10.0,
                value=2.5,
                step=0.1,
                key="terminal_growth"
            )
            
            wacc = st.number_input(
                "WACC - Weighted Average Cost of Capital (%)",
                min_value=1.0,
                max_value=30.0,
                value=10.0,
                step=0.5,
                key="wacc"
            )
        
        if st.button("Calculate Intrinsic Value", type="primary", key="calc_fundamental"):
            
            fcf = data['free_cash_flow']
            shares = data['shares_outstanding']
            current_price = data['current_price']
            
            if fcf <= 0:
                st.error("Free Cash Flow must be positive for DCF calculation")
            else:
                # DCF Calculation
                projections = []
                fcf_projected = fcf
                total_pv = 0
                
                wacc_decimal = wacc / 100
                growth_decimal = growth_rate / 100
                terminal_growth_decimal = terminal_growth / 100
                
                # Project cash flows
                for year in range(1, projection_years + 1):
                    fcf_projected = fcf_projected * (1 + growth_decimal)
                    pv = fcf_projected / ((1 + wacc_decimal) ** year)
                    total_pv += pv
                    
                    projections.append({
                        'Year': year,
                        'Projected FCF': fcf_projected / 1e9,
                        'Present Value': pv / 1e9,
                        'Discount Factor': 1 / ((1 + wacc_decimal) ** year)
                    })
                
                # Terminal value
                terminal_fcf = fcf_projected * (1 + terminal_growth_decimal)
                terminal_value = terminal_fcf / (wacc_decimal - terminal_growth_decimal)
                pv_terminal = terminal_value / ((1 + wacc_decimal) ** projection_years)
                
                # Enterprise value and intrinsic value
                enterprise_value = total_pv + pv_terminal
                intrinsic_value = enterprise_value / shares
                
                # Calculate upside/downside
                upside = ((intrinsic_value - current_price) / current_price) * 100
                
                df_projections = pd.DataFrame(projections)
                
                # Display results
                st.success("✅ Valuation Complete")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Intrinsic Value", f"${intrinsic_value:.2f}")
                with col2:
                    st.metric("Current Price", f"${current_price:.2f}")
                with col3:
                    upside_color = "normal" if upside > 0 else "inverse"
                    st.metric("Upside/Downside", f"{upside:+.2f}%", delta=f"{upside:.2f}%")
                with col4:
                    st.metric("Enterprise Value", f"${enterprise_value/1e9:.2f}B")
                
                # Additional metrics
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("PV of Projected FCF", f"${total_pv/1e9:.2f}B")
                with col2:
                    st.metric("PV of Terminal Value", f"${pv_terminal/1e9:.2f}B")
                
                # Interpretation
                if upside > 20:
                    st.success(f"🎯 **Strong Buy Signal**: Stock appears undervalued by {upside:.1f}%")
                elif upside > 0:
                    st.info(f"📊 **Potential Buy**: Stock appears undervalued by {upside:.1f}%")
                elif upside > -20:
                    st.warning(f"⚠️ **Hold**: Stock appears fairly valued (within ±20%)")
                else:
                    st.error(f"📉 **Overvalued**: Stock appears overvalued by {abs(upside):.1f}%")
                
                # Plot 1: FCF Projection vs Present Value
                fig1 = make_subplots(specs=[[{"secondary_y": False}]])
                
                fig1.add_trace(go.Bar(
                    x=df_projections['Year'],
                    y=df_projections['Projected FCF'],
                    name='Projected FCF',
                    marker_color='#10b981'
                ))
                
                fig1.add_trace(go.Bar(
                    x=df_projections['Year'],
                    y=df_projections['Present Value'],
                    name='Present Value',
                    marker_color='#6366f1'
                ))
                
                fig1.update_layout(
                    title="Free Cash Flow Projections & Present Values",
                    xaxis_title="Year",
                    yaxis_title="Value ($B)",
                    barmode='group',
                    template='plotly_white',
                    height=400
                )
                
                st.plotly_chart(fig1, use_container_width=True)
                
                # Plot 2: Enterprise Value Breakdown
                ev_breakdown = pd.DataFrame({
                    'Component': ['PV of Projected FCF', 'PV of Terminal Value'],
                    'Value': [total_pv/1e9, pv_terminal/1e9]
                })
                
                fig2 = px.pie(
                    ev_breakdown,
                    values='Value',
                    names='Component',
                    title='Enterprise Value Breakdown',
                    color_discrete_sequence=['#3b82f6', '#8b5cf6']
                )
                
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
                
                # Show projection table
                st.subheader("Detailed Cash Flow Projections")
                df_display = df_projections.copy()
                df_display['Projected FCF'] = df_display['Projected FCF'].apply(lambda x: f"${x:.2f}B")
                df_display['Present Value'] = df_display['Present Value'].apply(lambda x: f"${x:.2f}B")
                df_display['Discount Factor'] = df_display['Discount Factor'].apply(lambda x: f"{x:.4f}")
                st.dataframe(df_display, use_container_width=True)
                
                # Terminal value details
                st.subheader("Terminal Value Calculation")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Terminal FCF", f"${terminal_fcf/1e9:.2f}B")
                with col2:
                    st.metric("Terminal Value", f"${terminal_value/1e9:.2f}B")
                with col3:
                    st.metric("PV of Terminal Value", f"${pv_terminal/1e9:.2f}B")

else:
    st.info("👈 Enter a stock ticker in the sidebar and click 'Fetch Data' to begin")
    
    # Example section
    st.markdown("---")
    st.header("How to Use")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### Reverse DCF
        1. Enter a stock ticker (e.g., NVDA, AAPL, MSFT)
        2. Fetch the company's financial data
        3. Adjust terminal growth rate and WACC
        4. See what growth rate the market is pricing in
        
        **Use Case**: Understand market expectations
        """)
    
    with col2:
        st.markdown("""
        ### Fundamental DCF
        1. Enter a stock ticker
        2. Fetch the company's financial data
        3. Set your growth assumptions
        4. Calculate intrinsic value per share
        
        **Use Case**: Determine if stock is over/undervalued
        """)
    
    st.markdown("---")
    st.markdown("### Popular Stocks to Try")
    st.code("NVDA, AAPL, MSFT, GOOGL, AMZN, TSLA, META, NFLX, AMD, INTC")

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>Built with Streamlit & yfinance | Data provided by Yahoo Finance</p>
        <p>⚠️ This tool is for educational purposes only. Not financial advice. Always do your own research.</p>
    </div>
""", unsafe_allow_html=True)
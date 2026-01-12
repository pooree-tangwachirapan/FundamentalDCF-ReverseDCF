# Fetch stock data
if fetch_button and ticker_input:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        try:
            import time
            
            # Add delay to avoid rate limiting
            time.sleep(1)
            
            # Create ticker with session for better rate limit handling
            stock = yf.Ticker(ticker_input)
            
            # Try to get current price first (fastest endpoint)
            try:
                hist = stock.history(period="1d")
                current_price = hist['Close'].iloc[-1] if not hist.empty else 0
            except:
                current_price = 0
            
            # Get info with error handling (Fast Info)
            try:
                info = stock.fast_info
            except:
                info = {}
            
            # Get financial data (Cashflow & Income Statement)
            try:
                cashflow = stock.cashflow
                financials = stock.financials  # เพิ่ม: ดึงงบกำไรขาดทุนเพื่อหา Revenue
            except:
                cashflow = pd.DataFrame()
                financials = pd.DataFrame()
            
            # Extract Revenue from financials
            revenue = 0
            if not financials.empty:
                try:
                    # พยายามหา Key ที่เป็น Total Revenue
                    if 'Total Revenue' in financials.index:
                        revenue = financials.loc['Total Revenue'].iloc[0]
                    elif 'Operating Revenue' in financials.index:
                        revenue = financials.loc['Operating Revenue'].iloc[0]
                except:
                    pass

            # Extract key metrics with fallbacks
            stock_data = {
                'ticker': ticker_input,
                'current_price': current_price if current_price > 0 else info.get('currentPrice', info.get('regularMarketPrice', 0)) if isinstance(info, dict) else info.last_price,
                'shares_outstanding': info.shares if hasattr(info, 'shares') else 0,
                'market_cap': info.market_cap if hasattr(info, 'market_cap') else 0,
                'free_cash_flow': 0,
                'revenue': revenue, # แก้ไข: ใช้ค่า revenue ที่ดึงจาก financials
                'net_income': 0,
                'total_debt': 0,
                'cash': 0,
                'company_name': ticker_input
            }
            
            # Try to get Free Cash Flow (เหมือนเดิม)
            if not cashflow.empty:
                try:
                    if 'Free Cash Flow' in cashflow.index:
                        stock_data['free_cash_flow'] = cashflow.loc['Free Cash Flow'].iloc[0]
                    elif 'Operating Cash Flow' in cashflow.index:
                        ocf = cashflow.loc['Operating Cash Flow'].iloc[0] if 'Operating Cash Flow' in cashflow.index else 0
                        capex = cashflow.loc['Capital Expenditure'].iloc[0] if 'Capital Expenditure' in cashflow.index else 0
                        stock_data['free_cash_flow'] = ocf + capex
                except:
                    pass
            
            # Validate (เหมือนเดิม)
            if stock_data['current_price'] == 0:
                 # ... (ส่วน Error Handling เดิม ไม่มีการแก้ไข) ...
                 st.error("❌ Could not fetch complete data...")
                 # ... (Code ส่วน Manual Input คงเดิม) ...
            else:
                st.session_state.stock_data = stock_data
                st.success(f"✅ Successfully fetched data for {ticker_input}")
            
        except Exception as e:
             # ... (ส่วน Error Exception เดิม ไม่มีการแก้ไข) ...
             st.error(f"❌ Error fetching data: {error_msg}")

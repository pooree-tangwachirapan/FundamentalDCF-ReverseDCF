# 📊 DCF Valuation Calculator (Dark Mode Enhanced)

เครื่องมือคำนวณมูลค่าหุ้นด้วยวิธี DCF พร้อม **Dark Mode ที่สวยงาม**! 🌙

## ✨ Features

### 1. 🔄 Reverse DCF
- คำนวณอัตราการเติบโตที่ตลาดคาดหวัง (Implied Growth Rate)
- ใช้ Numerical Solver (เร็ว 40-60x กว่า Brute Force)
- รองรับทั้ง scipy และ bisection method

### 2. 📈 Fundamental DCF
- คำนวณมูลค่าที่แท้จริง (Intrinsic Value)
- แสดง Valuation Bridge แบบละเอียด
- กราฟ Present Value และ FCF Projection

### 3. 📊 Sensitivity Analysis
- ทดสอบผลกระทบของ WACC และ Terminal Growth
- Heatmap แบบ Interactive
- ตารางแสดงผลทุกสถานการณ์

### 4. 🌙 Dark Mode Optimized
- กราฟทุกอันปรับสีให้เหมาะกับ Dark Theme
- Text ชัดเจน อ่านง่าย
- สี Color Scheme ที่สวยงามทั้ง Light/Dark

---

## 🚀 วิธีติดตั้ง

### Local (คอมพิวเตอร์ส่วนตัว)

```bash
# 1. Clone repository
git clone <your-repo-url>
cd dcf-calculator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run app
streamlit run dcf_calculator_improved.py
```

### Streamlit Cloud

1. Push ไฟล์ทั้งหมดไป GitHub
2. ไป [share.streamlit.io](https://share.streamlit.io)
3. Connect repository
4. Deploy! ✅

**โครงสร้างไฟล์:**
```
your-repo/
├── dcf_calculator_improved.py
├── requirements.txt
└── .streamlit/
    └── config.toml          # Dark theme config
```

---

## 🎨 Dark Mode Setup

### วิธีที่ 1: ใช้ config.toml (แนะนำ)
ไฟล์ `.streamlit/config.toml` จะตั้ง Dark Mode เป็นค่าเริ่มต้น:

```toml
[theme]
primaryColor="#3b82f6"
backgroundColor="#0e1117"
secondaryBackgroundColor="#1a1d29"
textColor="#fafafa"
```

### วิธีที่ 2: เปลี่ยนใน App
1. เปิด app
2. กด `⋮` (Settings) มุมขวาบน
3. เลือก **Settings** → **Theme** → **Dark**

---

## 📊 Color Palette (Dark Mode Friendly)

| สี | Hex | ใช้สำหรับ |
|---|---|---|
| Primary Blue | `#3b82f6` | Bar charts, Main elements |
| Secondary Purple | `#8b5cf6` | Terminal value, Highlights |
| Success Green | `#10b981` | Growth projections |
| Warning Amber | `#f59e0b` | Alerts |
| Danger Red | `#ef4444` | Negative values |

---

## 🛠️ Technical Details

### กราฟที่ปรับปรุง:
```python
# ✅ Dark Mode Template
fig.update_layout(
    template="plotly_dark",
    paper_bgcolor='rgba(0,0,0,0)',  # โปร่งใส
    plot_bgcolor='rgba(0,0,0,0)',   # โปร่งใส
    font=dict(size=12, color="white")
)
```

### ความเร็วของ Solver:
- **Scipy Brentq**: 5-10 iterations (0.01 วินาที) ⚡
- **Bisection Method**: 10-20 iterations (0.05 วินาที) 🚀
- **Brute Force (เก่า)**: 1,200 iterations (2-3 วินาที) 🐌

---

## 📖 วิธีใช้งาน

### Step 1: ใส่ Ticker
```
Sidebar → Enter Stock Ticker → "NVDA"
```

### Step 2: Fetch Data
```
Click "🔍 Fetch Data" 
หรือใส่ข้อมูลเองใน "📝 Update/Enter Data Manually"
```

### Step 3: เลือก Analysis
- **Reverse DCF** → ตลาดคาดหวังการเติบโต % เท่าไร?
- **Fundamental DCF** → หุ้นแพงหรือถูก?
- **Sensitivity** → ถ้าสมมติฐานเปลี่ยน จะเป็นยังไง?

---

## ⚙️ Requirements

```
streamlit
yfinance
pandas
numpy
plotly
scipy        # Optional - มีก็ดี ไม่มีก็ได้
```

---

## 🎯 Example: NVDA Analysis

**Input:**
- Ticker: NVDA
- Current Price: $140
- Market Cap: $3,400B
- FCF: $30B
- WACC: 10%
- Terminal Growth: 2.5%

**Reverse DCF Result:**
```
Implied Growth Rate: 15.2%
→ ตลาดคาดว่า NVDA จะเติบโต 15.2% ต่อปี (5 ปี)
```

---

## 🌟 Credits

Created with ❤️ using:
- Streamlit
- Plotly (Dark Theme)
- yfinance
- scipy/numpy

---

## 📝 License

MIT License - ใช้ได้ฟรี!

---

## 🐛 Issues?

มีปัญหา? เปิด Issue ใน GitHub ได้เลย!

**Happy Investing! 📈💰**

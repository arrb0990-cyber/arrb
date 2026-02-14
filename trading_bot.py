import yfinance as yf
import pandas as pd
import time
import threading
import telebot
import matplotlib.pyplot as plt
from io import BytesIO

# --- 1. الإعدادات ---
TOKEN = '8288599325:AAHXJTLuQA7kUBQATwiURGbOygsH6Ij1szc'
MY_CHAT_ID = 721121366 

# التركيز على البيتكوين مع العملات القيادية والأسهم النشطة
SYMBOLS = ['BTC-USD', 'ETH-USD', 'NVDA', 'TSLA', 'AAPL']

bot = telebot.TeleBot(TOKEN)

def calculate_indicators(df):
    # حساب MACD
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal_line = macd.ewm(span=9, adjust=False).mean()
    
    # حساب RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs.fillna(0)))
    
    return rsi.iloc[-1], macd.iloc[-1], signal_line.iloc[-1]

def create_chart(symbol, prices, s1, r1, current_price, signal_type):
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(prices.index, prices['Close'], color='#f2a900' if 'BTC' in symbol else '#00d4ff', label='Price')
    ax.axhline(s1, color='#00ff00', linestyle='--', alpha=0.6, label=f'Support: {s1:.2f}')
    ax.axhline(r1, color='#ff0000', linestyle='--', alpha=0.6, label=f'Resistance: {r1:.2f}')
    
    color = 'green' if "CALL" in signal_type else 'red'
    ax.scatter(prices.index[-1], current_price, color=color, s=100, edgecolors='white', zorder=5)
    ax.set_title(f'Analysis: {symbol} (Live)')
    ax.legend()
    
    buf = BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf

def get_signal(symbol):
    try:
        # بيانات 15 دقيقة لتحليل البيتكوين
        m_data = yf.download(symbol, period='5d', interval='15m', progress=False, auto_adjust=True)
        if m_data.empty: return None, None
        if isinstance(m_data.columns, pd.MultiIndex): m_data.columns = m_data.columns.get_level_values(0)

        # حساب الدعم والمقاومة الأسبوعية (نقاط ارتكاز قوية)
        w_data = yf.download(symbol, period='1mo', interval='1wk', progress=False, auto_adjust=True)
        if isinstance(w_data.columns, pd.MultiIndex): w_data.columns = w_data.columns.get_level_values(0)
        h, l, c = float(w_data['High'].iloc[-2]), float(w_data['Low'].iloc[-2]), float(w_data['Close'].iloc[-2])
        pp = (h + l + c) / 3
        s1, r1 = (2 * pp) - h, (2 * pp) - l

        current_price = float(m_data['Close'].iloc[-1])
        rsi, macd_v, macd_s = calculate_indicators(m_data)

        signal_type = None
        # شروط البيتكوين: ارتداد من دعم أسبوعي + زخم صاعد
        if current_price <= (s1 * 1.001) and rsi < 40 and macd_v > macd_s:
            signal_type = "BUY/CALL 🟢 (ارتداد من دعم)"
        elif current_price >= (r1 * 0.999) and rsi > 60 and macd_v < macd_s:
            signal_type = "SELL/PUT 🔴 (ارتداد من مقاومة)"

        if signal_type:
            msg = (
                f"💎 **فرصة ذهبية للبيتكوين**\n"
                f"━━━━━━━━━━━━━━\n"
                f"📍 الاتجاه: **{signal_type}**\n"
                f"💰 السعر الحالي: **${current_price:,.2f}**\n"
                f"📊 RSI: {rsi:.1f} | MACD: متقاطع\n"
                f"━━━━━━━━━━━━━━\n"
                f"⚠️ تداول بحذر، البيتكوين عالي التذبذب!"
            )
            chart = create_chart(symbol, m_data, s1, r1, current_price, signal_type)
            return msg, chart
        return None, None
    except Exception as e:
        print(f"Error {symbol}: {e}")
        return None, None

def scanner_loop():
    print("🚀 البوت يراقب البيتكوين والأسهم الآن...")
    while True:
        for s in SYMBOLS:
            msg, chart = get_signal(s)
            if msg and chart:
                bot.send_photo(MY_CHAT_ID, photo=chart, caption=msg, parse_mode="Markdown")
                print(f"✅ تم إرسال إشارة لـ {s}")
            time.sleep(1)
        time.sleep(60) # الفحص كل دقيقة

threading.Thread(target=scanner_loop, daemon=True).start()
bot.send_message(MY_CHAT_ID, "🚀 تم تشغيل البوت بنجاح من السيرفر، جاري مراقبة السوق...")
bot.polling(none_stop=True)

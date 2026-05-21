import requests

TOKEN   = "8493063414:AAGs6qSi4zNFq84U9qOgvj6wfQkicGmySXI"
CHAT_ID = "1767336223"

LEVELS = {
    "ES":  {"ticker":"ES=F",    "entry":7375, "stop":7360, "target":7415},
    "BTC": {"ticker":"BTC-USD", "entry":76200, "stop":75000, "target":79500},
}

def get_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
    r = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
    return float(r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])

def alert(name, price, c):
    risk   = abs(c["entry"]-c["stop"])   * (5 if name=="ES" else 1)
    reward = abs(c["target"]-c["entry"]) * (5 if name=="ES" else 1)
    msg = (f"🚨 <b>SIGNAL — {name}</b>\n\n"
           f"💰 מחיר: <b>{price:,.2f}</b>\n"
           f"🎯 כניסה: {c['entry']:,.2f}\n"
           f"🛑 סטופ:  {c['stop']:,.2f}  (-${risk:,.0f})\n"
           f"✅ מטרה:  {c['target']:,.2f} (+${reward:,.0f})\n\n"
           f"⚠️ PAPER TRADING ONLY")
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id":CHAT_ID,"text":msg,"parse_mode":"HTML"})

for name, c in LEVELS.items():
    price = get_price(c["ticker"])
    print(f"{name}: {price:,.2f}")
    if abs(price - c["entry"]) / c["entry"] < 0.001 and price > c["stop"]:
        alert(name, price, c)
        print(f"✅ התראה נשלחה: {name}")
    else:
        print(f"😴 אין הזדמנות: {name}")

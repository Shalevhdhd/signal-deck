import requests

TOKEN   = "8493063414:AAGs6qSi4zNFq84U9qOgvj6wfQkicGmySXI"
CHAT_ID = "1767336223"

LEVELS = {
    "ES":   {"ticker": "ES=F",    "entry": 7375,  "stop": 7360,  "target": 7415,  "mult": 5},
    "NQ":   {"ticker": "NQ=F",    "entry": 29100, "stop": 28900, "target": 29600, "mult": 2},
    "BTC":  {"ticker": "BTC-USD", "entry": 76200, "stop": 75000, "target": 79500, "mult": 1},
    "ETH":  {"ticker": "ETH-USD", "entry": 2050,  "stop": 1980,  "target": 2200,  "mult": 1},
    "GOLD": {"ticker": "GC=F",    "entry": 4480,  "stop": 4440,  "target": 4580,  "mult": 1},
    "OIL":  {"ticker": "CL=F",    "entry": 102,   "stop": 100,   "target": 107,   "mult": 1},
}

def get_price(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
    return float(r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"])

def send_alert(name, price, c):
    risk   = abs(c["entry"] - c["stop"])   * c["mult"]
    reward = abs(c["target"] - c["entry"]) * c["mult"]
    msg = (
        f"SIGNAL DECK - {name}\n\n"
        f"Price: {price:,.2f}\n"
        f"Entry: {c['entry']:,.2f}\n"
        f"Stop:  {c['stop']:,.2f}  (-${risk:,.0f})\n"
        f"Target:{c['target']:,.2f} (+${reward:,.0f})\n\n"
        f"PAPER TRADING ONLY"
    )
    requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

for name, c in LEVELS.items():
    try:
        price = get_price(c["ticker"])
        print(f"{name}: {price:,.2f}")
        near = abs(price - c["entry"]) / c["entry"] < 0.001
        safe = price > c["stop"]
        if near and safe:
            send_alert(name, price, c)
            print(f"Alert sent: {name}")
        else:
            print(f"No signal: {name}")
    except Exception as e:
        print(f"Error {name}: {e}")")e}")

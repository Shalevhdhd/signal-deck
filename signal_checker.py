import requests
import json
import os
from datetime import datetime, timezone

TOKEN   = "8493063414:AAGV8a7eCkDey481lukc-GR4mpsOFV52GTw"
CHAT_ID = "1767336223"
LOG_FILE = "sent_signals.json"

MARKETS = {
    "ES":   {"ticker": "ES=F",    "mult": 5},
    "NQ":   {"ticker": "NQ=F",    "mult": 2},
    "BTC":  {"ticker": "BTC-USD", "mult": 1},
    "ETH":  {"ticker": "ETH-USD", "mult": 1},
    "GOLD": {"ticker": "GC=F",    "mult": 1},
    "OIL":  {"ticker": "CL=F",    "mult": 1},
}

def load_sent():
    if not os.path.exists(LOG_FILE):
        return {}
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return {k: v for k, v in data.items() if v.get("date") == today}
    except:
        return {}

def save_sent(sent):
    with open(LOG_FILE, "w") as f:
        json.dump(sent, f)

def already_sent(sent, name, direction):
    return name + "_" + direction in sent

def mark_sent(sent, name, direction):
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sent[name + "_" + direction] = {"date": today, "time": datetime.now(timezone.utc).strftime("%H:%M")}
    return sent

def get_candles(ticker):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + ticker + "?interval=5m&range=2d"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    data = r.json()["chart"]["result"][0]
    closes = [c for c in data["indicators"]["quote"][0]["close"] if c is not None]
    highs  = [h for h in data["indicators"]["quote"][0]["high"]  if h is not None]
    lows   = [l for l in data["indicators"]["quote"][0]["low"]   if l is not None]
    price  = float(data["meta"]["regularMarketPrice"])
    prev   = float(data["meta"]["previousClose"])
    return closes, highs, lows, price, prev

def ema(data, period):
    if len(data) < period:
        return None
    k = 2 / (period + 1)
    e = sum(data[:period]) / period
    for v in data[period:]:
        e = v * k + e * (1 - k)
    return e

def calc_macd(closes):
    if len(closes) < 26:
        return None, None
    e12 = ema(closes, 12)
    e26 = ema(closes, 26)
    e12p = ema(closes[:-1], 12)
    e26p = ema(closes[:-1], 26)
    if None in [e12, e26, e12p, e26p]:
        return None, None
    return e12 - e26, e12p - e26p

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50
    gains  = [max(closes[i]-closes[i-1], 0) for i in range(1, len(closes))]
    losses = [max(closes[i-1]-closes[i], 0) for i in range(1, len(closes))]
    ag = sum(gains[-period:]) / period
    al = sum(losses[-period:]) / period
    if al == 0:
        return 100
    return round(100 - (100 / (1 + ag/al)), 1)

def calc_vwap(closes, highs, lows):
    n = min(50, len(closes), len(highs), len(lows))
    typicals = [(highs[-n:][i] + lows[-n:][i] + closes[-n:][i]) / 3 for i in range(n)]
    return round(sum(typicals) / len(typicals), 2)

def analyze(name, closes, highs, lows, price, prev):
    change_pct = round((price - prev) / prev * 100, 2)
    macd, macd_prev = calc_macd(closes)
    rsi = calc_rsi(closes)
    vwap = calc_vwap(closes, highs, lows)
    score = 0
    if macd is not None:
        if macd > 0 and macd > macd_prev: score += 1
        elif macd < 0 and macd < macd_prev: score -= 1
    if rsi < 35: score += 1
    elif rsi > 65: score -= 1
    if price > vwap: score += 1
    else: score -= 1
    if change_pct > 0: score += 0.5
    else: score -= 0.5
    if score >= 2:
        direction = "LONG"
        entry  = round(price * 0.995, 2)
        stop   = round(price * 0.990, 2)
        target = round(price * 1.015, 2)
        confidence = "HIGH" if score >= 2.5 else "MEDIUM"
    elif score <= -2:
        direction = "SHORT"
        entry  = round(price * 1.005, 2)
        stop   = round(price * 1.010, 2)
        target = round(price * 0.985, 2)
        confidence = "HIGH" if score <= -2.5 else "MEDIUM"
    else:
        return None
    return {"name": name, "direction": direction, "confidence": confidence,
            "price": price, "entry": entry, "stop": stop, "target": target,
            "rsi": rsi, "vwap": vwap, "change_pct": change_pct, "score": score}

def send_alert(s, mult):
    risk   = abs(s["entry"] - s["stop"])   * mult
    reward = abs(s["target"] - s["entry"]) * mult
    rr     = round(reward / risk, 1) if risk > 0 else 0
    arrow  = "+" if s["change_pct"] >= 0 else ""
    msg = (
        "SIGNAL DECK - " + s["name"] + " " + s["direction"] + " [" + s["confidence"] + "]\n\n"
        "Price:  " + str(s["price"]) + " (" + arrow + str(s["change_pct"]) + "%)\n"
        "Entry:  " + str(s["entry"]) + "\n"
        "Stop:   " + str(s["stop"]) + "  (-$" + str(int(risk)) + ")\n"
        "Target: " + str(s["target"]) + " (+$" + str(int(reward)) + ")\n"
        "R:R:    1:" + str(rr) + "\n\n"
        "RSI: " + str(s["rsi"]) + " | VWAP: " + str(s["vwap"]) + "\n\n"
        "PAPER TRADING ONLY"
    )
    requests.post(
        "https://api.telegram.org/bot" + TOKEN + "/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg}
    )

sent = load_sent()
changed = False

for name, c in MARKETS.items():
    try:
        closes, highs, lows, price, prev = get_candles(c["ticker"])
        print(name + ": " + str(round(price, 2)))
        result = analyze(name, closes, highs, lows, price, prev)
        if result:
            if already_sent(sent, name, result["direction"]):
                print("Already sent today: " + name + " " + result["direction"])
            else:
                send_alert(result, c["mult"])
                sent = mark_sent(sent, name, result["direction"])
                changed = True
                print("Alert sent: " + name + " " + result["direction"])
        else:
            for d in ["LONG", "SHORT"]:
                key = name + "_" + d
                if key in sent:
                    del sent[key]
                    changed = True
            print("No signal: " + name)
    except Exception as err:
        print("Error " + name + ": " + str(err))

if changed:
    save_sent(sent)

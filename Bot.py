import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

BOT_TOKEN = os.environ.get("BOT_TOKEN")


def get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BTC-Risk-Bot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


# ---------- TELEGRAM ----------

def telegram(method, params=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"

    if params:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
    else:
        req = urllib.request.Request(url)

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def get_chat_id():
    data = telegram("getUpdates")
    updates = data.get("result", [])

    if not updates:
        return None

    # Берём последнее сообщение пользователя
    for update in reversed(updates):
        message = update.get("message")
        if message and message.get("chat"):
            return message["chat"]["id"]

    return None


def send_message(chat_id, text):
    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )


# ---------- BINANCE ----------

def binance_ticker(symbol):
    url = (
        "https://api.binance.com/api/v3/ticker/24hr"
        f"?symbol={symbol}"
    )

    data = get_json(url)

    return {
        "price": float(data["lastPrice"]),
        "change": float(data["priceChangePercent"]),
        "volume": float(data["quoteVolume"])
    }


def get_binance():
    btc = binance_ticker("BTCUSDT")
    ethbtc = binance_ticker("ETHBTC")

    return btc, ethbtc


# ---------- YAHOO ----------

def yahoo(symbol):
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        + urllib.parse.quote(symbol)
        + "?range=5d&interval=1d"
    )

    data = get_json(url)
    result = data["chart"]["result"][0]

    closes = [
        x for x in result["indicators"]["quote"][0]["close"]
        if x is not None
    ]

    if len(closes) < 2:
        return None

    price = closes[-1]
    previous = closes[-2]

    change = (price / previous - 1) * 100

    return price, change


# ---------- UKRAINE FX ----------

def nbu_rate(currency):
    url = (
        "https://bank.gov.ua/NBUStatService/v1/statdirectory/"
        f"exchange?valcode={currency}&json"
    )

    data = get_json(url)

    if not data:
        return None

    return float(data[0]["rate"])


# ---------- BTC DOMINANCE ----------

def btc_dominance():
    url = "https://api.coingecko.com/api/v3/global"

    data = get_json(url)

    return float(
        data["data"]["market_cap_percentage"]["btc"]
    )


# ---------- SCORE ----------

def calculate_score(btc, vix, dxy, nasdaq, sp500, us10y):

    score = 0

    # VIX
    if vix:
        if vix[1] < 0:
            score += 15
        else:
            score -= 15

    # DXY
    if dxy:
        if dxy[1] < 0:
            score += 15
        else:
            score -= 15

    # NASDAQ
    if nasdaq:
        if nasdaq[1] > 0:
            score += 15
        else:
            score -= 15

    # S&P500
    if sp500:
        if sp500[1] > 0:
            score += 10
        else:
            score -= 10

    # US10Y
    if us10y:
        if us10y[1] < 0:
            score += 10
        else:
            score -= 10

    # BTC momentum
    if btc["change"] > 1:
        score += 15
    elif btc["change"] < -1:
        score -= 15

    # BTC relative strength vs Nasdaq
    if nasdaq:
        if btc["change"] > nasdaq[1]:
            score += 10
        elif btc["change"] < nasdaq[1]:
            score -= 10

    return max(-100, min(100, score))


def signal_from_score(score):

    if score >= 60:
        return "🟢 STRONG LONG", "RISK-ON"

    if score >= 30:
        return "🟢 LONG BIAS", "RISK-ON"

    if score <= -60:
        return "🔴 STRONG SHORT", "RISK-OFF"

    if score <= -30:
        return "🔴 SHORT BIAS", "RISK-OFF"

    return "🟡 WAIT", "MIXED"


# ---------- MAIN ----------

def main():

    if not BOT_TOKEN:
        raise Exception("BOT_TOKEN is missing")

    chat_id = get_chat_id()

    if not chat_id:
        print("No Telegram chat found.")
        print("Open the bot and press START.")
        return

    # Market data
    btc, ethbtc = get_binance()

    vix = yahoo("^VIX")
    dxy = yahoo("DX-Y.NYB")
    nasdaq = yahoo("^IXIC")
    sp500 = yahoo("^GSPC")
    us10y = yahoo("^TNX")

    # Ukraine
    usd_uah = nbu_rate("USD")
    eur_uah = nbu_rate("EUR")

    # Crypto
    dominance = btc_dominance()

    score = calculate_score(
        btc,
        vix,
        dxy,
        nasdaq,
        sp500,
        us10y
    )

    signal, regime = signal_from_score(score)

    # BTC volume in billions
    btc_volume = btc["volume"] / 1_000_000_000

    # ETH/BTC
    ethbtc_value = ethbtc["price"]

    now = datetime.now(timezone.utc).strftime(
        "%d.%m.%Y %H:%M UTC"
    )

    text = f"""🤖 BTC RISK-ON ROBOT

{now}

━━━━━━━━━━━━━━━━━━
🇺🇦 УКРАИНА
━━━━━━━━━━━━━━━━━━

💵 USD/UAH: {usd_uah:.2f}
💶 EUR/UAH: {eur_uah:.2f}

━━━━━━━━━━━━━━━━━━
🌎 RISK-ON / RISK-OFF
━━━━━━━━━━━━━━━━━━

RISK SCORE: {score:+d}

Режим: {regime}

😨 VIX:
{vix[0]:.2f} ({vix[1]:+.2f}%)

💵 DXY:
{dxy[0]:.2f} ({dxy[1]:+.2f}%)

📈 NASDAQ:
{nasdaq[0]:,.0f} ({nasdaq[1]:+.2f}%)

📊 S&P500:
{sp500[0]:,.0f} ({sp500[1]:+.2f}%)

🏦 US10Y:
{us10y[0]:.2f}% ({us10y[1]:+.2f}%)

━━━━━━━━━━━━━━━━━━
₿ CRYPTO
━━━━━━━━━━━━━━━━━━

₿ BTC:
${btc["price"]:,.0f} ({btc["change"]:+.2f}%)

📊 BTC 24h volume:
${btc_volume:.2f}B

₿ BTC Dominance:
{dominance:.2f}%

Ξ ETH/BTC:
{ethbtc_value:.5f}

━━━━━━━━━━━━━━━━━━
🎯 РЕШЕНИЕ
━━━━━━━━━━━━━━━━━━

{signal}

"""

    # Additional interpretation
    if signal.startswith("🟢"):
        text += (
            "Идея: рынок поддерживает LONG-сценарий.\n"
            "Но вход ищем по самому BTC, а не только по Risk Score."
        )

    elif signal.startswith("🔴"):
        text += (
            "Идея: фон неблагоприятный для LONG.\n"
            "При слабом BTC приоритет — SHORT или ожидание."
        )

    else:
        text += (
            "Идея: рынок смешанный.\n"
            "Лучше ждать подтверждения BTC."
        )

    text += "\n\n⚠️ Risk Score — фильтр, а не гарантия сделки."

    send_message(chat_id, text)


if __name__ == "__main__":
    main()

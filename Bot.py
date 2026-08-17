import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")


def get_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BTC-Risk-Bot/1.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def telegram(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"

    if params:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
    else:
        req = urllib.request.Request(url)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode())


def get_crypto():

    ids = (
        "bitcoin,ethereum,solana,hype,"
        "ripple,binancecoin,dogecoin,cardano,"
        "sui,avalanche-2,chainlink,the-open-network"
    )

    url = (
        "https://api.coingecko.com/api/v3/simple/price?"
        f"ids={ids}"
        "&vs_currencies=usd"
        "&include_24hr_change=true"
    )

    return get_json(url)


def get_yahoo(symbol):

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


def get_usd_uah():

    url = (
        "https://bank.gov.ua/NBUStatService/v1/statdirectory/"
        "exchange?valcode=USD&json"
    )

    data = get_json(url)

    return float(data[0]["rate"])


def get_gold():

    data = get_yahoo("GC=F")

    if data:
        return data[0], data[1]

    return None, None


def calculate_score(btc, vix, dxy, nasdaq, sp500, us10y):

    score = 0

    # BTC
    if btc > 1:
        score += 20
    elif btc < -1:
        score -= 20

    # VIX
    if vix < 0:
        score += 15
    else:
        score -= 15

    # DXY
    if dxy < 0:
        score += 15
    else:
        score -= 15

    # NASDAQ
    if nasdaq > 0:
        score += 15
    else:
        score -= 15

    # S&P
    if sp500 > 0:
        score += 10
    else:
        score -= 10

    # US10Y
    if us10y < 0:
        score += 10
    else:
        score -= 10

    return max(-100, min(100, score))


def get_signal(score):

    if score >= 60:
        return "🟢 STRONG LONG"

    if score >= 30:
        return "🟢 LONG BIAS"

    if score <= -60:
        return "🔴 STRONG SHORT"

    if score <= -30:
        return "🔴 SHORT BIAS"

    return "🟡 WAIT"


def fmt(value, digits=2):

    if value is None:
        return "N/A"

    return f"{value:,.{digits}f}"


def main():

    print("BTC RISK BOT STARTED")

    crypto = get_crypto()

    btc = crypto["bitcoin"]
    eth = crypto["ethereum"]
    sol = crypto["solana"]
    hype = crypto["hype"]
    xrp = crypto["ripple"]
    bnb = crypto["binancecoin"]
    doge = crypto["dogecoin"]
    ada = crypto["cardano"]
    sui = crypto["sui"]
    avax = crypto["avalanche-2"]
    link = crypto["chainlink"]
    ton = crypto["the-open-network"]

    vix = get_yahoo("^VIX")
    dxy = get_yahoo("DX-Y.NYB")
    nasdaq = get_yahoo("^IXIC")
    sp500 = get_yahoo("^GSPC")
    us10y = get_yahoo("^TNX")

    gold_price, gold_change = get_gold()

    usd_uah = get_usd_uah()

    score = calculate_score(
        btc["usd_24h_change"],
        vix[1],
        dxy[1],
        nasdaq[1],
        sp500[1],
        us10y[1]
    )

    signal = get_signal(score)

    btc_change = btc["usd_24h_change"]

    if score >= 30 and btc_change > 0:
        confirmation = "🟢 BTC подтверждает Risk-On"

    elif score >= 30 and btc_change <= 0:
        confirmation = "⚠️ Risk-On есть, но BTC слабый"

    elif score <= -30 and btc_change < 0:
        confirmation = "🔴 BTC подтверждает Risk-Off"

    else:
        confirmation = "🟡 BTC не даёт подтверждения"

    now = datetime.now(timezone.utc).strftime(
        "%d.%m.%Y %H:%M UTC"
    )

    message = f"""
🤖 BTC RISK MONITOR

🕐 {now}

━━━━━━━━━━━━━━━━━━
₿ CRYPTO
━━━━━━━━━━━━━━━━━━

₿ BTC
${fmt(btc["usd"])}  {btc_change:+.2f}%

Ξ ETH
${fmt(eth["usd"])}  {eth["usd_24h_change"]:+.2f}%

◎ SOL
${fmt(sol["usd"])}  {sol["usd_24h_change"]:+.2f}%

🔥 HYPE
${fmt(hype["usd"], 4)}  {hype["usd_24h_change"]:+.2f}%

XRP
${fmt(xrp["usd"])}  {xrp["usd_24h_change"]:+.2f}%

BNB
${fmt(bnb["usd"])}  {bnb["usd_24h_change"]:+.2f}%

DOGE
${fmt(doge["usd"], 4)}  {doge["usd_24h_change"]:+.2f}%

ADA
${fmt(ada["usd"], 4)}  {ada["usd_24h_change"]:+.2f}%

SUI
${fmt(sui["usd"])}  {sui["usd_24h_change"]:+.2f}%

AVAX
${fmt(avax["usd"])}  {avax["usd_24h_change"]:+.2f}%

LINK
${fmt(link["usd"])}  {link["usd_24h_change"]:+.2f}%

TON
${fmt(ton["usd"])}  {ton["usd_24h_change"]:+.2f}%

━━━━━━━━━━━━━━━━━━
🌎 MACRO
━━━━━━━━━━━━━━━━━━

DXY
{fmt(dxy[0])}  {dxy[1]:+.2f}%

VIX
{fmt(vix[0])}  {vix[1]:+.2f}%

NASDAQ
{fmt(nasdaq[0], 0)}  {nasdaq[1]:+.2f}%

S&P500
{fmt(sp500[0], 0)}  {sp500[1]:+.2f}%

US10Y
{fmt(us10y[0])}%  {us10y[1]:+.2f}%

🥇 GOLD
${fmt(gold_price)}  {gold_change:+.2f}%

🇺🇦 USD/UAH
{fmt(usd_uah)}

━━━━━━━━━━━━━━━━━━
🎯 ALGORITHM
━━━━━━━━━━━━━━━━━━

RISK SCORE: {score:+d}/100

{signal}

{confirmation}

━━━━━━━━━━━━━━━━━━

⚠️ Это рыночный фильтр.
Не является гарантией сделки.
"""

    # Получаем последний Telegram chat
    updates = telegram("getUpdates")

    if not updates.get("ok"):
        raise Exception("Telegram API error")

    results = updates.get("result", [])

    if not results:
        print("No Telegram chat found.")
        return

    chat_id = None

    for update in reversed(results):

        message_data = update.get("message")

        if message_data:
            chat_id = message_data["chat"]["id"]
            break

    if not chat_id:
        print("Chat ID not found.")
        return

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message
        }
    )

    print("MESSAGE SENT")


if __name__ == "__main__":
    main()

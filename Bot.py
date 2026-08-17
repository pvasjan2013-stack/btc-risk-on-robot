import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")


# =========================
# НАСТРОЙКИ
# =========================

CRYPTO_IDS = {
    "bitcoin": "BTC",
    "ethereum": "ETH",
    "solana": "SOL",
    "hype": "HYPE",
    "ripple": "XRP",
    "binancecoin": "BNB",
    "dogecoin": "DOGE",
    "cardano": "ADA",
    "sui": "SUI",
    "avalanche-2": "AVAX",
    "chainlink": "LINK",
    "the-open-network": "TON"
}


# =========================
# HTTP
# =========================

def get_json(url):

    try:

        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "BTC-Risk-Bot/2.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except Exception as error:

        print("REQUEST ERROR:", error)

        return None


# =========================
# TELEGRAM
# =========================

def telegram(method, params=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TOKEN}/{method}"
    )

    try:

        if params:

            data = urllib.parse.urlencode(
                params
            ).encode()

            request = urllib.request.Request(
                url,
                data=data
            )

        else:

            request = urllib.request.Request(
                url
            )

        with urllib.request.urlopen(
            request,
            timeout=30
        ) as response:

            return json.loads(
                response.read().decode()
            )

    except Exception as error:

        print("TELEGRAM ERROR:", error)

        return None


# =========================
# ФОРМАТИРОВАНИЕ
# =========================

def number(value, digits=2):

    if value is None:
        return "N/A"

    try:
        return f"{float(value):,.{digits}f}"

    except:
        return "N/A"


def percent(value):

    if value is None:
        return "N/A"

    try:
        return f"{float(value):+.2f}%"

    except:
        return "N/A"


# =========================
# CRYPTO
# =========================

def get_crypto():

    ids = ",".join(
        CRYPTO_IDS.keys()
    )

    url = (
        "https://api.coingecko.com/api/v3/"
        "simple/price?"
        f"ids={ids}"
        "&vs_currencies=usd"
        "&include_24hr_change=true"
    )

    data = get_json(url)

    if not data:

        print("Crypto data unavailable")

        return {}

    return data


# =========================
# YAHOO
# =========================

def get_yahoo(symbol):

    url = (
        "https://query1.finance.yahoo.com/"
        "v8/finance/chart/"
        + urllib.parse.quote(symbol)
        + "?range=5d&interval=1d"
    )

    data = get_json(url)

    if not data:

        return None, None

    try:

        result = data["chart"]["result"][0]

        closes = (
            result["indicators"]
            ["quote"][0]
            ["close"]
        )

        closes = [
            x for x in closes
            if x is not None
        ]

        if len(closes) < 2:

            return None, None

        current = float(closes[-1])
        previous = float(closes[-2])

        change = (
            (current / previous) - 1
        ) * 100

        return current, change

    except Exception as error:

        print(
            f"Yahoo error {symbol}:",
            error
        )

        return None, None


# =========================
# USD / UAH
# =========================

def get_usd_uah():

    url = (
        "https://bank.gov.ua/"
        "NBUStatService/v1/statdirectory/"
        "exchange?valcode=USD&json"
    )

    data = get_json(url)

    try:

        return float(
            data[0]["rate"]
        )

    except:

        return None


# =========================
# RISK SCORE
# =========================

def calculate_score(
    btc_change,
    vix_change,
    dxy_change,
    nasdaq_change,
    sp500_change,
    us10y_change
):

    score = 0

    # BTC

    if btc_change is not None:

        if btc_change > 1:
            score += 20

        elif btc_change < -1:
            score -= 20


    # VIX
    # падающий VIX = risk-on

    if vix_change is not None:

        if vix_change < 0:
            score += 15

        elif vix_change > 0:
            score -= 15


    # DXY
    # падающий доллар = risk-on

    if dxy_change is not None:

        if dxy_change < 0:
            score += 15

        elif dxy_change > 0:
            score -= 15


    # NASDAQ

    if nasdaq_change is not None:

        if nasdaq_change > 0:
            score += 15

        elif nasdaq_change < 0:
            score -= 15


    # S&P500

    if sp500_change is not None:

        if sp500_change > 0:
            score += 10

        elif sp500_change < 0:
            score -= 10


    # US10Y

    if us10y_change is not None:

        if us10y_change < 0:
            score += 10

        elif us10y_change > 0:
            score -= 10


    return max(
        -100,
        min(100, score)
    )


# =========================
# SIGNAL
# =========================

def signal(score):

    if score >= 60:
        return "🟢 STRONG LONG"

    if score >= 30:
        return "🟢 LONG BIAS"

    if score <= -60:
        return "🔴 STRONG SHORT"

    if score <= -30:
        return "🔴 SHORT BIAS"

    return "🟡 WAIT"


# =========================
# MAIN
# =========================

def main():

    print("======================")
    print("BTC RISK BOT STARTED")
    print("======================")


    # Telegram

    me = telegram("getMe")

    if not me or not me.get("ok"):

        raise Exception(
            "Telegram BOT_TOKEN error"
        )

    print(
        "Telegram:",
        me["result"].get("username")
    )


    # Crypto

    crypto = get_crypto()

    print(
        "Crypto assets:",
        len(crypto)
    )


    # Macro

    vix_price, vix_change = (
        get_yahoo("^VIX")
    )

    dxy_price, dxy_change = (
        get_yahoo("DX-Y.NYB")
    )

    nasdaq_price, nasdaq_change = (
        get_yahoo("^IXIC")
    )

    sp500_price, sp500_change = (
        get_yahoo("^GSPC")
    )

    us10y_price, us10y_change = (
        get_yahoo("^TNX")
    )


    gold_price, gold_change = (
        get_yahoo("GC=F")
    )


    usd_uah = get_usd_uah()


    # BTC

    btc = crypto.get(
        "bitcoin",
        {}
    )

    btc_price = btc.get(
        "usd"
    )

    btc_change = btc.get(
        "usd_24h_change"
    )


    # SCORE

    score = calculate_score(
        btc_change,
        vix_change,
        dxy_change,
        nasdaq_change,
        sp500_change,
        us10y_change
    )


    market_signal = signal(score)


    # BTC confirmation

    if (
        score >= 30
        and btc_change is not None
        and btc_change > 0
    ):

        confirmation = (
            "🟢 BTC подтверждает Risk-On"
        )

    elif (
        score >= 30
        and btc_change is not None
        and btc_change <= 0
    ):

        confirmation = (
            "⚠️ Risk-On есть, "
            "но BTC пока слабый"
        )

    elif (
        score <= -30
        and btc_change is not None
        and btc_change < 0
    ):

        confirmation = (
            "🔴 BTC подтверждает Risk-Off"
        )

    else:

        confirmation = (
            "🟡 BTC пока не подтверждает "
            "сигнал"
        )


    # =========================
    # CRYPTO TEXT
    # =========================

    crypto_text = ""

    for coin_id, ticker in CRYPTO_IDS.items():

        coin = crypto.get(
            coin_id,
            {}
        )

        price = coin.get(
            "usd"
        )

        change = coin.get(
            "usd_24h_change"
        )

        if ticker == "HYPE":

            price_text = number(
                price,
                4
            )

        else:

            price_text = number(
                price,
                2
            )

        crypto_text += (
            f"{ticker:<5} "
            f"${price_text}  "
            f"{percent(change)}\n"
        )


    # =========================
    # TIME
    # =========================

    from zoneinfo import ZoneInfo

now = datetime.now(
    ZoneInfo("Europe/Kyiv")
).strftime(
    "%d.%m.%Y %H:%M"
)


    # =========================
    # MESSAGE
    # =========================

    message = f"""
🤖 BTC RISK MONITOR

🕐 {now}

━━━━━━━━━━━━━━━━━━
₿ CRYPTO
━━━━━━━━━━━━━━━━━━

{crypto_text}
━━━━━━━━━━━━━━━━━━
🌎 MACRO
━━━━━━━━━━━━━━━━━━

DXY
{number(dxy_price)}  {percent(dxy_change)}
VIX
{number(vix_price)}  {percent(vix_change)}
NASDAQ
{number(nasdaq_price, 0)}  {percent(nasdaq_change)}
S&P500
{number(sp500_price, 0)}  {percent(sp500_change)}
US10Y
{number(us10y_price)}%  {percent(us10y_change)}
🥇 GOLD
${number(gold_price)}  {percent(gold_change)}
🇺🇦 USD/UAH
{number(usd_uah)}

━━━━━━━━━━━━━━━━━━
🎯 ALGORITHM
━━━━━━━━━━━━━━━━━━

RISK SCORE: {score:+d}/100

{market_signal}

{confirmation}

━━━━━━━━━━━━━━━━━━

ℹ️ N/A означает, что источник
временно не отдал значение.
⚠️ Это рыночный фильтр,
а не гарантия сделки.
"""


    # =========================
    # TELEGRAM CHAT
    # =========================

    updates = telegram(
        "getUpdates"
    )

    if not updates or not updates.get("ok"):

        raise Exception(
            "Telegram getUpdates error"
        )


    results = updates.get(
        "result",
        []
    )


    if not results:

        print(
            "No Telegram chat found."
        )

        print(
            "Send /start to the bot."
        )

        return


    chat_id = None


    for update in reversed(results):

        msg = update.get(
            "message"
        )

        if msg and msg.get("chat"):

            chat_id = msg["chat"]["id"]

            break


    if not chat_id:

        print(
            "Chat ID not found."
        )

        return


    # =========================
    # SEND
    # =========================

    result = telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message
        }
    )


    if not result or not result.get("ok"):

        print(
            "Telegram send error:",
            result
        )

        raise Exception(
            "Message was not sent"
        )


    print("======================")
    print("MESSAGE SENT")
    print("======================")


if __name__ == "__main__":

    main()

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is missing")


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


def get_json(url):

    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "BTC-Risk-Bot/4.0"
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
        return {}

    return data


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


def get_btc_dominance():

    url = (
        "https://api.coingecko.com/api/v3/"
        "global"
    )

    data = get_json(url)

    try:

        return float(
            data["data"]
            ["market_cap_percentage"]
            ["btc"]
        )

    except:
        return None


def get_binance_funding():

    url = (
        "https://fapi.binance.com/"
        "fapi/v1/premiumIndex?"
        "symbol=BTCUSDT"
    )

    data = get_json(url)

    try:

        return float(
            data["lastFundingRate"]
        ) * 100

    except:
        return None


def get_binance_oi():

    url = (
        "https://fapi.binance.com/"
        "fapi/v1/openInterest?"
        "symbol=BTCUSDT"
    )

    data = get_json(url)

    try:

        return float(
            data["openInterest"]
        )

    except:
        return None


def get_binance_liquidations():

    url = (
        "https://fapi.binance.com/"
        "fapi/v1/allForceOrders?"
        "symbol=BTCUSDT&"
        "limit=100"
    )

    data = get_json(url)

    if not data:
        return None, None

    try:

        long_liq = 0
        short_liq = 0

        for order in data:

            qty = float(
                order["origQty"]
            )

            price = float(
                order["price"]
            )

            value = qty * price

            side = order["side"]

            if side == "SELL":
                long_liq += value

            elif side == "BUY":
                short_liq += value

        return long_liq, short_liq

    except:

        return None, None


def calculate_score(
    btc_change,
    vix_change,
    dxy_change,
    nasdaq_change,
    sp500_change,
    us10y_change
):

    score = 0

    if btc_change is not None:

        if btc_change > 1:
            score += 20

        elif btc_change < -1:
            score -= 20

    if vix_change is not None:

        if vix_change < 0:
            score += 15

        elif vix_change > 0:
            score -= 15

    if dxy_change is not None:

        if dxy_change < 0:
            score += 15

        elif dxy_change > 0:
            score -= 15

    if nasdaq_change is not None:

        if nasdaq_change > 0:
            score += 15

        elif nasdaq_change < 0:
            score -= 15

    if sp500_change is not None:

        if sp500_change > 0:
            score += 10

        elif sp500_change < 0:
            score -= 10

    if us10y_change is not None:

        if us10y_change < 0:
            score += 10

        elif us10y_change > 0:
            score -= 10

    return max(
        -100,
        min(100, score)
    )


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


def get_chat_id():

    updates = telegram(
        "getUpdates"
    )

    if not updates or not updates.get("ok"):
        return None

    results = updates.get(
        "result",
        []
    )

    for update in reversed(results):

        message = update.get(
            "message"
        )

        if message and message.get("chat"):

            return message["chat"]["id"]

    return None


def make_keyboard():

    return json.dumps({
        "inline_keyboard": [
            [
                {
                    "text": "📊 Обновить отчёт",
                    "callback_data": "report"
                }
            ]
        ]
    })


def build_report():

    crypto = get_crypto()

    btc = crypto.get(
        "bitcoin",
        {}
    )

    btc_change = btc.get(
        "usd_24h_change"
    )

    vix_price, vix_change = get_yahoo("^VIX")
    dxy_price, dxy_change = get_yahoo("DX-Y.NYB")
    nasdaq_price, nasdaq_change = get_yahoo("^IXIC")
    sp500_price, sp500_change = get_yahoo("^GSPC")
    us10y_price, us10y_change = get_yahoo("^TNX")
    gold_price, gold_change = get_yahoo("GC=F")

    usd_uah = get_usd_uah()

    dominance = get_btc_dominance()

    funding = get_binance_funding()

    oi = get_binance_oi()

    long_liq, short_liq = get_binance_liquidations()

    score = calculate_score(
        btc_change,
        vix_change,
        dxy_change,
        nasdaq_change,
        sp500_change,
        us10y_change
    )

    market_signal = get_signal(
        score
    )

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
            "⚠️ Risk-On есть, но BTC слабый"
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
            "🟡 BTC пока не подтверждает сигнал"
        )

    now = datetime.now(
        ZoneInfo("Europe/Kyiv")
    ).strftime(
        "%d.%m.%Y %H:%M"
    )

    if funding is not None:

        if funding > 0.01:
            funding_text = "🔴 Лонги перегреты"

        elif funding < -0.01:
            funding_text = "🟢 Шорты перегреты"

        else:
            funding_text = "🟡 Нейтральный"

    else:

        funding_text = "N/A"

    if long_liq is not None:

        liquidation_text = (
            f"Long ${number(long_liq / 1_000_000)}M / "
            f"Short ${number(short_liq / 1_000_000)}M"
        )

    else:

        liquidation_text = "N/A"

    message = f"""
🤖 BTC RISK MONITOR

🕐 {now}

━━━━━━━━━━━━━━━━━━
🌎 MACRO
━━━━━━━━━━━━━━━━━━

DXY     {number(dxy_price)}  {percent(dxy_change)}
VIX     {number(vix_price)}  {percent(vix_change)}
NASDAQ  {number(nasdaq_price, 0)}  {percent(nasdaq_change)}
S&P500  {number(sp500_price, 0)}  {percent(sp500_change)}
US10Y   {number(us10y_price)}%  {percent(us10y_change)}
GOLD    ${number(gold_price)}  {percent(gold_change)}
USD/UAH {number(usd_uah)}

━━━━━━━━━━━━━━━━━━
₿ BTC POSITIONING
━━━━━━━━━━━━━━━━━━

BTC Dominance  {number(dominance)}%
Funding        {percent(funding)}
OI             {number(oi, 0)}
Liquidations   {liquidation_text}

Funding: {funding_text}

━━━━━━━━━━━━━━━━━━
🎯 ALGORITHM
━━━━━━━━━━━━━━━━━━

RISK SCORE: {score:+d}/100

{market_signal}

{confirmation}

━━━━━━━━━━━━━━━━━━

⚠️ Risk Score — рыночный фильтр,
не гарантия сделки.
"""

    return message


def send_report(chat_id):

    message = build_report()

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
            "reply_markup": make_keyboard()
        }
    )


def main():

    print("BTC RISK BOT STARTED")

    me = telegram(
        "getMe"
    )

    if not me or not me.get("ok"):

        raise Exception(
            "Telegram BOT_TOKEN error"
        )

    chat_id = get_chat_id()

    if not chat_id:

        print(
            "Chat not found."
        )

        return

    send_report(
        chat_id
    )

    print(
        "REPORT SENT"
    )


if __name__ == "__main__":

    main()

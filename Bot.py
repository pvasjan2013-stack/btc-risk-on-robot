import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    raise Exception("BOT_TOKEN is not configured")


def api(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "BTC-Risk-Bot/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def telegram(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"

    if params:
        data = urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=data)
    else:
        req = urllib.request.Request(url)

    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode())


def get_price(symbol):
    data = api(
        f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    )

    return {
        "price": float(data["lastPrice"]),
        "change": float(data["priceChangePercent"]),
        "volume": float(data["quoteVolume"])
    }


def make_analysis(btc, eth):
    score = 0

    if btc["change"] > 2:
        score += 2
    elif btc["change"] > 0:
        score += 1
    elif btc["change"] < -2:
        score -= 2
    else:
        score -= 1

    if eth["change"] > 2:
        score += 1
    elif eth["change"] < -2:
        score -= 1

    if score >= 2:
        signal = "🟢 LONG"
        idea = (
            "Фон рынка сейчас больше поддерживает LONG-сценарий.\n"
            "Но вход лучше искать после подтверждения движения BTC."
        )
    elif score <= -2:
        signal = "🔴 SHORT"
        idea = (
            "Фон рынка сейчас больше поддерживает SHORT-сценарий.\n"
            "Не стоит открывать позицию только по этому сигналу."
        )
    else:
        signal = "🟡 WAIT"
        idea = (
            "Рынок смешанный.\n"
            "Лучше дождаться более чёткого движения BTC."
        )

    score_text = f"{score:+d}/3"

    now = datetime.now(timezone.utc).strftime("%H:%M UTC")

    text = (
        "₿ BTC RISK ON BOT\n"
        "━━━━━━━━━━━━━━\n\n"
        f"🕐 {now}\n\n"
        f"₿ BTC: ${btc['price']:,.2f}\n"
        f"📊 24h: {btc['change']:+.2f}%\n\n"
        f"Ξ ETH: ${eth['price']:,.2f}\n"
        f"📊 24h: {eth['change']:+.2f}%\n\n"
        "━━━━━━━━━━━━━━\n"
        f"🎯 SIGNAL: {signal}\n"
        f"⚡ Risk Score: {score_text}\n\n"
        f"{idea}\n\n"
        "⚠️ Risk Score — фильтр, а не гарантия прибыли."
    )

    return text


def main():
    print("Bot started")

    btc = get_price("BTCUSDT")
    eth = get_price("ETHUSDT")

    print("BTC:", btc)
    print("ETH:", eth)

    result = telegram("getUpdates")

    if not result.get("ok"):
        raise Exception("Telegram getUpdates error")

    updates = result.get("result", [])

    if not updates:
        print("No Telegram messages yet.")
        print("Open your bot in Telegram and press /start.")
        return

    chat_id = None

    for update in reversed(updates):
        message = update.get("message")

        if message and message.get("chat"):
            chat_id = message["chat"]["id"]
            break

    if chat_id is None:
        print("No chat found.")
        return

    text = make_analysis(btc, eth)

    telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )

    print("Message sent successfully!")


if __name__ == "__main__":
    main()

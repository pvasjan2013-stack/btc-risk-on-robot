import os
import json
import urllib.request
import urllib.parse

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("ERROR: BOT_TOKEN not found")
    exit(1)


def request_json(url, data=None):
    try:
        if data:
            data = urllib.parse.urlencode(data).encode()
            req = urllib.request.Request(url, data=data)
        else:
            req = urllib.request.Request(url)

        req.add_header("User-Agent", "BTC-Risk-Bot/1.0")

        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode())

    except Exception as e:
        print("REQUEST ERROR:")
        print(type(e).__name__, str(e))
        return None


def telegram(method, params=None):
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    return request_json(url, params)


def get_market():
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum"
        "&vs_currencies=usd"
        "&include_24hr_change=true"
    )

    data = request_json(url)

    if not data:
        return None

    if "bitcoin" not in data or "ethereum" not in data:
        print("ERROR: CoinGecko returned unexpected data")
        print(data)
        return None

    return data


def main():

    print("================================")
    print("BTC RISK ON BOT STARTED")
    print("================================")

    print("Checking Telegram...")

    me = telegram("getMe")

    if not me or not me.get("ok"):
        print("ERROR: Telegram token is invalid or Telegram unavailable")
        print(me)
        exit(1)

    print("Telegram OK:", me["result"]["username"])

    print("Getting market data...")

    market = get_market()

    if not market:
        print("ERROR: Could not get market data")
        exit(1)

    btc_price = market["bitcoin"]["usd"]
    btc_change = market["bitcoin"].get("usd_24h_change", 0)

    eth_price = market["ethereum"]["usd"]
    eth_change = market["ethereum"].get("usd_24h_change", 0)

    print("BTC:", btc_price)
    print("BTC 24h:", btc_change)
    print("ETH:", eth_price)
    print("ETH 24h:", eth_change)

    if btc_change >= 2:
        signal = "🟢 LONG"
        idea = "BTC показывает сильный рост. LONG-сценарий выглядит предпочтительнее."
        score = 3

    elif btc_change <= -2:
        signal = "🔴 SHORT"
        idea = "BTC показывает сильное снижение. SHORT-сценарий выглядит предпочтительнее."
        score = -3

    else:
        signal = "🟡 WAIT"
        idea = "Движение BTC пока недостаточно сильное. Лучше дождаться подтверждения."
        score = 0

    text = f"""₿ BTC RISK ON BOT

━━━━━━━━━━━━━━

₿ BTC: ${btc_price:,.2f}
📊 24h: {btc_change:+.2f}%

Ξ ETH: ${eth_price:,.2f}
📊 24h: {eth_change:+.2f}%

━━━━━━━━━━━━━━

🎯 SIGNAL: {signal}
⚡ Risk Score: {score:+d}/3

{idea}

⚠️ Это аналитический фильтр, а не гарантия прибыли.
"""

    print("Searching for Telegram chat...")

    updates = telegram("getUpdates")

    if not updates or not updates.get("ok"):
        print("ERROR: Telegram getUpdates failed")
        print(updates)
        exit(1)

    results = updates.get("result", [])

    if not results:
        print("================================")
        print("NO CHAT FOUND")
        print("Open the bot in Telegram and send /start")
        print("Then run the workflow again.")
        print("================================")
        return

    chat_id = None

    for update in reversed(results):

        message = update.get("message")

        if message and message.get("chat"):
            chat_id = message["chat"]["id"]
            break

    if not chat_id:
        print("ERROR: Could not find chat_id")
        return

    print("Chat ID:", chat_id)

    result = telegram(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text
        }
    )

    if not result or not result.get("ok"):
        print("ERROR: Telegram could not send message")
        print(result)
        exit(1)

    print("================================")
    print("MESSAGE SENT SUCCESSFULLY")
    print("================================")


if __name__ == "__main__":
    main()

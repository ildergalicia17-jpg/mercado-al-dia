"""Genera crypto.json con cotizaciones públicas de Binance, sin API key."""
import datetime as dt
import json
import os
import urllib.parse
import urllib.request

ASSETS = [
    ("BTCUSDT", "Bitcoin", "BTC"),
    ("ETHUSDT", "Ethereum", "ETH"),
    ("BNBUSDT", "BNB", "BNB"),
    ("SOLUSDT", "Solana", "SOL"),
    ("XRPUSDT", "XRP", "XRP"),
    ("ADAUSDT", "Cardano", "ADA"),
    ("DOGEUSDT", "Dogecoin", "DOGE"),
    ("LINKUSDT", "Chainlink", "LINK"),
    ("AVAXUSDT", "Avalanche", "AVAX"),
    ("TRXUSDT", "TRON", "TRX"),
]


def main():
    symbols = [a[0] for a in ASSETS]
    query = urllib.parse.urlencode({"symbols": json.dumps(symbols, separators=(",", ":"))})
    url = "https://api.binance.com/api/v3/ticker/24hr?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "MercadoAlDia/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = json.loads(response.read().decode("utf-8"))

    by_symbol = {row.get("symbol"): row for row in raw}
    coins = []
    for market_symbol, name, symbol in ASSETS:
        row = by_symbol.get(market_symbol)
        if not row:
            continue
        coins.append({
            "name": name,
            "symbol": symbol,
            "price": float(row["lastPrice"]),
            "change24h": float(row["priceChangePercent"]),
            "high24h": float(row["highPrice"]),
            "low24h": float(row["lowPrice"]),
            "volume24h": float(row["quoteVolume"]),
        })

    if len(coins) < 8:
        raise RuntimeError(f"Respuesta incompleta del proveedor: solo {len(coins)} activos")

    output = {
        "provider": "Binance",
        "currency": "USDT",
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "coins": coins,
    }
    with open("crypto.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    print(f"Guardadas {len(coins)} cotizaciones; actualización UTC: {output['updated']}")


if __name__ == "__main__":
    main()

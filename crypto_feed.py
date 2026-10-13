"""Genera crypto.json con cotizaciones públicas de CoinGecko, sin API key."""
import datetime as dt
import json
import urllib.parse
import urllib.request

ASSETS = [
    ("bitcoin", "Bitcoin", "BTC"),
    ("ethereum", "Ethereum", "ETH"),
    ("binancecoin", "BNB", "BNB"),
    ("solana", "Solana", "SOL"),
    ("ripple", "XRP", "XRP"),
    ("cardano", "Cardano", "ADA"),
    ("dogecoin", "Dogecoin", "DOGE"),
    ("chainlink", "Chainlink", "LINK"),
    ("avalanche-2", "Avalanche", "AVAX"),
    ("tron", "TRON", "TRX"),
]


def main():
    ids = ",".join(asset[0] for asset in ASSETS)
    query = urllib.parse.urlencode({
        "vs_currency": "usd",
        "ids": ids,
        "price_change_percentage": "24h",
    })
    url = "https://api.coingecko.com/api/v3/coins/markets?" + query
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "MercadoAlDia/1.0",
            "accept": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = json.loads(response.read().decode("utf-8"))

    by_id = {row.get("id"): row for row in raw}
    coins = []
    for coin_id, name, symbol in ASSETS:
        row = by_id.get(coin_id)
        if not row or row.get("current_price") is None:
            continue
        coins.append({
            "name": name,
            "symbol": symbol,
            "price": float(row["current_price"]),
            "change24h": float(row.get("price_change_percentage_24h") or 0),
            "high24h": float(row.get("high_24h") or 0),
            "low24h": float(row.get("low_24h") or 0),
            "volume24h": float(row.get("total_volume") or 0),
        })

    if len(coins) < 8:
        raise RuntimeError(f"Respuesta incompleta del proveedor: solo {len(coins)} activos")

    output = {
        "provider": "CoinGecko",
        "currency": "USD",
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "coins": coins,
    }
    with open("crypto.json", "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
    print(f"Guardadas {len(coins)} cotizaciones; actualización UTC: {output['updated']}")


if __name__ == "__main__":
    main()

"""Genera data.json con datos de mercado (Yahoo Finance vía yfinance).
Uso: pip install yfinance && python update_data.py
"""
import json, datetime as dt
import yfinance as yf

INDICES = {"S&P 500": "^GSPC", "Nasdaq": "^IXIC", "Dow Jones": "^DJI", "Russell 2000": "^RUT"}
# Edita esta lista con las empresas que quieras seguir
WATCH = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "JPM", "V", "MA",
         "BAC", "WMT", "KO", "XOM", "LLY", "AVGO", "NFLX", "AMD", "COST", "DIS"]
REC = [(1.8, "Compra fuerte"), (2.6, "Compra"), (3.4, "Mantener"), (4.2, "Vender"), (9, "Vender fuerte")]


def clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def rec_text(v):
    return next((t for lim, t in REC if v <= lim), "N/D")


def analizar(sym):
    t = yf.Ticker(sym)
    h = t.history(period="6mo")["Close"].dropna()
    if len(h) < 65:
        return None
    px, prev = float(h.iloc[-1]), float(h.iloc[-2])
    mom = px / float(h.iloc[-64]) - 1
    try:
        info = t.info
    except Exception:
        info = {}
    tp = info.get("targetMeanPrice")
    rm = info.get("recommendationMean")
    up = (tp / px - 1) if tp else None
    score = None
    if up is not None and rm:
        score = round(100 * (0.45 * clip(up / 0.4) + 0.25 * clip((mom + 0.1) / 0.4)
                             + 0.30 * clip((5 - rm) / 4)))
    return {"t": sym, "n": info.get("shortName", sym), "p": px, "c": (px / prev - 1) * 100,
            "px": px, "tp": tp or px, "up": (up or 0) * 100, "mom": mom * 100,
            "rec": rec_text(rm) if rm else "N/D", "score": score,
            "h": [round(float(x), 2) for x in h.iloc[-90:]]}


def indices():
    out = []
    for name, sym in INDICES.items():
        try:
            h = yf.Ticker(sym).history(period="3mo")["Close"].dropna()
            out.append({"n": name, "p": float(h.iloc[-1]), "c": (h.iloc[-1] / h.iloc[-2] - 1) * 100,
                        "h": [round(float(x), 2) for x in h.iloc[-90:]]})
        except Exception:
            pass
    return out


def noticias():
    out = []
    try:
        for n in yf.Ticker("^GSPC").news[:8]:
            c = n.get("content", n)
            link = (c.get("canonicalUrl") or {}).get("url") or n.get("link")
            src = (c.get("provider") or {}).get("displayName") or n.get("publisher")
            if c.get("title") and link:
                out.append({"h": c["title"], "u": link, "s": src})
    except Exception:
        pass
    return out


def main():
    datos = [r for r in (analizar(s) for s in WATCH) if r]
    por_cambio = sorted(datos, key=lambda r: r["c"], reverse=True)
    preds = sorted([r for r in datos if r["score"] is not None], key=lambda r: r["score"], reverse=True)[:6]
    salida = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "indices": indices(),
        "predictions": preds,
        "movers": {"up": por_cambio[:5], "dn": por_cambio[-5:][::-1]},
        "news": noticias(),
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Recopila titulares financieros de RSS públicos y guarda news.json.
Publica titulares, fuente, fecha y enlace; no copia el cuerpo de los artículos.
"""
import datetime as dt
import email.utils
import json
import os
import time
import urllib.request
import xml.etree.ElementTree as ET

FEEDS = [
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Markets", "https://www.cnbc.com/id/15839135/device/rss/rss.html"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/"),
    ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Investing.com", "https://www.investing.com/rss/news_25.rss"),
]
OUT = "news.json"
MAX_ITEMS = 30
TIMEOUT = 18

def text(node, path):
    found = node.find(path)
    return (found.text or "").strip() if found is not None else ""

def parse_date(value):
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        return ""

def get_items(name, url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "MercadoAlDiaNewsBot/1.0 (financial headlines; RSS reader)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read(2_000_000)
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    if not items:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        items = root.findall(".//atom:entry", ns)
        result = []
        for item in items:
            title = text(item, "{http://www.w3.org/2005/Atom}title")
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
            published = text(item, "{http://www.w3.org/2005/Atom}published") or text(item, "{http://www.w3.org/2005/Atom}updated")
            if title and link.startswith("http"):
                result.append({"h": title, "u": link, "s": name, "published": parse_date(published)})
        return result
    result = []
    for item in items:
        title = text(item, "title")
        link = text(item, "link")
        published = text(item, "pubDate") or text(item, "published") or text(item, "date")
        if title and link.startswith("http"):
            result.append({"h": title, "u": link, "s": name, "published": parse_date(published)})
    return result

def main():
    collected = []
    for name, url in FEEDS:
        try:
            collected.extend(get_items(name, url))
            print(f"OK: {name}")
        except Exception as exc:
            print(f"WARN: {name}: {exc}")
    # Si un feed falla, conservamos noticias previas para no vaciar el panel.
    previous = []
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                previous = json.load(f).get("news", [])
        except Exception:
            previous = []
    by_url = {}
    for item in collected + previous:
        if item.get("u") and item.get("h"):
            by_url.setdefault(item["u"], item)
    items = list(by_url.values())
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    items = items[:MAX_ITEMS]
    if not items:
        raise RuntimeError("No se pudo obtener ninguna noticia; se conserva el archivo anterior.")
    old_items = previous[:MAX_ITEMS]
    old_urls = [x.get("u") for x in old_items]
    new_urls = [x.get("u") for x in items]
    # La marca de actualización cambia solo si llegaron titulares nuevos o cambió el listado.
    old_updated = ""
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                old_updated = json.load(f).get("updated", "")
        except Exception:
            pass
    updated = old_updated if old_urls == new_urls and old_updated else dt.datetime.now(dt.timezone.utc).isoformat()
    payload = {"updated": updated, "news": items, "sources": [name for name, _ in FEEDS]}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Noticias guardadas: {len(items)}; actualización: {updated}")

if __name__ == "__main__":
    main()

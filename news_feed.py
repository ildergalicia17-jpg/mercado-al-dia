#!/usr/bin/env python3
"""Recopila titulares y resúmenes RSS, traduce al español e intenta obtener imágenes."""
import datetime as dt
import email.utils
import html
import json
import os
import re
import time
import urllib.parse
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
NS_MEDIA = "{http://search.yahoo.com/mrss/}"
NS_CONTENT = "{http://purl.org/rss/1.0/modules/content/}"

def clean_html(value):
    value = html.unescape(value or "")
    value = re.sub(r"(?is)<(script|style).*?>.*?</\\1>", " ", value)
    value = re.sub(r"(?i)<br\\s*/?>|</p>|</div>|</li>", " ", value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\\s+", " ", value).strip()

def node_text(node, path):
    found = node.find(path)
    if found is None:
        return ""
    return "".join(found.itertext()).strip()

def parse_date(value):
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc).isoformat()
    except Exception:
        try:
            return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(dt.timezone.utc).isoformat()
        except Exception:
            return ""

def image_for(item, description=""):
    for path in (NS_MEDIA + "thumbnail", NS_MEDIA + "content", "image", "enclosure"):
        for el in item.findall(path):
            url = el.get("url") or el.get("href")
            mime = el.get("type", "")
            if url and (path != "enclosure" or mime.startswith("image/") or re.search(r"\\.(jpg|jpeg|png|webp)(?:[?#]|$)", url, re.I)):
                if url.startswith("https://") or url.startswith("http://"):
                    return url
    for el in item.findall(".//" + NS_CONTENT + "encoded"):
        description += " " + (el.text or "")
    match = re.search(r'<img[^>]+src=[\'"]([^\'"]+)', description, re.I)
    if match and match.group(1).startswith(("https://", "http://")):
        return match.group(1)
    return ""

def translate_es(value):
    value = (value or "").strip()
    if not value:
        return ""
    # Google Translate endpoint is used only for short RSS-provided snippets.
    try:
        query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": "es", "dt": "t", "q": value[:1200]})
        req = urllib.request.Request("https://translate.googleapis.com/translate_a/single?" + query,
            headers={"User-Agent": "Mozilla/5.0 MercadoAlDia/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read(500_000).decode("utf-8"))
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or value
    except Exception as exc:
        print("WARN traducción:", exc)
        return value

def get_items(name, url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MercadoAlDiaNewsBot/1.0)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml"
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
        raw = response.read(2_000_000)
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    result = []
    if items:
        for item in items:
            title = node_text(item, "title")
            link = node_text(item, "link")
            raw_desc = node_text(item, "description") or node_text(item, NS_CONTENT + "encoded")
            summary = clean_html(raw_desc)
            published = node_text(item, "pubDate") or node_text(item, "published") or node_text(item, "date")
            if title and link.startswith("http"):
                result.append({"h": title, "es": translate_es(title), "d": translate_es(summary[:900]),
                    "u": link, "s": name, "img": image_for(item, raw_desc), "published": parse_date(published)})
    else:
        ns = "{http://www.w3.org/2005/Atom}"
        for item in root.findall(".//" + ns + "entry"):
            title = node_text(item, ns + "title")
            link_el = item.find(ns + "link")
            link = link_el.get("href", "") if link_el is not None else ""
            summary = clean_html(node_text(item, ns + "summary") or node_text(item, ns + "content"))
            published = node_text(item, ns + "published") or node_text(item, ns + "updated")
            image = ""
            for el in item.findall(ns + "link"):
                if "image" in el.get("type", ""):
                    image = el.get("href", "")
                    break
            if title and link.startswith("http"):
                result.append({"h": title, "es": translate_es(title), "d": translate_es(summary[:900]),
                    "u": link, "s": name, "img": image, "published": parse_date(published)})
    return result

def main():
    collected = []
    for name, url in FEEDS:
        try:
            items = get_items(name, url)
            collected.extend(items)
            print(f"OK: {name} ({len(items)} titulares)")
        except Exception as exc:
            print(f"WARN: {name}: {exc}")
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
            # RSS actual tiene prioridad sobre los datos guardados anteriormente.
            by_url[item["u"]] = {**by_url.get(item["u"], {}), **item}
    items = list(by_url.values())
    for item in items:
        if not item.get("es"):
            item["es"] = translate_es(item.get("h", ""))
        if not item.get("d"):
            item["d"] = translate_es(clean_html(item.get("description", ""))[:900])
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    items = items[:MAX_ITEMS]
    if not items:
        raise RuntimeError("No se pudo obtener ninguna noticia; se conserva el archivo anterior.")
    old_urls = [x.get("u") for x in previous[:MAX_ITEMS]]
    new_urls = [x.get("u") for x in items]
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
